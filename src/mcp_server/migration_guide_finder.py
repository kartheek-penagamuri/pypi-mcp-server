"""
Migration resource discovery functionality.

This module provides the MigrationGuideFinder class for locating migration documentation,
changelogs, and upgrade guides for Python packages across different versions.
"""

from __future__ import annotations

import re
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .migration_models import MigrationResource, MigrationResources
from .errors import MigrationResourceError, NetworkError
from .package_manager import PackageManager


class MigrationGuideFinder:
    """
    Discovers migration resources for Python packages including changelogs,
    migration guides, and upgrade documentation from various sources.
    """

    def __init__(self, package_manager: Optional[PackageManager] = None, timeout: float = 10.0):
        self.package_manager = package_manager or PackageManager()
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": "pypi-mcp-server/0.1"},
            follow_redirects=True
        )

    async def find_migration_resources(
        self, 
        package_name: str, 
        old_version: str, 
        new_version: str
    ) -> MigrationResources:
        """
        Find migration resources for upgrading from old_version to new_version.
        
        Args:
            package_name: Name of the package
            old_version: Starting version
            new_version: Target version
            
        Returns:
            MigrationResources containing categorized migration information
        """
        version_range = f"{old_version} -> {new_version}"
        
        try:
            # Get package metadata to extract URLs
            package_info = self.package_manager.get_package_info(package_name)
            
            # Initialize result structure
            resources = MigrationResources(
                package_name=package_name,
                version_range=version_range,
                search_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            # Extract URLs from package metadata
            urls = await self._extract_urls_from_metadata(package_name)
            
            # Search for resources from different sources
            tasks = [
                self._find_github_resources(urls.get('github'), old_version, new_version),
                self._find_readthedocs_resources(urls.get('readthedocs')),
                self._find_pypi_resources(package_name),
                self._find_changelog_resources(urls.get('homepage'), urls.get('repository'))
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Merge results from all sources
            for result in results:
                if isinstance(result, Exception):
                    continue  # Skip failed searches, don't fail the entire operation
                if isinstance(result, list):
                    for resource in result:
                        self._categorize_resource(resource, resources)
            
            # Add fallback resources if no official ones found
            if not any([resources.official_guides, resources.changelogs, resources.documentation_links]):
                fallback_resources = await self._find_fallback_resources(package_name, old_version, new_version)
                for resource in fallback_resources:
                    self._categorize_resource(resource, resources)
            
            return resources
            
        except Exception as e:
            raise MigrationResourceError(f"Failed to find migration resources for {package_name}: {e}") from e

    async def _extract_urls_from_metadata(self, package_name: str) -> Dict[str, str]:
        """Extract relevant URLs from package metadata."""
        try:
            package_info = self.package_manager.get_package_info(package_name)
            urls = {}
            
            # Check homepage and repository URLs
            if package_info.homepage:
                urls['homepage'] = package_info.homepage
            if package_info.repository:
                urls['repository'] = package_info.repository
            
            # Try to get additional URLs from PyPI project_urls
            try:
                pypi_data = self.package_manager.client.get_project(package_name)
                project_urls = pypi_data.get('info', {}).get('project_urls', {}) or {}
                
                for key, url in project_urls.items():
                    key_lower = key.lower()
                    if 'github' in key_lower or 'source' in key_lower or 'repository' in key_lower:
                        urls['github'] = url
                    elif 'doc' in key_lower or 'readthedocs' in key_lower:
                        urls['readthedocs'] = url
                    elif 'changelog' in key_lower or 'history' in key_lower:
                        urls['changelog'] = url
                        
            except Exception:
                pass  # Continue with what we have
            
            # Detect GitHub URLs (prefer repository URLs over specific file URLs)
            github_urls = []
            for url_key, url in list(urls.items()):
                if 'github.com' in url:
                    github_urls.append(url)
                elif 'readthedocs' in url:
                    urls['readthedocs'] = url
            
            # Choose the best GitHub URL (prefer repository root over specific files)
            if github_urls:
                # Sort by length to prefer shorter URLs (likely repository roots)
                github_urls.sort(key=len)
                urls['github'] = github_urls[0]
            
            return urls
            
        except Exception as e:
            # Return empty dict if metadata extraction fails
            return {}

    async def _find_github_resources(
        self, 
        github_url: Optional[str], 
        old_version: str, 
        new_version: str
    ) -> List[MigrationResource]:
        """Find migration resources from GitHub repository."""
        if not github_url:
            return []
        
        resources = []
        
        try:
            # Extract owner/repo from GitHub URL
            match = re.search(r'github\.com/([^/]+)/([^/]+)', github_url)
            if not match:
                return []
            
            owner, repo = match.groups()
            repo = repo.rstrip('.git')
            
            # Check GitHub releases for changelogs
            releases_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
            try:
                response = await self._client.get(releases_url)
                if response.status_code == 200:
                    releases = response.json()
                    for release in releases[:10]:  # Check last 10 releases
                        tag_name = release.get('tag_name', '')
                        if self._is_version_relevant(tag_name, old_version, new_version):
                            resources.append(MigrationResource(
                                title=f"Release {tag_name}",
                                url=release.get('html_url', ''),
                                type='changelog',
                                version_range=tag_name,
                                description=release.get('name', '') or f"Release notes for {tag_name}",
                                source='github'
                            ))
            except Exception:
                pass
            
            # Look for common changelog files
            changelog_files = [
                'CHANGELOG.md', 'CHANGELOG.rst', 'CHANGELOG.txt',
                'HISTORY.md', 'HISTORY.rst', 'HISTORY.txt',
                'CHANGES.md', 'CHANGES.rst', 'CHANGES.txt',
                'NEWS.md', 'NEWS.rst', 'NEWS.txt'
            ]
            
            for filename in changelog_files:
                file_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{filename}"
                try:
                    response = await self._client.get(file_url)
                    if response.status_code == 200:
                        resources.append(MigrationResource(
                            title=f"{filename}",
                            url=f"https://github.com/{owner}/{repo}/blob/main/{filename}",
                            type='changelog',
                            version_range=f"{old_version} -> {new_version}",
                            description=f"Changelog file from repository",
                            source='github'
                        ))
                        break  # Found one changelog, don't need to check others
                except Exception:
                    continue
            
            # Look for migration guides in docs directory
            docs_url = f"https://api.github.com/repos/{owner}/{repo}/contents/docs"
            try:
                response = await self._client.get(docs_url)
                if response.status_code == 200:
                    docs_files = response.json()
                    for file_info in docs_files:
                        filename = file_info.get('name', '').lower()
                        if any(keyword in filename for keyword in ['migration', 'upgrade', 'breaking']):
                            resources.append(MigrationResource(
                                title=f"Migration Guide: {file_info.get('name')}",
                                url=file_info.get('html_url', ''),
                                type='official_guide',
                                version_range=f"{old_version} -> {new_version}",
                                description="Migration documentation from repository",
                                source='github'
                            ))
            except Exception:
                pass
                
        except Exception:
            pass  # Don't fail if GitHub search fails
        
        return resources

    async def _find_readthedocs_resources(self, readthedocs_url: Optional[str]) -> List[MigrationResource]:
        """Find migration resources from ReadTheDocs documentation."""
        if not readthedocs_url:
            return []
        
        resources = []
        
        try:
            # Try to find migration/upgrade pages
            migration_paths = [
                '/en/latest/migration/',
                '/en/latest/upgrading/',
                '/en/latest/changelog/',
                '/en/stable/migration/',
                '/en/stable/upgrading/',
                '/en/stable/changelog/'
            ]
            
            base_url = readthedocs_url.rstrip('/')
            
            for path in migration_paths:
                try:
                    test_url = base_url + path
                    response = await self._client.get(test_url)
                    if response.status_code == 200:
                        # Parse the page to get title
                        soup = BeautifulSoup(response.text, 'html.parser')
                        title_elem = soup.find('title') or soup.find('h1')
                        title = title_elem.get_text().strip() if title_elem else f"Documentation: {path.split('/')[-2]}"
                        
                        resource_type = 'official_guide' if 'migration' in path or 'upgrading' in path else 'changelog'
                        
                        resources.append(MigrationResource(
                            title=title,
                            url=test_url,
                            type=resource_type,
                            description=f"Documentation from ReadTheDocs",
                            source='readthedocs'
                        ))
                except Exception:
                    continue
                    
        except Exception:
            pass  # Don't fail if ReadTheDocs search fails
        
        return resources

    async def _find_pypi_resources(self, package_name: str) -> List[MigrationResource]:
        """Find migration resources from PyPI package information."""
        resources = []
        
        try:
            pypi_data = self.package_manager.client.get_project(package_name)
            info = pypi_data.get('info', {})
            
            # Check long description for migration information
            long_description = info.get('description', '') or ''
            if long_description and any(keyword in long_description.lower() for keyword in 
                                     ['migration', 'upgrade', 'breaking change', 'changelog']):
                resources.append(MigrationResource(
                    title=f"{package_name} - Package Description",
                    url=f"https://pypi.org/project/{package_name}/",
                    type='documentation',
                    description="Package description contains migration information",
                    source='pypi'
                ))
            
            # Check project URLs for relevant links
            project_urls = info.get('project_urls', {}) or {}
            for key, url in project_urls.items():
                key_lower = key.lower()
                if any(keyword in key_lower for keyword in ['changelog', 'history', 'migration', 'upgrade']):
                    resources.append(MigrationResource(
                        title=f"{key}",
                        url=url,
                        type='changelog' if 'changelog' in key_lower or 'history' in key_lower else 'official_guide',
                        description=f"Link from PyPI project URLs: {key}",
                        source='pypi'
                    ))
                    
        except Exception:
            pass  # Don't fail if PyPI search fails
        
        return resources

    async def _find_changelog_resources(
        self, 
        homepage_url: Optional[str], 
        repository_url: Optional[str]
    ) -> List[MigrationResource]:
        """Find changelog resources from homepage and repository URLs."""
        resources = []
        urls_to_check = []
        
        if homepage_url:
            urls_to_check.append(homepage_url)
        if repository_url and repository_url != homepage_url:
            urls_to_check.append(repository_url)
        
        for base_url in urls_to_check:
            try:
                # Try common changelog paths
                changelog_paths = [
                    '/changelog', '/changelog.html', '/changelog/',
                    '/history', '/history.html', '/history/',
                    '/changes', '/changes.html', '/changes/',
                    '/releases', '/releases.html', '/releases/'
                ]
                
                for path in changelog_paths:
                    try:
                        test_url = urljoin(base_url, path)
                        response = await self._client.get(test_url)
                        if response.status_code == 200:
                            resources.append(MigrationResource(
                                title=f"Changelog - {urlparse(base_url).netloc}",
                                url=test_url,
                                type='changelog',
                                description=f"Changelog found at {path}",
                                source='official_docs'
                            ))
                            break  # Found one, don't need to check others for this base URL
                    except Exception:
                        continue
                        
            except Exception:
                continue
        
        return resources

    async def _find_fallback_resources(
        self, 
        package_name: str, 
        old_version: str, 
        new_version: str
    ) -> List[MigrationResource]:
        """Find fallback resources when official documentation is not available."""
        resources = []
        
        # Add generic PyPI project page as fallback
        resources.append(MigrationResource(
            title=f"{package_name} - PyPI Project Page",
            url=f"https://pypi.org/project/{package_name}/",
            type='documentation',
            description="PyPI project page - check description and project links for migration information",
            source='pypi'
        ))
        
        # Suggest common community resources
        resources.append(MigrationResource(
            title=f"Search GitHub for {package_name} migration guides",
            url=f"https://github.com/search?q={package_name}+migration+upgrade&type=repositories",
            type='community_guide',
            description="GitHub search for community migration guides and discussions",
            source='github'
        ))
        
        resources.append(MigrationResource(
            title=f"Stack Overflow discussions about {package_name} upgrades",
            url=f"https://stackoverflow.com/search?q={package_name}+upgrade+migration",
            type='community_guide',
            description="Community discussions about package upgrades and migrations",
            source='stackoverflow'
        ))
        
        return resources

    def _categorize_resource(self, resource: MigrationResource, resources: MigrationResources) -> None:
        """Categorize a migration resource into the appropriate list."""
        if resource.type == 'official_guide':
            resources.official_guides.append(resource)
        elif resource.type == 'changelog':
            resources.changelogs.append(resource)
        elif resource.type == 'community_guide':
            resources.community_resources.append(resource)
        elif resource.type == 'documentation':
            resources.documentation_links.append(resource)
        else:
            # Default to documentation links for unknown types
            resources.documentation_links.append(resource)

    def _is_version_relevant(self, tag_name: str, old_version: str, new_version: str) -> bool:
        """Check if a version tag is relevant for the migration."""
        # Simple heuristic: if the tag contains version-like patterns
        # and might be between old and new versions
        version_pattern = r'v?(\d+\.?\d*\.?\d*)'
        match = re.search(version_pattern, tag_name)
        if not match:
            return False
        
        # For now, include all version tags - more sophisticated version
        # comparison could be added here using packaging.version
        return True

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()