"""Tests for MCP server functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock

import pytest
from mcp_server.server import (
    analyze_project_dependencies,
    get_package_metadata,
    search_packages,
    check_package_compatibility,
    get_latest_version,
    analyze_package_api_surface,
    compare_package_versions,
    get_migration_resources,
    _analyzer,
    _pkg,
    _migration_analyzer
)
from mcp_server.models import Dependency, PackageInfo, ProjectInfo, PackageSearchResult
from mcp_server.migration_models import APISurface, VersionComparison, MigrationResources, APIElement, APIChange, MigrationResource
from mcp_server.errors import MigrationAnalysisError


class TestAnalyzeProjectDependencies:
    """Test the analyze_project_dependencies MCP tool."""

    @patch('mcp_server.server._analyzer')
    def test_analyze_project_dependencies_default_path(self, mock_analyzer):
        """Test analyzing project with default path (CWD)."""
        mock_info = ProjectInfo(
            project_path="/current/dir",
            dependency_files=["requirements.txt"],
            dependencies=[Dependency(name="requests", version_spec=">=2.0")]
        )
        mock_analyzer.analyze_project.return_value = mock_info
        
        with patch('os.getcwd', return_value="/current/dir"):
            result = analyze_project_dependencies()
        
        assert result["project_path"] == "/current/dir"
        assert len(result["dependencies"]) == 1
        assert result["dependencies"][0]["name"] == "requests"
        mock_analyzer.analyze_project.assert_called_once_with("/current/dir")

    @patch('mcp_server.server._analyzer')
    def test_analyze_project_dependencies_custom_path(self, mock_analyzer):
        """Test analyzing project with custom path."""
        mock_info = ProjectInfo(
            project_path="/custom/path",
            dependency_files=["pyproject.toml"],
            dependencies=[Dependency(name="httpx", version_spec=">=0.27")]
        )
        mock_analyzer.analyze_project.return_value = mock_info
        
        result = analyze_project_dependencies(project_path="/custom/path")
        
        assert result["project_path"] == "/custom/path"
        assert len(result["dependency_files"]) == 1
        assert "pyproject.toml" in result["dependency_files"][0]
        mock_analyzer.analyze_project.assert_called_once_with("/custom/path")

    @patch('mcp_server.server._analyzer')
    def test_analyze_project_dependencies_serialization(self, mock_analyzer):
        """Test that result is properly serialized."""
        mock_info = ProjectInfo(
            project_path="/test",
            dependencies=[
                Dependency(
                    name="requests", 
                    version_spec=">=2.0", 
                    extras=["security"],
                    is_dev_dependency=True
                )
            ]
        )
        mock_analyzer.analyze_project.return_value = mock_info
        
        result = analyze_project_dependencies(project_path="/test")
        
        # Check serialization of complex objects
        dep = result["dependencies"][0]
        assert dep["name"] == "requests"
        assert dep["version_spec"] == ">=2.0"
        assert dep["extras"] == ["security"]
        assert dep["is_dev_dependency"] is True


class TestGetPackageMetadata:
    """Test the get_package_metadata MCP tool."""

    @patch('mcp_server.server._pkg')
    def test_get_package_metadata_basic(self, mock_pkg):
        """Test getting basic package metadata."""
        mock_info = PackageInfo(
            name="requests",
            version="2.25.0",
            description="HTTP library",
            author="Kenneth Reitz",
            license="Apache 2.0"
        )
        mock_pkg.get_package_info.return_value = mock_info
        
        result = get_package_metadata("requests")
        
        assert result["name"] == "requests"
        assert result["version"] == "2.25.0"
        assert result["description"] == "HTTP library"
        assert result["install_hint"] == "pip install requests"
        mock_pkg.get_package_info.assert_called_once_with("requests", version_spec=None)

    @patch('mcp_server.server._pkg')
    def test_get_package_metadata_with_version_spec(self, mock_pkg):
        """Test getting package metadata with version specifier."""
        mock_info = PackageInfo(name="requests", version="2.25.0")
        mock_pkg.get_package_info.return_value = mock_info
        
        result = get_package_metadata("requests", version_spec=">=2.0,<3.0")
        
        assert result["install_hint"] == "pip install requests>=2.0,<3.0"
        mock_pkg.get_package_info.assert_called_once_with("requests", version_spec=">=2.0,<3.0")

    @patch('mcp_server.server._pkg')
    def test_get_package_metadata_with_long_description(self, mock_pkg):
        """Test getting package metadata with long description."""
        mock_info = PackageInfo(
            name="requests",
            version="2.25.0",
            description="HTTP library",
            long_description="# Requests\n\nA simple HTTP library",
            long_description_content_type="text/markdown"
        )
        mock_pkg.get_package_info.return_value = mock_info
        
        result = get_package_metadata("requests")
        
        assert result["long_description"] == "# Requests\n\nA simple HTTP library"
        assert result["long_description_content_type"] == "text/markdown"


class TestSearchPackages:
    """Test the search_packages MCP tool."""

    @patch('mcp_server.server._pkg')
    def test_search_packages_basic(self, mock_pkg):
        """Test basic package search."""
        mock_results = [
            PackageSearchResult(
                name="requests",
                description="HTTP library",
                version="2.25.0",
                author="Kenneth Reitz"
            ),
            PackageSearchResult(
                name="httpx",
                description="Async HTTP client",
                version="0.27.0",
                author="Tom Christie"
            )
        ]
        mock_pkg.search_packages.return_value = mock_results
        
        result = search_packages("http client")
        
        assert len(result) == 2
        assert result[0]["name"] == "requests"
        assert result[1]["name"] == "httpx"
        mock_pkg.search_packages.assert_called_once_with("http client", limit=10, python_version=None)

    @patch('mcp_server.server._pkg')
    def test_search_packages_with_limit(self, mock_pkg):
        """Test package search with custom limit."""
        mock_pkg.search_packages.return_value = []
        
        search_packages("test", limit=5)
        
        mock_pkg.search_packages.assert_called_once_with("test", limit=5, python_version=None)

    @patch('mcp_server.server._pkg')
    def test_search_packages_with_python_version(self, mock_pkg):
        """Test package search with Python version hint."""
        mock_pkg.search_packages.return_value = []
        
        search_packages("test", python_version="3.11")
        
        mock_pkg.search_packages.assert_called_once_with("test", limit=10, python_version="3.11")

    @patch('mcp_server.server._pkg')
    def test_search_packages_fallback_to_exact_match(self, mock_pkg):
        """Test fallback to exact package name when search returns nothing."""
        # First call (search) returns empty
        # Second call (get_package_info) returns package info
        mock_pkg.search_packages.return_value = []
        mock_info = PackageInfo(
            name="exact-package",
            version="1.0.0",
            description="Exact match",
            author="Test Author"
        )
        mock_pkg.get_package_info.return_value = mock_info
        
        result = search_packages("exact-package")
        
        assert len(result) == 1
        assert result[0]["name"] == "exact-package"
        assert result[0]["description"] == "Exact match"
        mock_pkg.get_package_info.assert_called_once_with("exact-package")

    @patch('mcp_server.server._pkg')
    def test_search_packages_fallback_fails(self, mock_pkg):
        """Test fallback behavior when exact match also fails."""
        mock_pkg.search_packages.return_value = []
        mock_pkg.get_package_info.side_effect = Exception("Package not found")
        
        result = search_packages("nonexistent")
        
        assert result == []


class TestCheckPackageCompatibility:
    """Test the check_package_compatibility MCP tool."""

    @patch('mcp_server.server._analyzer')
    @patch('mcp_server.server._pkg')
    def test_check_package_compatibility_default_path(self, mock_pkg, mock_analyzer):
        """Test compatibility check with default path."""
        mock_info = ProjectInfo(
            project_path="/current/dir",
            dependencies=[Dependency(name="requests", version_spec=">=2.0")]
        )
        mock_analyzer.analyze_project.return_value = mock_info
        mock_pkg.check_compatibility.return_value = {"conflicts": []}
        
        with patch('os.getcwd', return_value="/current/dir"):
            result = check_package_compatibility("httpx")
        
        assert result["conflicts"] == []
        mock_analyzer.analyze_project.assert_called_once_with("/current/dir")
        mock_pkg.check_compatibility.assert_called_once_with(
            mock_info.dependencies, "httpx", None
        )

    @patch('mcp_server.server._analyzer')
    @patch('mcp_server.server._pkg')
    def test_check_package_compatibility_with_version(self, mock_pkg, mock_analyzer):
        """Test compatibility check with version specifier."""
        mock_info = ProjectInfo(project_path="/test", dependencies=[])
        mock_analyzer.analyze_project.return_value = mock_info
        mock_pkg.check_compatibility.return_value = {"conflicts": []}
        
        check_package_compatibility("httpx", version_spec=">=0.27", project_path="/test")
        
        mock_pkg.check_compatibility.assert_called_once_with([], "httpx", ">=0.27")

    @patch('mcp_server.server._analyzer')
    @patch('mcp_server.server._pkg')
    def test_check_package_compatibility_with_conflicts(self, mock_pkg, mock_analyzer):
        """Test compatibility check that finds conflicts."""
        mock_info = ProjectInfo(project_path="/test", dependencies=[])
        mock_analyzer.analyze_project.return_value = mock_info
        
        conflicts = [
            {
                "package": "requests",
                "reason": "No version satisfies all constraints",
                "constraints": [">=2.0", ">=3.0"]
            }
        ]
        mock_pkg.check_compatibility.return_value = {"conflicts": conflicts}
        
        result = check_package_compatibility("requests", version_spec=">=3.0")
        
        assert len(result["conflicts"]) == 1
        assert result["conflicts"][0]["package"] == "requests"


class TestGetLatestVersion:
    """Test the get_latest_version MCP tool."""

    @patch('mcp_server.server._pkg')
    def test_get_latest_version_basic(self, mock_pkg):
        """Test getting latest version."""
        mock_result = {
            "name": "requests",
            "version": "2.25.0",
            "is_prerelease": False,
            "source": "pypi"
        }
        mock_pkg.get_latest_version.return_value = mock_result
        
        result = get_latest_version("requests")
        
        assert result == mock_result
        mock_pkg.get_latest_version.assert_called_once_with("requests", allow_prerelease=False)

    @patch('mcp_server.server._pkg')
    def test_get_latest_version_with_prerelease(self, mock_pkg):
        """Test getting latest version including prereleases."""
        mock_result = {
            "name": "requests",
            "version": "2.26.0rc1",
            "is_prerelease": True,
            "source": "pypi"
        }
        mock_pkg.get_latest_version.return_value = mock_result
        
        result = get_latest_version("requests", allow_prerelease=True)
        
        assert result["version"] == "2.26.0rc1"
        assert result["is_prerelease"] is True
        mock_pkg.get_latest_version.assert_called_once_with("requests", allow_prerelease=True)


class TestServerIntegration:
    """Integration tests for the MCP server."""

    def test_server_singletons_exist(self):
        """Test that server singletons are properly initialized."""
        assert _analyzer is not None
        assert _pkg is not None

    @patch('mcp_server.server.mcp')
    def test_main_function_stdio(self, mock_mcp):
        """Test main function with stdio transport."""
        from mcp_server.server import main
        
        with patch('sys.argv', ['server.py', 'stdio']):
            main()
        
        mock_mcp.run.assert_called_once_with(transport='stdio')

    @patch('mcp_server.server.mcp')
    def test_main_function_default_transport(self, mock_mcp):
        """Test main function with default transport."""
        from mcp_server.server import main
        
        with patch('sys.argv', ['server.py']):
            main()
        
        mock_mcp.run.assert_called_once_with(transport='stdio')

    def test_real_project_analysis(self):
        """Integration test with real project structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a real requirements.txt
            req_file = Path(tmpdir) / "requirements.txt"
            req_file.write_text("requests>=2.25.0\nhttpx==0.27.0\n")
            
            # Test the actual function
            result = analyze_project_dependencies(project_path=tmpdir)
            
            assert "project_path" in result
            assert "dependencies" in result
            assert len(result["dependencies"]) == 2
            
            # Check dependency details
            dep_names = {d["name"] for d in result["dependencies"]}
            assert dep_names == {"requests", "httpx"}

    def test_tool_error_handling(self):
        """Test that tools handle errors gracefully."""
        # This should not raise an exception even with invalid path
        result = analyze_project_dependencies(project_path="/nonexistent/path")
        
        # Should return valid structure even on error
        assert "project_path" in result
        assert "dependencies" in result
        assert isinstance(result["dependencies"], list)


