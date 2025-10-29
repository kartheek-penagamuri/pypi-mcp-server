"""Tests for migration analyzer functionality."""

import asyncio
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch
import json
import os

import pytest

from mcp_server.migration_analyzer import MigrationAnalyzer
from mcp_server.migration_models import (
    APIElement, APISurface, APIChange, VersionComparison, 
    MigrationResource, MigrationResources
)
from mcp_server.package_manager import PackageManager
from mcp_server.api_surface_extractor import APISurfaceExtractor
from mcp_server.version_comparator import VersionComparator
from mcp_server.migration_guide_finder import MigrationGuideFinder
from mcp_server.errors import MigrationAnalysisError, APIExtractionError


class TestMigrationAnalyzer:
    """Test cases for MigrationAnalyzer class."""

    @pytest.fixture
    def mock_package_manager(self):
        """Create a mock PackageManager."""
        return Mock(spec=PackageManager)

    @pytest.fixture
    def mock_api_extractor(self):
        """Create a mock APISurfaceExtractor."""
        return Mock(spec=APISurfaceExtractor)

    @pytest.fixture
    def mock_version_comparator(self):
        """Create a mock VersionComparator."""
        return Mock(spec=VersionComparator)

    @pytest.fixture
    def mock_migration_finder(self):
        """Create a mock MigrationGuideFinder."""
        return Mock(spec=MigrationGuideFinder)

    @pytest.fixture
    def sample_api_surface(self):
        """Create a sample API surface for testing."""
        return APISurface(
            package_name="test_package",
            version="1.0.0",
            classes=[
                APIElement(
                    name="TestClass",
                    type="class",
                    signature="class TestClass",
                    docstring="A test class."
                )
            ],
            functions=[
                APIElement(
                    name="test_function",
                    type="function",
                    signature="def test_function(x: int) -> str",
                    docstring="A test function."
                )
            ],
            constants=[
                APIElement(
                    name="TEST_CONSTANT",
                    type="constant",
                    signature="TEST_CONSTANT: str = 'test'",
                    docstring="A test constant."
                )
            ],
            extraction_method="runtime"
        )

    @pytest.fixture
    def migration_analyzer(self, mock_package_manager, mock_api_extractor, 
                          mock_version_comparator, mock_migration_finder):
        """Create a MigrationAnalyzer with mocked dependencies."""
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = MigrationAnalyzer(
                package_manager=mock_package_manager,
                api_extractor=mock_api_extractor,
                version_comparator=mock_version_comparator,
                migration_finder=mock_migration_finder,
                cache_dir=temp_dir,
                timeout=5.0
            )
            yield analyzer

    @pytest.mark.asyncio
    async def test_analyze_api_surface_success(self, migration_analyzer, mock_api_extractor, sample_api_surface):
        """Test successful API surface analysis."""
        mock_api_extractor.extract_from_package = AsyncMock(return_value=sample_api_surface)
        
        result = await migration_analyzer.analyze_api_surface("test_package", "1.0.0")
        
        assert result == sample_api_surface
        mock_api_extractor.extract_from_package.assert_called_once_with("test_package", "1.0.0")

    @pytest.mark.asyncio
    async def test_analyze_api_surface_caching(self, migration_analyzer, mock_api_extractor, sample_api_surface):
        """Test that API surface analysis results are cached."""
        mock_api_extractor.extract_from_package = AsyncMock(return_value=sample_api_surface)
        
        # First call
        result1 = await migration_analyzer.analyze_api_surface("test_package", "1.0.0")
        
        # Second call should use cache
        result2 = await migration_analyzer.analyze_api_surface("test_package", "1.0.0")
        
        assert result1 == result2
        # Should only call the extractor once
        mock_api_extractor.extract_from_package.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_api_surface_timeout(self, migration_analyzer, mock_api_extractor):
        """Test timeout handling in API surface analysis."""
        # Mock a slow operation
        async def slow_extract(*args, **kwargs):
            await asyncio.sleep(10)  # Longer than timeout
            return APISurface("test", "1.0.0")
        
        mock_api_extractor.extract_from_package = slow_extract
        
        with pytest.raises(MigrationAnalysisError, match="timed out"):
            await migration_analyzer.analyze_api_surface("test_package", "1.0.0")

    @pytest.mark.asyncio
    async def test_analyze_api_surface_error_handling(self, migration_analyzer, mock_api_extractor):
        """Test error handling in API surface analysis."""
        mock_api_extractor.extract_from_package = AsyncMock(
            side_effect=APIExtractionError("Extraction failed")
        )
        
        with pytest.raises(MigrationAnalysisError, match="Failed to analyze API surface"):
            await migration_analyzer.analyze_api_surface("test_package", "1.0.0")

    @pytest.mark.asyncio
    async def test_compare_versions_success(self, migration_analyzer, mock_api_extractor, 
                                          mock_version_comparator, sample_api_surface):
        """Test successful version comparison."""
        # Mock API surface extraction
        old_surface = sample_api_surface
        new_surface = APISurface(
            package_name="test_package",
            version="2.0.0",
            functions=[
                APIElement(
                    name="new_function",
                    type="function",
                    signature="def new_function() -> None",
                    docstring="A new function."
                )
            ]
        )
        
        mock_api_extractor.extract_from_package = AsyncMock(
            side_effect=[old_surface, new_surface]
        )
        
        # Mock version comparison
        comparison = VersionComparison(
            package_name="test_package",
            old_version="1.0.0",
            new_version="2.0.0",
            additions=[
                APIChange(
                    element_name="new_function",
                    change_type="added",
                    impact_level="enhancement",
                    element_type="function"
                )
            ]
        )
        mock_version_comparator.compare_api_surfaces = Mock(return_value=comparison)
        
        result = await migration_analyzer.compare_versions("test_package", "1.0.0", "2.0.0")
        
        assert result.package_name == "test_package"
        assert result.old_version == "1.0.0"
        assert result.new_version == "2.0.0"
        assert len(result.additions) == 1
        assert result.analysis_timestamp is not None

    @pytest.mark.asyncio
    async def test_compare_versions_concurrent_extraction(self, migration_analyzer, mock_api_extractor):
        """Test that version comparison extracts API surfaces concurrently."""
        call_times = []
        
        async def mock_extract(package_name, version):
            call_times.append(time.time())
            await asyncio.sleep(0.1)  # Simulate work
            return APISurface(package_name=package_name, version=version)
        
        mock_api_extractor.extract_from_package = mock_extract
        
        # Mock the version comparison to return a proper VersionComparison
        comparison = VersionComparison(
            package_name="test_package",
            old_version="1.0.0", 
            new_version="2.0.0",
            breaking_changes=[],
            additions=[],
            modifications=[],
            deprecations=[],
            dependency_changes=[]
        )
        migration_analyzer._perform_version_comparison = AsyncMock(return_value=comparison)
        
        start_time = time.time()
        await migration_analyzer.compare_versions("test_package", "1.0.0", "2.0.0")
        total_time = time.time() - start_time
        
        # Should take roughly 0.1s (concurrent) not 0.2s (sequential)
        assert total_time < 0.15
        assert len(call_times) == 2
        # Calls should be nearly simultaneous
        assert abs(call_times[1] - call_times[0]) < 0.05

    @pytest.mark.asyncio
    async def test_find_migration_resources_success(self, migration_analyzer, mock_migration_finder):
        """Test successful migration resource discovery."""
        resources = MigrationResources(
            package_name="test_package",
            version_range="1.0.0 -> 2.0.0",
            official_guides=[
                MigrationResource(
                    title="Migration Guide",
                    url="https://example.com/migration",
                    type="official_guide",
                    source="docs"
                )
            ]
        )
        
        mock_migration_finder.find_migration_resources = AsyncMock(return_value=resources)
        
        result = await migration_analyzer.find_migration_resources("test_package", "1.0.0", "2.0.0")
        
        assert result == resources
        mock_migration_finder.find_migration_resources.assert_called_once_with(
            "test_package", "1.0.0", "2.0.0"
        )

    @pytest.mark.asyncio
    async def test_find_migration_resources_fallback(self, migration_analyzer, mock_migration_finder):
        """Test fallback behavior when migration resource discovery fails."""
        mock_migration_finder.find_migration_resources = AsyncMock(
            side_effect=Exception("Discovery failed")
        )
        
        result = await migration_analyzer.find_migration_resources("test_package", "1.0.0", "2.0.0")
        
        # Should return fallback resources
        assert result.package_name == "test_package"
        assert result.version_range == "1.0.0 -> 2.0.0"
        assert len(result.documentation_links) >= 1
        assert "pypi.org" in result.documentation_links[0].url

    @pytest.mark.asyncio
    async def test_find_migration_resources_timeout_fallback(self, migration_analyzer, mock_migration_finder):
        """Test fallback behavior on timeout."""
        async def slow_find(*args, **kwargs):
            await asyncio.sleep(10)  # Longer than timeout
            return MigrationResources("test", "1.0->2.0")
        
        mock_migration_finder.find_migration_resources = slow_find
        
        result = await migration_analyzer.find_migration_resources("test_package", "1.0.0", "2.0.0")
        
        # Should return fallback resources
        assert result.package_name == "test_package"
        assert len(result.documentation_links) >= 1

    @pytest.mark.asyncio
    async def test_disk_cache_api_surface(self, migration_analyzer, mock_api_extractor, sample_api_surface):
        """Test disk caching for API surface analysis."""
        # Mock the disk cache methods to simulate caching behavior
        migration_analyzer._load_cached_api_surface = AsyncMock(return_value=None)  # First call: no cache
        migration_analyzer._save_cached_api_surface = AsyncMock()
        
        mock_api_extractor.extract_from_package = AsyncMock(return_value=sample_api_surface)
        
        # First call - should extract and cache
        result1 = await migration_analyzer.analyze_api_surface("test_package", "1.0.0")
        
        # Clear memory cache
        migration_analyzer._api_cache.clear()
        
        # Mock disk cache to return the cached result for second call
        migration_analyzer._load_cached_api_surface = AsyncMock(return_value=sample_api_surface)
        
        # Second call - should load from disk cache
        result2 = await migration_analyzer.analyze_api_surface("test_package", "1.0.0")
        
        assert result1.package_name == result2.package_name
        assert result1.version == result2.version
        assert len(result1.functions) == len(result2.functions)
        
        # Should only call extractor once (second call uses disk cache)
        mock_api_extractor.extract_from_package.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup(self, migration_analyzer, mock_api_extractor, mock_migration_finder):
        """Test cleanup functionality."""
        mock_api_extractor.cleanup_temp_directories = Mock()
        mock_migration_finder.close = AsyncMock()
        
        await migration_analyzer.cleanup()
        
        mock_api_extractor.cleanup_temp_directories.assert_called_once()
        mock_migration_finder.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_package_manager, mock_api_extractor, 
                                  mock_version_comparator, mock_migration_finder):
        """Test async context manager functionality."""
        mock_api_extractor.cleanup_temp_directories = Mock()
        mock_migration_finder.close = AsyncMock()
        
        async with MigrationAnalyzer(
            package_manager=mock_package_manager,
            api_extractor=mock_api_extractor,
            version_comparator=mock_version_comparator,
            migration_finder=mock_migration_finder
        ) as analyzer:
            assert analyzer is not None
        
        # Cleanup should be called on exit
        mock_api_extractor.cleanup_temp_directories.assert_called_once()
        mock_migration_finder.close.assert_called_once()


