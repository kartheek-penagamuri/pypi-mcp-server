"""Tests for migration guide finder functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import httpx

from mcp_server.migration_guide_finder import MigrationGuideFinder
from mcp_server.migration_models import MigrationResource, MigrationResources
from mcp_server.package_manager import PackageManager
from mcp_server.models import PackageInfo
from mcp_server.errors import MigrationResourceError


@pytest.fixture
def mock_package_manager():
    """Create a mock PackageManager."""
    manager = Mock(spec=PackageManager)
    manager.client = Mock()
    return manager


@pytest.fixture
def sample_package_info():
    """Create sample package info for testing."""
    return PackageInfo(
        name="test-package",
        version="2.0.0",
        description="A test package",
        homepage="https://test-package.readthedocs.io",
        repository="https://github.com/test/test-package",
        dependencies=[]
    )


@pytest.fixture
def mock_github_releases():
    """Mock GitHub releases API response."""
    return [
        {
            "tag_name": "v2.0.0",
            "name": "Version 2.0.0 - Major Release",
            "html_url": "https://github.com/test/test-package/releases/tag/v2.0.0",
            "body": "Major version with breaking changes"
        },
        {
            "tag_name": "v1.5.0",
            "name": "Version 1.5.0",
            "html_url": "https://github.com/test/test-package/releases/tag/v1.5.0",
            "body": "Feature release"
        }
    ]


@pytest.fixture
def mock_pypi_project_data():
    """Mock PyPI project data."""
    return {
        "info": {
            "name": "test-package",
            "version": "2.0.0",
            "description": "A test package with migration information. See CHANGELOG for upgrade instructions.",
            "project_urls": {
                "Homepage": "https://test-package.readthedocs.io",
                "Repository": "https://github.com/test/test-package",
                "Changelog": "https://github.com/test/test-package/blob/main/CHANGELOG.md"
            }
        }
    }


class TestMigrationGuideFinder:
    """Test cases for MigrationGuideFinder class."""

    @pytest.mark.asyncio
    async def test_find_migration_resources_basic(self, mock_package_manager, sample_package_info):
        """Test basic migration resource discovery."""
        mock_package_manager.get_package_info.return_value = sample_package_info
        
        finder = MigrationGuideFinder(package_manager=mock_package_manager)
        
        with patch.object(finder, '_client') as mock_client:
            # Mock all async methods to return empty lists
            with patch.object(finder, '_find_github_resources', return_value=[]):
                with patch.object(finder, '_find_readthedocs_resources', return_value=[]):
                    with patch.object(finder, '_find_pypi_resources', return_value=[]):
                        with patch.object(finder, '_find_changelog_resources', return_value=[]):
                            with patch.object(finder, '_find_fallback_resources') as mock_fallback:
                                mock_fallback.return_value = [
                                    MigrationResource(
                                        title="PyPI Project Page",
                                        url="https://pypi.org/project/test-package/",
                                        type="documentation",
                                        source="pypi"
                                    )
                                ]
                                
                                result = await finder.find_migration_resources("test-package", "1.0.0", "2.0.0")
        
        assert isinstance(result, MigrationResources)
        assert result.package_name == "test-package"
        assert result.version_range == "1.0.0 -> 2.0.0"
        assert len(result.documentation_links) == 1
        assert result.documentation_links[0].title == "PyPI Project Page"

    @pytest.mark.asyncio
    async def test_extract_urls_from_metadata(self, mock_package_manager, sample_package_info):
        """Test URL extraction from package metadata."""
        mock_package_manager.get_package_info.return_value = sample_package_info
        mock_package_manager.client.get_project.return_value = {
            "info": {
                "project_urls": {
                    "Source": "https://github.com/test/test-package",
                    "Documentation": "https://test-package.readthedocs.io",
                    "Changelog": "https://github.com/test/test-package/blob/main/CHANGELOG.md"
                }
            }
        }
        
        finder = MigrationGuideFinder(package_manager=mock_package_manager)
        urls = await finder._extract_urls_from_metadata("test-package")
        
        assert "github" in urls
        assert "readthedocs" in urls
        assert "changelog" in urls
        assert urls["github"] == "https://github.com/test/test-package"

    @pytest.mark.asyncio
    async def test_find_github_resources(self, mock_package_manager):
        """Test GitHub resource discovery."""
        finder = MigrationGuideFinder(package_manager=mock_package_manager)
        
        # Mock GitHub API responses
        mock_releases_response = Mock()
        mock_releases_response.status_code = 200
        mock_releases_response.json.return_value = [
            {
                "tag_name": "v2.0.0",
                "name": "Version 2.0.0",
                "html_url": "https://github.com/test/test-package/releases/tag/v2.0.0"
            }
        ]
        
        mock_changelog_response = Mock()
        mock_changelog_response.status_code = 200
        
        with patch.object(finder._client, 'get') as mock_get:
            mock_get.side_effect = [mock_releases_response, mock_changelog_response]
            
            resources = await finder._find_github_resources(
                "https://github.com/test/test-package", "1.0.0", "2.0.0"
            )
        
        assert len(resources) >= 1
        assert any(r.type == "changelog" for r in resources)
        assert any("github" in r.source for r in resources)

    @pytest.mark.asyncio
    async def test_find_readthedocs_resources(self, mock_package_manager):
        """Test ReadTheDocs resource discovery."""
        finder = MigrationGuideFinder(package_manager=mock_package_manager)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><head><title>Migration Guide</title></head></html>"
        
        with patch.object(finder._client, 'get', return_value=mock_response):
            resources = await finder._find_readthedocs_resources("https://test-package.readthedocs.io")
        
        assert len(resources) >= 1
        assert any(r.source == "readthedocs" for r in resources)

    @pytest.mark.asyncio
    async def test_find_pypi_resources(self, mock_package_manager, mock_pypi_project_data):
        """Test PyPI resource discovery."""
        mock_package_manager.client.get_project.return_value = mock_pypi_project_data
        
        finder = MigrationGuideFinder(package_manager=mock_package_manager)
        resources = await finder._find_pypi_resources("test-package")
        
        assert len(resources) >= 1
        # Should find resources from project URLs and description
        changelog_resources = [r for r in resources if r.type == "changelog"]
        assert len(changelog_resources) >= 1

    @pytest.mark.asyncio
    async def test_find_fallback_resources(self, mock_package_manager):
        """Test fallback resource discovery."""
        finder = MigrationGuideFinder(package_manager=mock_package_manager)
        
        resources = await finder._find_fallback_resources("test-package", "1.0.0", "2.0.0")
        
        assert len(resources) >= 3  # PyPI, GitHub search, Stack Overflow
        assert any("pypi.org" in r.url for r in resources)
        assert any("github.com/search" in r.url for r in resources)
        assert any("stackoverflow.com" in r.url for r in resources)

    @pytest.mark.asyncio
    async def test_categorize_resource(self, mock_package_manager):
        """Test resource categorization."""
        finder = MigrationGuideFinder(package_manager=mock_package_manager)
        resources = MigrationResources(package_name="test", version_range="1.0->2.0")
        
        # Test different resource types
        official_guide = MigrationResource(
            title="Migration Guide", url="http://example.com", type="official_guide", source="docs"
        )
        changelog = MigrationResource(
            title="Changelog", url="http://example.com", type="changelog", source="github"
        )
        community = MigrationResource(
            title="Community Guide", url="http://example.com", type="community_guide", source="github"
        )
        
        finder._categorize_resource(official_guide, resources)
        finder._categorize_resource(changelog, resources)
        finder._categorize_resource(community, resources)
        
        assert len(resources.official_guides) == 1
        assert len(resources.changelogs) == 1
        assert len(resources.community_resources) == 1

    def test_is_version_relevant(self, mock_package_manager):
        """Test version relevance checking."""
        finder = MigrationGuideFinder(package_manager=mock_package_manager)
        
        assert finder._is_version_relevant("v2.0.0", "1.0.0", "2.0.0")
        assert finder._is_version_relevant("2.1.0", "1.0.0", "2.0.0")
        assert not finder._is_version_relevant("invalid-tag", "1.0.0", "2.0.0")

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_package_manager):
        """Test error handling in migration resource discovery."""
        mock_package_manager.get_package_info.side_effect = Exception("Package not found")
        
        finder = MigrationGuideFinder(package_manager=mock_package_manager)
        
        with pytest.raises(MigrationResourceError):
            await finder.find_migration_resources("nonexistent-package", "1.0.0", "2.0.0")

    @pytest.mark.asyncio
    async def test_network_error_graceful_handling(self, mock_package_manager, sample_package_info):
        """Test graceful handling of network errors."""
        mock_package_manager.get_package_info.return_value = sample_package_info
        
        finder = MigrationGuideFinder(package_manager=mock_package_manager)
        
        # Mock network failures for individual sources
        with patch.object(finder, '_find_github_resources', side_effect=Exception("Network error")):
            with patch.object(finder, '_find_readthedocs_resources', return_value=[]):
                with patch.object(finder, '_find_pypi_resources', return_value=[]):
                    with patch.object(finder, '_find_changelog_resources', return_value=[]):
                        with patch.object(finder, '_find_fallback_resources') as mock_fallback:
                            mock_fallback.return_value = [
                                MigrationResource(
                                    title="Fallback", url="http://example.com", 
                                    type="documentation", source="fallback"
                                )
                            ]
                            
                            result = await finder.find_migration_resources("test-package", "1.0.0", "2.0.0")
        
        # Should still return results despite GitHub failure
        assert isinstance(result, MigrationResources)
        assert len(result.documentation_links) == 1

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_package_manager):
        """Test async context manager functionality."""
        async with MigrationGuideFinder(package_manager=mock_package_manager) as finder:
            assert finder is not None
        
        # Client should be closed after context exit
        # Note: In real usage, this would close the httpx client