class TestAnalyzePackageAPISurface:
    """Test the analyze_package_api_surface MCP tool."""

    @pytest.mark.asyncio
    @patch('mcp_server.server._migration_analyzer')
    async def test_analyze_api_surface_basic(self, mock_analyzer):
        """Test basic API surface analysis."""
        mock_api_surface = APISurface(
            package_name="requests",
            version="2.25.0",
            classes=[APIElement(name="Session", type="class", signature="class Session")],
            functions=[APIElement(name="get", type="function", signature="def get(url, **kwargs)")],
            constants=[APIElement(name="__version__", type="constant", signature="__version__ = '2.25.0'")],
            modules=["requests.auth", "requests.models"],
            extraction_method="runtime",
            extraction_timestamp="2023-01-01T00:00:00Z"
        )
        mock_analyzer.analyze_api_surface = AsyncMock(return_value=mock_api_surface)
        
        result = await analyze_package_api_surface("requests", "2.25.0")
        
        assert result["package_name"] == "requests"
        assert result["version"] == "2.25.0"
        assert len(result["classes"]) == 1
        assert result["classes"][0]["name"] == "Session"
        assert len(result["functions"]) == 1
        assert result["functions"][0]["name"] == "get"
        assert len(result["constants"]) == 1
        assert result["constants"][0]["name"] == "__version__"
        assert result["extraction_method"] == "runtime"
        mock_analyzer.analyze_api_surface.assert_called_once_with("requests", "2.25.0")

    @pytest.mark.asyncio
    @patch('mcp_server.server._migration_analyzer')
    async def test_analyze_api_surface_migration_error(self, mock_analyzer):
        """Test API surface analysis with migration error."""
        mock_analyzer.analyze_api_surface = AsyncMock(
            side_effect=MigrationAnalysisError("Failed to extract API surface")
        )
        
        with pytest.raises(MigrationAnalysisError, match="Failed to extract API surface"):
            await analyze_package_api_surface("nonexistent", "1.0.0")

    @pytest.mark.asyncio
    @patch('mcp_server.server._migration_analyzer')
    async def test_analyze_api_surface_unexpected_error(self, mock_analyzer):
        """Test API surface analysis with unexpected error."""
        mock_analyzer.analyze_api_surface = AsyncMock(
            side_effect=Exception("Unexpected error")
        )
        
        with pytest.raises(MigrationAnalysisError, match="Failed to analyze API surface"):
            await analyze_package_api_surface("requests", "2.25.0")


