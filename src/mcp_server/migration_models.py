"""
Data models for package migration analysis functionality.

This module contains data classes for representing API surfaces, version comparisons,
and migration resources used by the migration analysis tools.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class APIElement:
    """Represents a single element of a package's public API."""
    name: str
    type: str  # 'class', 'function', 'method', 'property', 'constant'
    signature: str
    docstring: str = ""
    is_deprecated: bool = False
    deprecation_message: str = ""
    source_location: str = ""
    parent_class: str = ""  # For methods and properties


@dataclass
class APISurface:
    """Represents the complete public API surface of a package version."""
    package_name: str
    version: str
    classes: List[APIElement] = field(default_factory=list)
    functions: List[APIElement] = field(default_factory=list)
    constants: List[APIElement] = field(default_factory=list)
    modules: List[str] = field(default_factory=list)
    extraction_method: str = ""  # 'runtime', 'ast', 'hybrid'
    extraction_timestamp: Optional[str] = None


@dataclass
class APIChange:
    """Represents a change in the API between two versions."""
    element_name: str
    change_type: str  # 'added', 'removed', 'modified', 'deprecated'
    old_signature: str = ""
    new_signature: str = ""
    impact_level: str = ""  # 'breaking', 'compatible', 'enhancement'
    description: str = ""
    element_type: str = ""  # 'class', 'function', 'method', etc.


@dataclass
class VersionComparison:
    """Results of comparing API surfaces between two package versions."""
    package_name: str
    old_version: str
    new_version: str
    breaking_changes: List[APIChange] = field(default_factory=list)
    additions: List[APIChange] = field(default_factory=list)
    modifications: List[APIChange] = field(default_factory=list)
    deprecations: List[APIChange] = field(default_factory=list)
    dependency_changes: List[str] = field(default_factory=list)
    analysis_timestamp: Optional[str] = None


@dataclass
class MigrationResource:
    """Represents a single migration resource (guide, changelog, etc.)."""
    title: str
    url: str
    type: str  # 'official_guide', 'changelog', 'community_guide', 'blog_post', 'documentation'
    version_range: str = ""
    description: str = ""
    source: str = ""  # 'github', 'readthedocs', 'pypi', 'official_docs'


@dataclass
class MigrationResources:
    """Collection of migration resources for a package version transition."""
    package_name: str
    version_range: str
    official_guides: List[MigrationResource] = field(default_factory=list)
    changelogs: List[MigrationResource] = field(default_factory=list)
    community_resources: List[MigrationResource] = field(default_factory=list)
    documentation_links: List[MigrationResource] = field(default_factory=list)
    search_timestamp: Optional[str] = None