class TestMigrationAnalyzerIntegration:
    """Integration tests for MigrationAnalyzer with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_end_to_end_migration_analysis(self):
        """Test complete end-to-end migration analysis workflow."""
        # Create real instances with mocked external dependencies
        package_manager = Mock(spec=PackageManager)
        
        # Mock package info
        package_manager.get_package_info.return_value = Mock(
            name="requests",
            version="2.28.0",
            homepage="https://requests.readthedocs.io",
            repository="https://github.com/psf/requests"
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = MigrationAnalyzer(
                package_manager=package_manager,
                cache_dir=temp_dir,
                timeout=10.0
            )
            
            # Mock the API extractor to return realistic API surfaces
            old_api = APISurface(
                package_name="requests",
                version="2.25.0",
                functions=[
                    APIElement(
                        name="get",
                        type="function",
                        signature="def get(url, **kwargs)",
                        docstring="Send a GET request."
                    ),
                    APIElement(
                        name="post",
                        type="function", 
                        signature="def post(url, data=None, **kwargs)",
                        docstring="Send a POST request."
                    )
                ],
                classes=[
                    APIElement(
                        name="Session",
                        type="class",
                        signature="class Session",
                        docstring="A Requests session."
                    )
                ]
            )
            
            new_api = APISurface(
                package_name="requests",
                version="2.28.0",
                functions=[
                    APIElement(
                        name="get",
                        type="function",
                        signature="def get(url, **kwargs)",
                        docstring="Send a GET request."
                    ),
                    APIElement(
                        name="post",
                        type="function",
                        signature="def post(url, data=None, json=None, **kwargs)",
                        docstring="Send a POST request."
                    )
                ],
                classes=[
                    APIElement(
                        name="Session",
                        type="class",
                        signature="class Session",
                        docstring="A Requests session."
                    )
                ]
            )
            
            # Mock API extraction - return appropriate API based on version
            async def mock_extract(package_name, version):
                if version == "2.25.0":
                    return old_api
                elif version == "2.28.0":
                    return new_api
                else:
                    return new_api  # Default to new API
            
            analyzer.api_extractor.extract_from_package = mock_extract
            
            # Mock migration resource discovery
            resources = MigrationResources(
                package_name="requests",
                version_range="2.25.0 -> 2.28.0",
                changelogs=[
                    MigrationResource(
                        title="Requests Changelog",
                        url="https://github.com/psf/requests/blob/main/HISTORY.md",
                        type="changelog",
                        source="github"
                    )
                ]
            )
            analyzer.migration_finder.find_migration_resources = AsyncMock(return_value=resources)
            
            # Perform complete analysis
            api_result = await analyzer.analyze_api_surface("requests", "2.28.0")
            comparison_result = await analyzer.compare_versions("requests", "2.25.0", "2.28.0")
            resource_result = await analyzer.find_migration_resources("requests", "2.25.0", "2.28.0")
            
            # Verify results
            assert api_result.package_name == "requests"
            assert api_result.version == "2.28.0"
            
            assert comparison_result.package_name == "requests"
            assert comparison_result.old_version == "2.25.0"
            assert comparison_result.new_version == "2.28.0"
            
            assert resource_result.package_name == "requests"
            assert len(resource_result.changelogs) == 1

    @pytest.mark.asyncio
    async def test_performance_concurrent_operations(self):
        """Test performance with concurrent migration analysis operations."""
        package_manager = Mock(spec=PackageManager)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = MigrationAnalyzer(
                package_manager=package_manager,
                cache_dir=temp_dir,
                timeout=10.0
            )
            
            # Mock fast API extraction
            async def mock_extract(package_name, version):
                await asyncio.sleep(0.1)  # Simulate work
                return APISurface(
                    package_name=package_name,
                    version=version,
                    functions=[
                        APIElement(
                            name=f"func_{version.replace('.', '_')}",
                            type="function",
                            signature=f"def func_{version.replace('.', '_')}()",
                            docstring=f"Function for version {version}"
                        )
                    ]
                )
            
            analyzer.api_extractor.extract_from_package = mock_extract
            
            # Run multiple concurrent analyses
            packages = [
                ("package1", "1.0.0"),
                ("package2", "2.0.0"), 
                ("package3", "3.0.0"),
                ("package1", "1.1.0"),  # Same package, different version
                ("package2", "2.1.0")
            ]
            
            start_time = time.time()
            
            tasks = [
                analyzer.analyze_api_surface(pkg, ver) 
                for pkg, ver in packages
            ]
            results = await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            
            # Should complete in roughly 0.1s (concurrent) not 0.5s (sequential)
            assert total_time < 0.3
            assert len(results) == 5
            
            # Verify all results are correct
            for i, (pkg, ver) in enumerate(packages):
                assert results[i].package_name == pkg
                assert results[i].version == ver

    @pytest.mark.asyncio
    async def test_large_package_analysis_simulation(self):
        """Test analysis of a large package with many API elements."""
        package_manager = Mock(spec=PackageManager)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = MigrationAnalyzer(
                package_manager=package_manager,
                cache_dir=temp_dir,
                timeout=30.0
            )
            
            # Create a large API surface (simulating a big package like Django)
            large_api = APISurface(
                package_name="large_package",
                version="3.0.0",
                classes=[
                    APIElement(
                        name=f"Class{i}",
                        type="class",
                        signature=f"class Class{i}",
                        docstring=f"Class number {i}"
                    )
                    for i in range(100)  # 100 classes
                ],
                functions=[
                    APIElement(
                        name=f"function_{i}",
                        type="function",
                        signature=f"def function_{i}(arg1: int, arg2: int, arg3: int)",
                        docstring=f"Function number {i}"
                    )
                    for i in range(200)  # 200 functions
                ],
                constants=[
                    APIElement(
                        name=f"CONSTANT_{i}",
                        type="constant",
                        signature=f"CONSTANT_{i}: str = 'value_{i}'",
                        docstring=f"Constant number {i}"
                    )
                    for i in range(50)  # 50 constants
                ]
            )
            
            analyzer.api_extractor.extract_from_package = AsyncMock(return_value=large_api)
            
            start_time = time.time()
            result = await analyzer.analyze_api_surface("large_package", "3.0.0")
            analysis_time = time.time() - start_time
            
            # Should handle large API surface efficiently
            assert analysis_time < 5.0  # Should complete within 5 seconds
            assert len(result.classes) == 100
            assert len(result.functions) == 200
            assert len(result.constants) == 50
            
            # Test caching with large data
            start_time = time.time()
            cached_result = await analyzer.analyze_api_surface("large_package", "3.0.0")
            cache_time = time.time() - start_time
            
            # Cached access should be much faster
            assert cache_time < 0.1
            assert cached_result == result

    @pytest.mark.asyncio
    async def test_error_recovery_and_partial_results(self):
        """Test error recovery and partial result handling."""
        package_manager = Mock(spec=PackageManager)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            analyzer = MigrationAnalyzer(
                package_manager=package_manager,
                cache_dir=temp_dir,
                timeout=10.0
            )
            
            # Mock API extraction that fails for one version but succeeds for another
            call_count = 0
            async def mock_extract_with_failure(package_name, version):
                nonlocal call_count
                call_count += 1
                if version == "1.0.0":
                    raise APIExtractionError("Failed to extract API for 1.0.0")
                return APISurface(package_name=package_name, version=version)
            
            analyzer.api_extractor.extract_from_package = mock_extract_with_failure
            
            # Test that failure in one operation doesn't affect others
            with pytest.raises(MigrationAnalysisError):
                await analyzer.analyze_api_surface("test_package", "1.0.0")
            
            # But success should still work
            result = await analyzer.analyze_api_surface("test_package", "2.0.0")
            assert result.package_name == "test_package"
            assert result.version == "2.0.0"
            
            # Test migration resource fallback
            analyzer.migration_finder.find_migration_resources = AsyncMock(
                side_effect=Exception("Network error")
            )
            
            resources = await analyzer.find_migration_resources("test_package", "1.0.0", "2.0.0")
            
            # Should get fallback resources despite error
            assert resources.package_name == "test_package"
            assert len(resources.documentation_links) >= 1