class TestComparePackageVersions:
    """Test the compare_package_versions MCP tool."""

    @pytest.mark.asyncio
    @patch('mcp_server.server._migration_analyzer')
    async def test_compare_versions_basic(self, mock_analyzer):
        """Test basic version comparison."""
        mock_comparison = VersionComparison(
            package_name="django",
            old_version="3.2.0",
            new_version="4.0.0",
            breaking_changes=[
                APIChange(
                    element_name="django.conf.urls.url",
                    change_type="removed",
                    impact_level="breaking",
                    description="Function removed, use django.urls.re_path instead",
                    element_type="function"
                )
            ],
            additions=[
                APIChange(
                    element_name="django.urls.re_path",
                    change_type="added",
                    new_signature="def re_path(route, view, kwargs=None, name=None)",
                    impact_level="enhancement",
                    description="New function for URL patterns",
                    element_type="function"
                )
            ],
            modifications=[],
            deprecations=[],
            dependency_changes=["Python 3.8+ required"],
            analysis_timestamp="2023-01-01T00:00:00Z"
        )
        mock_analyzer.compare_versions = AsyncMock(return_value=mock_comparison)
        
        result = await compare_package_versions("django", "3.2.0", "4.0.0")
        
        assert result["package_name"] == "django"
        assert result["old_version"] == "3.2.0"
        assert result["new_version"] == "4.0.0"
        assert len(result["breaking_changes"]) == 1
        assert result["breaking_changes"][0]["element_name"] == "django.conf.urls.url"
        assert result["breaking_changes"][0]["impact_level"] == "breaking"
        assert len(result["additions"]) == 1
        assert result["additions"][0]["element_name"] == "django.urls.re_path"
        assert len(result["dependency_changes"]) == 1
        assert result["dependency_changes"][0] == "Python 3.8+ required"
        mock_analyzer.compare_versions.assert_called_once_with("django", "3.2.0", "4.0.0")

    @pytest.mark.asyncio
    @patch('mcp_server.server._migration_analyzer')
    async def test_compare_versions_no_changes(self, mock_analyzer):
        """Test version comparison with no changes."""
        mock_comparison = VersionComparison(
            package_name="requests",
            old_version="2.25.0",
            new_version="2.25.1",
            analysis_timestamp="2023-01-01T00:00:00Z"
        )
        mock_analyzer.compare_versions = AsyncMock(return_value=mock_comparison)
        
        result = await compare_package_versions("requests", "2.25.0", "2.25.1")
        
        assert len(result["breaking_changes"]) == 0
        assert len(result["additions"]) == 0
        assert len(result["modifications"]) == 0
        assert len(result["deprecations"]) == 0

    @pytest.mark.asyncio
    @patch('mcp_server.server._migration_analyzer')
    async def test_compare_versions_migration_error(self, mock_analyzer):
        """Test version comparison with migration error."""
        mock_analyzer.compare_versions = AsyncMock(
            side_effect=MigrationAnalysisError("Failed to compare versions")
        )
        
        with pytest.raises(MigrationAnalysisError, match="Failed to compare versions"):
            await compare_package_versions("nonexistent", "1.0.0", "2.0.0")


