"""
Migration Analyzer - Main coordinator for package migration analysis operations.

This module provides the MigrationAnalyzer class that orchestrates API surface analysis,
version comparison, and migration resource discovery with caching and error handling.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple, Any
import hashlib
import json
import os
from pathlib import Path

from .api_surface_extractor import APISurfaceExtractor
from .version_comparator import VersionComparator
from .migration_guide_finder import MigrationGuideFinder
from .migration_models import APISurface, VersionComparison, MigrationResources
from .package_manager import PackageManager
from .errors import MigrationAnalysisError, APIExtractionError, VersionComparisonError, MigrationResourceError

logger = logging.getLogger(__name__)


class MigrationAnalyzer:
    """
    Main coordinator for migration analysis operations.
    
    Orchestrates API surface extraction, version comparison, and migration resource
    discovery with caching, timeout handling, and comprehensive error management.
    """

    def __init__(
        self,
        package_manager: Optional[PackageManager] = None,
        api_extractor: Optional[APISurfaceExtractor] = None,
        version_comparator: Optional[VersionComparator] = None,
        migration_finder: Optional[MigrationGuideFinder] = None,
        cache_dir: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize the migration analyzer.
        
        Args:
            package_manager: PackageManager instance for package operations
            api_extractor: APISurfaceExtractor for analyzing API surfaces
            version_comparator: VersionComparator for comparing versions
            migration_finder: MigrationGuideFinder for finding migration resources
            cache_dir: Directory for caching analysis results
            timeout: Default timeout for operations in seconds
        """
        self.package_manager = package_manager or PackageManager()
        self.api_extractor = api_extractor or APISurfaceExtractor()
        self.version_comparator = version_comparator or VersionComparator(self.package_manager, self.api_extractor)
        self.migration_finder = migration_finder or MigrationGuideFinder(self.package_manager)
        self.timeout = timeout
        
        # Set up caching
        self.cache_dir = cache_dir or os.path.join(os.path.expanduser("~"), ".cache", "mcp_migration_analyzer")
        self._ensure_cache_dir()
        
        # Cache for API surface analysis results
        self._api_cache: Dict[str, APISurface] = {}
        self._comparison_cache: Dict[str, VersionComparison] = {}
        self._resource_cache: Dict[str, MigrationResources] = {}

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        try:
            Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create cache directory {self.cache_dir}: {e}")
            # Fall back to no caching
            self.cache_dir = None

    async def analyze_api_surface(self, package_name: str, version: str) -> APISurface:
        """
        Analyze the public API surface of a package version with caching.
        
        Args:
            package_name: Name of the package to analyze
            version: Version of the package to analyze
            
        Returns:
            APISurface containing all public API elements
            
        Raises:
            MigrationAnalysisError: If analysis fails
        """
        cache_key = f"{package_name}:{version}"
        
        # Check memory cache first
        if cache_key in self._api_cache:
            logger.debug(f"Using cached API surface for {package_name} {version}")
            return self._api_cache[cache_key]
        
        # Check disk cache
        cached_surface = await self._load_cached_api_surface(package_name, version)
        if cached_surface:
            logger.debug(f"Loaded API surface from disk cache for {package_name} {version}")
            self._api_cache[cache_key] = cached_surface
            return cached_surface
        
        try:
            logger.info(f"Analyzing API surface for {package_name} {version}")
            
            # Perform API surface extraction with timeout
            api_surface = await asyncio.wait_for(
                self.api_extractor.extract_from_package(package_name, version),
                timeout=self.timeout
            )
            
            # Cache the result
            self._api_cache[cache_key] = api_surface
            await self._save_cached_api_surface(api_surface)
            
            logger.info(
                f"API surface analysis complete for {package_name} {version}: "
                f"{len(api_surface.classes)} classes, {len(api_surface.functions)} functions, "
                f"{len(api_surface.constants)} constants"
            )
            
            return api_surface
            
        except asyncio.TimeoutError:
            raise MigrationAnalysisError(
                f"API surface analysis timed out for {package_name} {version} after {self.timeout}s"
            )
        except APIExtractionError as e:
            raise MigrationAnalysisError(f"Failed to analyze API surface for {package_name} {version}: {e}") from e
        except Exception as e:
            raise MigrationAnalysisError(
                f"Unexpected error analyzing API surface for {package_name} {version}: {e}"
            ) from e

    async def compare_versions(
        self, 
        package_name: str, 
        old_version: str, 
        new_version: str
    ) -> VersionComparison:
        """
        Compare API surfaces between two package versions with caching.
        
        Args:
            package_name: Name of the package to compare
            old_version: Older version to compare from
            new_version: Newer version to compare to
            
        Returns:
            VersionComparison containing all detected changes
            
        Raises:
            MigrationAnalysisError: If comparison fails
        """
        cache_key = f"{package_name}:{old_version}:{new_version}"
        
        # Check memory cache first
        if cache_key in self._comparison_cache:
            logger.debug(f"Using cached version comparison for {package_name} {old_version} -> {new_version}")
            return self._comparison_cache[cache_key]
        
        # Check disk cache
        cached_comparison = await self._load_cached_version_comparison(package_name, old_version, new_version)
        if cached_comparison:
            logger.debug(f"Loaded version comparison from disk cache for {package_name} {old_version} -> {new_version}")
            self._comparison_cache[cache_key] = cached_comparison
            return cached_comparison
        
        try:
            logger.info(f"Comparing versions for {package_name}: {old_version} -> {new_version}")
            
            # Get API surfaces for both versions (with caching)
            old_api_task = self.analyze_api_surface(package_name, old_version)
            new_api_task = self.analyze_api_surface(package_name, new_version)
            
            # Run API surface extraction concurrently
            old_api, new_api = await asyncio.gather(old_api_task, new_api_task)
            
            # Perform version comparison with timeout
            comparison = await asyncio.wait_for(
                self._perform_version_comparison(old_api, new_api),
                timeout=self.timeout
            )
            
            # Add timestamp
            comparison.analysis_timestamp = datetime.now(timezone.utc).isoformat()
            
            # Cache the result
            self._comparison_cache[cache_key] = comparison
            await self._save_cached_version_comparison(comparison)
            
            logger.info(
                f"Version comparison complete for {package_name} {old_version} -> {new_version}: "
                f"{len(comparison.breaking_changes)} breaking changes, "
                f"{len(comparison.additions)} additions, "
                f"{len(comparison.modifications)} modifications, "
                f"{len(comparison.deprecations)} deprecations"
            )
            
            return comparison
            
        except asyncio.TimeoutError:
            raise MigrationAnalysisError(
                f"Version comparison timed out for {package_name} {old_version} -> {new_version} after {self.timeout}s"
            )
        except VersionComparisonError as e:
            raise MigrationAnalysisError(
                f"Failed to compare versions for {package_name} {old_version} -> {new_version}: {e}"
            ) from e
        except Exception as e:
            raise MigrationAnalysisError(
                f"Unexpected error comparing versions for {package_name} {old_version} -> {new_version}: {e}"
            ) from e

    async def find_migration_resources(
        self, 
        package_name: str, 
        old_version: str, 
        new_version: str
    ) -> MigrationResources:
        """
        Find migration resources for upgrading between package versions with caching and fallback.
        
        Args:
            package_name: Name of the package
            old_version: Starting version
            new_version: Target version
            
        Returns:
            MigrationResources containing categorized migration information
            
        Raises:
            MigrationAnalysisError: If resource discovery fails completely
        """
        cache_key = f"{package_name}:{old_version}:{new_version}"
        
        # Check memory cache first
        if cache_key in self._resource_cache:
            logger.debug(f"Using cached migration resources for {package_name} {old_version} -> {new_version}")
            return self._resource_cache[cache_key]
        
        # Check disk cache
        cached_resources = await self._load_cached_migration_resources(package_name, old_version, new_version)
        if cached_resources:
            logger.debug(f"Loaded migration resources from disk cache for {package_name} {old_version} -> {new_version}")
            self._resource_cache[cache_key] = cached_resources
            return cached_resources
        
        try:
            logger.info(f"Finding migration resources for {package_name}: {old_version} -> {new_version}")
            
            # Perform migration resource discovery with timeout and fallback handling
            resources = await asyncio.wait_for(
                self._find_migration_resources_with_fallback(package_name, old_version, new_version),
                timeout=self.timeout
            )
            
            # Cache the result
            self._resource_cache[cache_key] = resources
            await self._save_cached_migration_resources(resources)
            
            total_resources = (
                len(resources.official_guides) + 
                len(resources.changelogs) + 
                len(resources.community_resources) + 
                len(resources.documentation_links)
            )
            
            logger.info(
                f"Migration resource discovery complete for {package_name} {old_version} -> {new_version}: "
                f"{total_resources} resources found"
            )
            
            return resources
            
        except asyncio.TimeoutError:
            logger.warning(
                f"Migration resource discovery timed out for {package_name} {old_version} -> {new_version}, "
                f"returning minimal fallback resources"
            )
            # Return minimal fallback resources on timeout
            return await self._create_fallback_resources(package_name, old_version, new_version)
        except MigrationResourceError as e:
            logger.warning(f"Migration resource discovery failed: {e}, returning fallback resources")
            # Return fallback resources on error
            return await self._create_fallback_resources(package_name, old_version, new_version)
        except Exception as e:
            logger.warning(f"Unexpected error in migration resource discovery: {e}, returning fallback resources")
            # Return fallback resources on unexpected error
            return await self._create_fallback_resources(package_name, old_version, new_version)

    async def _perform_version_comparison(self, old_api: APISurface, new_api: APISurface) -> VersionComparison:
        """
        Perform version comparison using the version comparator.
        
        Args:
            old_api: API surface of the older version
            new_api: API surface of the newer version
            
        Returns:
            VersionComparison with detected changes
        """
        return self.version_comparator.compare_api_surfaces(old_api, new_api)

    async def _find_migration_resources_with_fallback(
        self, 
        package_name: str, 
        old_version: str, 
        new_version: str
    ) -> MigrationResources:
        """
        Find migration resources with fallback handling.
        
        Args:
            package_name: Name of the package
            old_version: Starting version
            new_version: Target version
            
        Returns:
            MigrationResources with found resources
        """
        try:
            return await self.migration_finder.find_migration_resources(package_name, old_version, new_version)
        except Exception as e:
            logger.warning(f"Primary migration resource discovery failed: {e}, trying fallback")
            return await self._create_fallback_resources(package_name, old_version, new_version)

    async def _create_fallback_resources(
        self, 
        package_name: str, 
        old_version: str, 
        new_version: str
    ) -> MigrationResources:
        """
        Create minimal fallback migration resources when discovery fails.
        
        Args:
            package_name: Name of the package
            old_version: Starting version
            new_version: Target version
            
        Returns:
            MigrationResources with basic fallback information
        """
        from .migration_models import MigrationResource
        
        version_range = f"{old_version} -> {new_version}"
        
        resources = MigrationResources(
            package_name=package_name,
            version_range=version_range,
            search_timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Add basic PyPI project page
        resources.documentation_links.append(MigrationResource(
            title=f"{package_name} - PyPI Project Page",
            url=f"https://pypi.org/project/{package_name}/",
            type='documentation',
            description="PyPI project page - check description and project links for migration information",
            source='pypi'
        ))
        
        return resources

    def _get_cache_filename(self, prefix: str, *args: str) -> str:
        """
        Generate a cache filename from arguments.
        
        Args:
            prefix: Prefix for the filename
            *args: Arguments to hash for the filename
            
        Returns:
            Cache filename
        """
        if not self.cache_dir:
            return ""
        
        # Create a hash of the arguments for the filename
        content = ":".join(args)
        hash_obj = hashlib.md5(content.encode())
        return os.path.join(self.cache_dir, f"{prefix}_{hash_obj.hexdigest()}.json")

    async def _load_cached_api_surface(self, package_name: str, version: str) -> Optional[APISurface]:
        """Load cached API surface from disk."""
        if not self.cache_dir:
            return None
        
        try:
            filename = self._get_cache_filename("api_surface", package_name, version)
            if not os.path.exists(filename):
                return None
            
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if cache is still valid (24 hours)
            if 'extraction_timestamp' in data:
                cache_time = datetime.fromisoformat(data['extraction_timestamp'].replace('Z', '+00:00'))
                age = datetime.now(timezone.utc) - cache_time
                if age.total_seconds() > 24 * 3600:  # 24 hours
                    return None
            
            # Reconstruct APISurface from cached data
            from .migration_models import APIElement
            
            api_surface = APISurface(
                package_name=data['package_name'],
                version=data['version'],
                extraction_method=data.get('extraction_method', ''),
                extraction_timestamp=data.get('extraction_timestamp')
            )
            
            # Reconstruct API elements
            for cls_data in data.get('classes', []):
                api_surface.classes.append(APIElement(**cls_data))
            for func_data in data.get('functions', []):
                api_surface.functions.append(APIElement(**func_data))
            for const_data in data.get('constants', []):
                api_surface.constants.append(APIElement(**const_data))
            
            api_surface.modules = data.get('modules', [])
            
            return api_surface
            
        except Exception as e:
            logger.debug(f"Failed to load cached API surface: {e}")
            return None

    async def _save_cached_api_surface(self, api_surface: APISurface) -> None:
        """Save API surface to disk cache."""
        if not self.cache_dir:
            return
        
        try:
            filename = self._get_cache_filename("api_surface", api_surface.package_name, api_surface.version)
            
            # Convert to serializable format
            data = {
                'package_name': api_surface.package_name,
                'version': api_surface.version,
                'classes': [self._serialize_api_element(cls) for cls in api_surface.classes],
                'functions': [self._serialize_api_element(func) for func in api_surface.functions],
                'constants': [self._serialize_api_element(const) for const in api_surface.constants],
                'modules': api_surface.modules,
                'extraction_method': api_surface.extraction_method,
                'extraction_timestamp': api_surface.extraction_timestamp
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.debug(f"Failed to save API surface to cache: {e}")

    async def _load_cached_version_comparison(
        self, 
        package_name: str, 
        old_version: str, 
        new_version: str
    ) -> Optional[VersionComparison]:
        """Load cached version comparison from disk."""
        if not self.cache_dir:
            return None
        
        try:
            filename = self._get_cache_filename("version_comparison", package_name, old_version, new_version)
            if not os.path.exists(filename):
                return None
            
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if cache is still valid (24 hours)
            if 'analysis_timestamp' in data:
                cache_time = datetime.fromisoformat(data['analysis_timestamp'].replace('Z', '+00:00'))
                age = datetime.now(timezone.utc) - cache_time
                if age.total_seconds() > 24 * 3600:  # 24 hours
                    return None
            
            # Reconstruct VersionComparison from cached data
            from .migration_models import APIChange
            
            comparison = VersionComparison(
                package_name=data['package_name'],
                old_version=data['old_version'],
                new_version=data['new_version'],
                analysis_timestamp=data.get('analysis_timestamp')
            )
            
            # Reconstruct API changes
            for change_data in data.get('breaking_changes', []):
                comparison.breaking_changes.append(APIChange(**change_data))
            for change_data in data.get('additions', []):
                comparison.additions.append(APIChange(**change_data))
            for change_data in data.get('modifications', []):
                comparison.modifications.append(APIChange(**change_data))
            for change_data in data.get('deprecations', []):
                comparison.deprecations.append(APIChange(**change_data))
            
            comparison.dependency_changes = data.get('dependency_changes', [])
            
            return comparison
            
        except Exception as e:
            logger.debug(f"Failed to load cached version comparison: {e}")
            return None

    async def _save_cached_version_comparison(self, comparison: VersionComparison) -> None:
        """Save version comparison to disk cache."""
        if not self.cache_dir:
            return
        
        try:
            filename = self._get_cache_filename(
                "version_comparison", 
                comparison.package_name, 
                comparison.old_version, 
                comparison.new_version
            )
            
            # Convert to serializable format
            data = {
                'package_name': comparison.package_name,
                'old_version': comparison.old_version,
                'new_version': comparison.new_version,
                'breaking_changes': [self._serialize_api_change(change) for change in comparison.breaking_changes],
                'additions': [self._serialize_api_change(change) for change in comparison.additions],
                'modifications': [self._serialize_api_change(change) for change in comparison.modifications],
                'deprecations': [self._serialize_api_change(change) for change in comparison.deprecations],
                'dependency_changes': comparison.dependency_changes,
                'analysis_timestamp': comparison.analysis_timestamp
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.debug(f"Failed to save version comparison to cache: {e}")

    async def _load_cached_migration_resources(
        self, 
        package_name: str, 
        old_version: str, 
        new_version: str
    ) -> Optional[MigrationResources]:
        """Load cached migration resources from disk."""
        if not self.cache_dir:
            return None
        
        try:
            filename = self._get_cache_filename("migration_resources", package_name, old_version, new_version)
            if not os.path.exists(filename):
                return None
            
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check if cache is still valid (7 days for migration resources)
            if 'search_timestamp' in data:
                cache_time = datetime.fromisoformat(data['search_timestamp'].replace('Z', '+00:00'))
                age = datetime.now(timezone.utc) - cache_time
                if age.total_seconds() > 7 * 24 * 3600:  # 7 days
                    return None
            
            # Reconstruct MigrationResources from cached data
            from .migration_models import MigrationResource
            
            resources = MigrationResources(
                package_name=data['package_name'],
                version_range=data['version_range'],
                search_timestamp=data.get('search_timestamp')
            )
            
            # Reconstruct migration resources
            for resource_data in data.get('official_guides', []):
                resources.official_guides.append(MigrationResource(**resource_data))
            for resource_data in data.get('changelogs', []):
                resources.changelogs.append(MigrationResource(**resource_data))
            for resource_data in data.get('community_resources', []):
                resources.community_resources.append(MigrationResource(**resource_data))
            for resource_data in data.get('documentation_links', []):
                resources.documentation_links.append(MigrationResource(**resource_data))
            
            return resources
            
        except Exception as e:
            logger.debug(f"Failed to load cached migration resources: {e}")
            return None

    async def _save_cached_migration_resources(self, resources: MigrationResources) -> None:
        """Save migration resources to disk cache."""
        if not self.cache_dir:
            return
        
        try:
            # Extract version range components for filename
            version_parts = resources.version_range.split(' -> ')
            old_version = version_parts[0] if len(version_parts) > 0 else "unknown"
            new_version = version_parts[1] if len(version_parts) > 1 else "unknown"
            
            filename = self._get_cache_filename(
                "migration_resources", 
                resources.package_name, 
                old_version, 
                new_version
            )
            
            # Convert to serializable format
            data = {
                'package_name': resources.package_name,
                'version_range': resources.version_range,
                'official_guides': [self._serialize_migration_resource(res) for res in resources.official_guides],
                'changelogs': [self._serialize_migration_resource(res) for res in resources.changelogs],
                'community_resources': [self._serialize_migration_resource(res) for res in resources.community_resources],
                'documentation_links': [self._serialize_migration_resource(res) for res in resources.documentation_links],
                'search_timestamp': resources.search_timestamp
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.debug(f"Failed to save migration resources to cache: {e}")

    def _serialize_api_element(self, element) -> Dict[str, Any]:
        """Serialize an APIElement to a dictionary."""
        return {
            'name': element.name,
            'type': element.type,
            'signature': element.signature,
            'docstring': element.docstring,
            'is_deprecated': element.is_deprecated,
            'deprecation_message': element.deprecation_message,
            'source_location': element.source_location,
            'parent_class': element.parent_class
        }

    def _serialize_api_change(self, change) -> Dict[str, Any]:
        """Serialize an APIChange to a dictionary."""
        return {
            'element_name': change.element_name,
            'change_type': change.change_type,
            'old_signature': change.old_signature,
            'new_signature': change.new_signature,
            'impact_level': change.impact_level,
            'description': change.description,
            'element_type': change.element_type
        }

    def _serialize_migration_resource(self, resource) -> Dict[str, Any]:
        """Serialize a MigrationResource to a dictionary."""
        return {
            'title': resource.title,
            'url': resource.url,
            'type': resource.type,
            'version_range': resource.version_range,
            'description': resource.description,
            'source': resource.source
        }

    async def cleanup(self) -> None:
        """Clean up resources and close connections."""
        try:
            # Clean up API extractor temporary directories
            if hasattr(self.api_extractor, 'cleanup_temp_directories'):
                self.api_extractor.cleanup_temp_directories()
            
            # Close migration finder HTTP client
            if hasattr(self.migration_finder, 'close'):
                await self.migration_finder.close()
                
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()