class TestGetMigrationResources:
    """Test the get_migration_resources MCP tool."""

    @pytest.mark.asyncio
    @patch('mcp_server.server._migration_analyzer')
    async def test_get_migration_resources_basic(self, mock_analyzer):
        """Test basic migration resource discovery."""
        mock_resources = MigrationResources(
            package_name="flask",
            version_range="1.1.0 -> 2.0.0",
            official_guides=[
                MigrationResource(
                    title="Flask 2.0 Migration Guide",
                    url="https://flask.palletsprojects.com/en/2.0.x/upgrading/",
                    type="official_guide",
                    description="Official migration guide for Flask 2.0",
                    source="official_docs"
                )
            ],
            changelogs=[
                MigrationResource(
                    title="Flask 2.0.0 Changelog",
                    url="https://github.com/pallets/flask/releases/tag/2.0.0",
                    type="changelog",
                    description="Release notes for Flask 2.0.0",
                    source="github"
                )
            ],
            community_resources=[],
            documentation_links=[
                MigrationResource(
                    title="Flask Documentation",
                    url="https://flask.palletsprojects.com/",
                    type="documentation",
                    description="Official Flask documentation",
                    source="official_docs"
                )
            ],
            search_timestamp="2023-01-01T00:00:00Z"
        )
        mock_analyzer.find_migration_resources = AsyncMock(return_value=mock_resources)
        
        result = await get_migration_resources("flask", "1.1.0", "2.0.0")
        
        assert result["package_name"] == "flask"
        assert result["version_range"] == "1.1.0 -> 2.0.0"
        assert len(result["official_guides"]) == 1
        assert result["official_guides"][0]["title"] == "Flask 2.0 Migration Guide"
        assert len(result["changelogs"]) == 1
        assert result["changelogs"][0]["title"] == "Flask 2.0.0 Changelog"
        assert len(result["documentation_links"]) == 1
        assert result["documentation_links"][0]["title"] == "Flask Documentation"
        mock_analyzer.find_migration_resources.assert_called_once_with("flask", "1.1.0", "2.0.0")

    @pytest.mark.asyncio
    @patch('mcp_server.server._migration_analyzer')
    async def test_get_migration_resources_migration_error(self, mock_analyzer):
        """Test migration resource discovery with migration error."""
        mock_analyzer.find_migration_resources = AsyncMock(
            side_effect=MigrationAnalysisError("Failed to find resources")
        )
        
        result = await get_migration_resources("nonexistent", "1.0.0", "2.0.0")
        
        # Should return fallback structure with error
        assert result["package_name"] == "nonexistent"
        assert result["version_range"] == "1.0.0 -> 2.0.0"
        assert result["official_guides"] == []
        assert result["changelogs"] == []
        assert result["community_resources"] == []
        assert result["documentation_links"] == []
        assert "error" in result
        assert "Failed to find resources" in result["error"]

    @pytest.mark.asyncio
    @patch('mcp_server.server._migration_analyzer')
    async def test_get_migration_resources_unexpected_error(self, mock_analyzer):
        """Test migration resource discovery with unexpected error."""
        mock_analyzer.find_migration_resources = AsyncMock(
            side_effect=Exception("Unexpected error")
        )
        
        result = await get_migration_resources("requests", "2.25.0", "2.26.0")
        
        # Should return fallback structure with PyPI link
        assert result["package_name"] == "requests"
        assert result["version_range"] == "2.25.0 -> 2.26.0"
        assert len(result["community_resources"]) == 1
        assert "pypi.org/project/requests" in result["community_resources"][0]["url"]
        assert "error" in result
        assert "Resource discovery failed" in result["error"]

    @pytest.mark.asyncio
    @patch('mcp_server.server._migration_analyzer')
    async def test_get_migration_resources_empty_results(self, mock_analyzer):
        """Test migration resource discovery with empty results."""
        mock_resources = MigrationResources(
            package_name="obscure-package",
            version_range="1.0.0 -> 2.0.0",
            search_timestamp="2023-01-01T00:00:00Z"
        )
        mock_analyzer.find_migration_resources = AsyncMock(return_value=mock_resources)
        
        result = await get_migration_resources("obscure-package", "1.0.0", "2.0.0")
        
        assert result["package_name"] == "obscure-package"
        assert len(result["official_guides"]) == 0
        assert len(result["changelogs"]) == 0
        assert len(result["community_resources"]) == 0
        assert len(result["documentation_links"]) == 0
        assert "error" not in result


class TestMigrationToolsIntegration:
    """Integration tests for migration tools."""

    def test_migration_analyzer_singleton_exists(self):
        """Test that migration analyzer singleton is properly initialized."""
        assert _migration_analyzer is not None
        assert _migration_analyzer.package_manager is _pkg

    @pytest.mark.asyncio
    async def test_migration_tools_async_compatibility(self):
        """Test that migration tools are properly async."""
        # These should be async functions
        import inspect
        assert inspect.iscoroutinefunction(analyze_package_api_surface)
        assert inspect.iscoroutinefunction(compare_package_versions)
        assert inspect.iscoroutinefunction(get_migration_resources)