"""
Version Comparator for analyzing differences between package API surfaces.

This module provides functionality to compare API surfaces between different
versions of Python packages, identifying breaking changes, additions, removals,
modifications, and deprecations.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Tuple

from .api_surface_extractor import APISurfaceExtractor
from .errors import VersionComparisonError
from .migration_models import APIChange, APIElement, APISurface, VersionComparison
from .package_manager import PackageManager

logger = logging.getLogger(__name__)


class VersionComparator:
    """
    Analyzes differences between API surfaces of different package versions.
    
    Provides methods to detect API additions, removals, signature modifications,
    breaking changes, and deprecation tracking across versions.
    """

    def __init__(self, package_manager: PackageManager, api_extractor: Optional[APISurfaceExtractor] = None):
        """
        Initialize the version comparator.
        
        Args:
            package_manager: PackageManager instance for retrieving package information
            api_extractor: APISurfaceExtractor instance for analyzing API surfaces
        """
        self.package_manager = package_manager
        self.api_extractor = api_extractor or APISurfaceExtractor()

    def compare_api_surfaces(self, old_api: APISurface, new_api: APISurface) -> VersionComparison:
        """
        Compare two API surfaces and return a detailed comparison.
        
        Args:
            old_api: API surface of the older version
            new_api: API surface of the newer version
            
        Returns:
            VersionComparison containing all detected changes
            
        Raises:
            VersionComparisonError: If comparison cannot be performed
        """
        # Validate that we're comparing the same package
        if old_api.package_name != new_api.package_name:
            raise VersionComparisonError(
                f"Cannot compare different packages: {old_api.package_name} vs {new_api.package_name}"
            )
        
        logger.info(f"Comparing {old_api.package_name} versions {old_api.version} -> {new_api.version}")
        
        # Create comparison result
        comparison = VersionComparison(
            package_name=old_api.package_name,
            old_version=old_api.version,
            new_version=new_api.version
        )
        
        # Create element maps for efficient comparison
        old_elements = self._create_element_map(old_api)
        new_elements = self._create_element_map(new_api)
        
        # Detect different types of changes
        comparison.additions = self.detect_additions(old_api, new_api)
        comparison.modifications = self._detect_modifications(old_elements, new_elements)
        comparison.deprecations = self.detect_deprecations(old_api, new_api)
        
        # Detect removals and classify as breaking changes
        removals = self._detect_removals(old_elements, new_elements)
        
        # Identify breaking changes from modifications
        breaking_modifications = self._identify_breaking_changes(comparison.modifications)
        
        # Combine all breaking changes
        comparison.breaking_changes = removals + breaking_modifications
        
        # Analyze dependency changes
        comparison.dependency_changes = self._analyze_dependency_changes(
            old_api.package_name, old_api.version, new_api.version
        )
        
        logger.info(
            f"Version comparison complete: {len(comparison.breaking_changes)} breaking changes, "
            f"{len(comparison.additions)} additions, {len(comparison.modifications)} modifications, "
            f"{len(comparison.deprecations)} deprecations"
        )
        
        return comparison

    async def compare_versions(
        self, 
        package_name: str, 
        old_version: str, 
        new_version: str
    ) -> VersionComparison:
        """
        Compare API surfaces between two package versions.
        
        Args:
            package_name: Name of the package to compare
            old_version: Older version to compare from
            new_version: Newer version to compare to
            
        Returns:
            VersionComparison containing all detected changes
            
        Raises:
            VersionComparisonError: If comparison cannot be performed
        """
        try:
            logger.info(f"Comparing {package_name} versions {old_version} -> {new_version}")
            
            # Extract API surfaces for both versions
            old_api = await self.api_extractor.extract_from_package(package_name, old_version)
            new_api = await self.api_extractor.extract_from_package(package_name, new_version)
            
            # Perform comparison analysis
            comparison = VersionComparison(
                package_name=package_name,
                old_version=old_version,
                new_version=new_version
            )
            
            # Detect different types of changes
            comparison.additions = self.detect_additions(old_api, new_api)
            comparison.breaking_changes = self.detect_breaking_changes(old_api, new_api)
            comparison.modifications = self.detect_modifications(old_api, new_api)
            comparison.deprecations = self.detect_deprecations(old_api, new_api)
            
            # Analyze dependency changes
            comparison.dependency_changes = await self.detect_dependency_changes(
                package_name, old_version, new_version
            )
            
            logger.info(
                f"Version comparison complete: {len(comparison.breaking_changes)} breaking changes, "
                f"{len(comparison.additions)} additions, {len(comparison.modifications)} modifications, "
                f"{len(comparison.deprecations)} deprecations"
            )
            
            return comparison
            
        except Exception as e:
            raise VersionComparisonError(
                f"Failed to compare {package_name} versions {old_version} -> {new_version}: {e}"
            ) from e

    def detect_additions(self, old_api: APISurface, new_api: APISurface) -> List[APIChange]:
        """
        Detect API elements that were added in the new version.
        
        Args:
            old_api: API surface of the older version
            new_api: API surface of the newer version
            
        Returns:
            List of APIChange objects representing additions
        """
        additions = []
        
        # Create lookup sets for old API elements
        old_elements = self._create_element_lookup(old_api)
        
        # Check for new elements in each category
        for element in new_api.classes + new_api.functions + new_api.constants:
            element_key = self._get_element_key(element)
            
            if element_key not in old_elements:
                additions.append(APIChange(
                    element_name=element.name,
                    change_type="added",
                    old_signature="",
                    new_signature=element.signature,
                    impact_level="enhancement",
                    description=f"New {element.type} '{element.name}' added",
                    element_type=element.type
                ))
        
        return additions

    def detect_breaking_changes(self, old_api: APISurface, new_api: APISurface) -> List[APIChange]:
        """
        Detect breaking changes between API versions.
        
        Breaking changes include:
        - Removed public API elements
        - Modified method signatures that break compatibility
        - Changed return types or parameter requirements
        
        Args:
            old_api: API surface of the older version
            new_api: API surface of the newer version
            
        Returns:
            List of APIChange objects representing breaking changes
        """
        breaking_changes = []
        
        # Create lookup dictionaries for efficient comparison
        old_elements = self._create_element_dict(old_api)
        new_elements = self._create_element_dict(new_api)
        
        # Check for removed elements (breaking changes)
        for element_key, old_element in old_elements.items():
            if element_key not in new_elements:
                breaking_changes.append(APIChange(
                    element_name=old_element.name,
                    change_type="removed",
                    old_signature=old_element.signature,
                    new_signature="",
                    impact_level="breaking",
                    description=f"Removed {old_element.type} '{old_element.name}'",
                    element_type=old_element.type
                ))
        
        # Check for signature changes that might be breaking
        for element_key, old_element in old_elements.items():
            if element_key in new_elements:
                new_element = new_elements[element_key]
                
                # Compare signatures for potential breaking changes
                if self._is_breaking_signature_change(old_element, new_element):
                    breaking_changes.append(APIChange(
                        element_name=old_element.name,
                        change_type="modified",
                        old_signature=old_element.signature,
                        new_signature=new_element.signature,
                        impact_level="breaking",
                        description=f"Breaking signature change in {old_element.type} '{old_element.name}'",
                        element_type=old_element.type
                    ))
        
        return breaking_changes

    def detect_modifications(self, old_api: APISurface, new_api: APISurface) -> List[APIChange]:
        """
        Detect non-breaking modifications between API versions.
        
        This includes signature changes that are backward compatible,
        docstring updates, and other non-breaking changes.
        
        Args:
            old_api: API surface of the older version
            new_api: API surface of the newer version
            
        Returns:
            List of APIChange objects representing modifications
        """
        modifications = []
        
        # Create lookup dictionaries
        old_elements = self._create_element_dict(old_api)
        new_elements = self._create_element_dict(new_api)
        
        # Check for non-breaking modifications
        for element_key, old_element in old_elements.items():
            if element_key in new_elements:
                new_element = new_elements[element_key]
                
                # Check for signature changes that are not breaking
                if (old_element.signature != new_element.signature and 
                    not self._is_breaking_signature_change(old_element, new_element)):
                    
                    modifications.append(APIChange(
                        element_name=old_element.name,
                        change_type="modified",
                        old_signature=old_element.signature,
                        new_signature=new_element.signature,
                        impact_level="compatible",
                        description=f"Compatible signature change in {old_element.type} '{old_element.name}'",
                        element_type=old_element.type
                    ))
                
                # Check for docstring changes
                elif old_element.docstring != new_element.docstring:
                    modifications.append(APIChange(
                        element_name=old_element.name,
                        change_type="modified",
                        old_signature=old_element.signature,
                        new_signature=new_element.signature,
                        impact_level="compatible",
                        description=f"Documentation updated for {old_element.type} '{old_element.name}'",
                        element_type=old_element.type
                    ))
        
        return modifications

    def detect_deprecations(self, old_api: APISurface, new_api: APISurface) -> List[APIChange]:
        """
        Detect newly deprecated functionality between versions.
        
        Args:
            old_api: API surface of the older version
            new_api: API surface of the newer version
            
        Returns:
            List of APIChange objects representing new deprecations
        """
        deprecations = []
        
        # Create lookup dictionaries
        old_elements = self._create_element_dict(old_api)
        new_elements = self._create_element_dict(new_api)
        
        # Check for newly deprecated elements
        for element_key, old_element in old_elements.items():
            if element_key in new_elements:
                new_element = new_elements[element_key]
                
                # Check if element became deprecated
                if not old_element.is_deprecated and new_element.is_deprecated:
                    deprecations.append(APIChange(
                        element_name=old_element.name,
                        change_type="deprecated",
                        old_signature=old_element.signature,
                        new_signature=new_element.signature,
                        impact_level="compatible",
                        description=(
                            f"Deprecated {old_element.type} '{old_element.name}': "
                            f"{new_element.deprecation_message}"
                        ),
                        element_type=old_element.type
                    ))
        
        return deprecations

    async def detect_dependency_changes(
        self, 
        package_name: str, 
        old_version: str, 
        new_version: str
    ) -> List[str]:
        """
        Detect changes in package dependencies between versions.
        
        Args:
            package_name: Name of the package
            old_version: Older version
            new_version: Newer version
            
        Returns:
            List of strings describing dependency changes
        """
        dependency_changes = []
        
        try:
            # Get package info for both versions
            old_info = self.package_manager.get_package_info(package_name, old_version)
            new_info = self.package_manager.get_package_info(package_name, new_version)
            
            # Create dependency lookup dictionaries
            old_deps = {dep.name: dep for dep in old_info.dependencies}
            new_deps = {dep.name: dep for dep in new_info.dependencies}
            
            # Check for removed dependencies
            for dep_name in old_deps:
                if dep_name not in new_deps:
                    dependency_changes.append(f"Removed dependency: {dep_name}")
            
            # Check for added dependencies
            for dep_name in new_deps:
                if dep_name not in old_deps:
                    new_dep = new_deps[dep_name]
                    dependency_changes.append(
                        f"Added dependency: {dep_name} {new_dep.version_spec}"
                    )
            
            # Check for version constraint changes
            for dep_name in old_deps:
                if dep_name in new_deps:
                    old_dep = old_deps[dep_name]
                    new_dep = new_deps[dep_name]
                    
                    if old_dep.version_spec != new_dep.version_spec:
                        dependency_changes.append(
                            f"Changed dependency version: {dep_name} "
                            f"{old_dep.version_spec} -> {new_dep.version_spec}"
                        )
            
        except Exception as e:
            logger.warning(f"Failed to analyze dependency changes: {e}")
            dependency_changes.append("Could not analyze dependency changes")
        
        return dependency_changes

    def _create_element_map(self, api_surface: APISurface) -> Dict[str, APIElement]:
        """
        Create a dictionary mapping element names to elements, handling methods with class prefixes.
        
        Args:
            api_surface: API surface to create map for
            
        Returns:
            Dictionary mapping element names to APIElement objects
        """
        element_map = {}
        
        for element in api_surface.classes + api_surface.functions + api_surface.constants:
            if element.parent_class:
                # For methods, use ClassName.method_name as key
                key = f"{element.parent_class}.{element.name}"
            else:
                # For top-level elements, use just the name
                key = element.name
            
            element_map[key] = element
        
        return element_map

    def _detect_removals(self, old_elements: Dict[str, APIElement], new_elements: Dict[str, APIElement]) -> List[APIChange]:
        """
        Detect API elements that were removed (breaking changes).
        
        Args:
            old_elements: Dictionary of old API elements
            new_elements: Dictionary of new API elements
            
        Returns:
            List of APIChange objects representing removals
        """
        removals = []
        
        for element_name, old_element in old_elements.items():
            if element_name not in new_elements:
                removals.append(APIChange(
                    element_name=old_element.name,
                    change_type="removed",
                    old_signature=old_element.signature,
                    new_signature="",
                    impact_level="breaking",
                    description=f"Removed {old_element.type} '{old_element.name}'",
                    element_type=old_element.type
                ))
        
        return removals

    def _detect_modifications(self, old_elements: Dict[str, APIElement], new_elements: Dict[str, APIElement]) -> List[APIChange]:
        """
        Detect modifications to existing API elements.
        
        Args:
            old_elements: Dictionary of old API elements
            new_elements: Dictionary of new API elements
            
        Returns:
            List of APIChange objects representing modifications
        """
        modifications = []
        
        for element_name, old_element in old_elements.items():
            if element_name in new_elements:
                new_element = new_elements[element_name]
                
                # Check for signature changes
                if old_element.signature != new_element.signature:
                    # Assess the impact of the change
                    if old_element.type in ["function", "method", "async_function", "async_method"]:
                        impact = self._assess_function_signature_change(old_element.signature, new_element.signature)
                    elif old_element.type == "class":
                        impact = self._assess_class_signature_change(old_element.signature, new_element.signature)
                    else:
                        impact = "compatible"  # Default for constants and other types
                    
                    modifications.append(APIChange(
                        element_name=old_element.name,
                        change_type="modified",
                        old_signature=old_element.signature,
                        new_signature=new_element.signature,
                        impact_level=impact,
                        description=f"Modified {old_element.type} '{old_element.name}'",
                        element_type=old_element.type
                    ))
                
                # Check for docstring changes (non-breaking)
                elif old_element.docstring != new_element.docstring:
                    modifications.append(APIChange(
                        element_name=old_element.name,
                        change_type="modified",
                        old_signature=old_element.signature,
                        new_signature=new_element.signature,
                        impact_level="compatible",
                        description=f"Documentation updated for {old_element.type} '{old_element.name}'",
                        element_type=old_element.type
                    ))
        
        return modifications

    def _identify_breaking_changes(self, changes: List[APIChange]) -> List[APIChange]:
        """
        Identify breaking changes from a list of changes.
        
        Args:
            changes: List of API changes to filter
            
        Returns:
            List of changes that are breaking
        """
        return [change for change in changes if change.impact_level == "breaking"]

    def _assess_function_signature_change(self, old_signature: str, new_signature: str) -> str:
        """
        Assess the impact level of a function signature change.
        
        Args:
            old_signature: Original function signature
            new_signature: New function signature
            
        Returns:
            Impact level: "breaking", "enhancement", or "compatible"
        """
        try:
            old_params = self._extract_parameters(old_signature)
            new_params = self._extract_parameters(new_signature)
            
            # Count required parameters (those without defaults)
            old_required = sum(1 for p in old_params if not p.get('has_default', False) and not p['name'].startswith('*'))
            new_required = sum(1 for p in new_params if not p.get('has_default', False) and not p['name'].startswith('*'))
            
            # If more required parameters were added, it's breaking
            if new_required > old_required:
                return "breaking"
            
            # If required parameters were removed, it's breaking
            if new_required < old_required:
                return "breaking"
            
            # Check if any existing parameters lost their default values
            old_param_names = {p['name']: p for p in old_params}
            new_param_names = {p['name']: p for p in new_params}
            
            for param_name, old_param in old_param_names.items():
                if param_name in new_param_names:
                    new_param = new_param_names[param_name]
                    # If a parameter had a default but now doesn't, it's breaking
                    if old_param.get('has_default', False) and not new_param.get('has_default', False):
                        return "breaking"
            
            # If we added optional parameters or made other compatible changes
            if len(new_params) > len(old_params):
                return "enhancement"
            
            return "compatible"
            
        except Exception:
            # If we can't parse the signatures, assume it might be breaking
            return "breaking"

    def _assess_class_signature_change(self, old_signature: str, new_signature: str) -> str:
        """
        Assess the impact level of a class signature change.
        
        Args:
            old_signature: Original class signature
            new_signature: New class signature
            
        Returns:
            Impact level: "breaking", "enhancement", or "compatible"
        """
        try:
            old_bases = self._extract_base_classes(old_signature)
            new_bases = self._extract_base_classes(new_signature)
            
            # If base classes were removed, it might be breaking
            if len(new_bases) < len(old_bases):
                return "breaking"
            
            # If base classes were added, it's usually an enhancement
            if len(new_bases) > len(old_bases):
                return "enhancement"
            
            # If base classes changed, it might be breaking
            if set(old_bases) != set(new_bases):
                return "breaking"
            
            return "compatible"
            
        except Exception:
            return "compatible"

    def _extract_parameters(self, signature: str) -> List[Dict[str, any]]:
        """
        Extract parameter information from a function signature.
        
        Args:
            signature: Function signature string
            
        Returns:
            List of parameter dictionaries with name and has_default keys
        """
        try:
            # Extract the parameter part from the signature
            # Example: "def func(a: str, b: int = 10) -> str" -> "a: str, b: int = 10"
            start = signature.find('(')
            end = signature.rfind(')')
            
            if start == -1 or end == -1:
                return []
            
            param_str = signature[start + 1:end].strip()
            
            if not param_str:
                return []
            
            # Split parameters, handling nested brackets
            param_parts = self._split_parameters(param_str)
            
            parameters = []
            for param in param_parts:
                param = param.strip()
                if not param:
                    continue
                
                # Check if parameter has a default value
                has_default = '=' in param
                
                # Extract parameter name (before : or =)
                name_part = param.split(':')[0].split('=')[0].strip()
                
                parameters.append({
                    'name': name_part,
                    'has_default': has_default
                })
            
            return parameters
            
        except Exception:
            return []

    def _split_parameters(self, param_str: str) -> List[str]:
        """
        Split parameter string by commas, respecting nested brackets.
        
        Args:
            param_str: Parameter string to split
            
        Returns:
            List of individual parameter strings
        """
        parameters = []
        current_param = ""
        bracket_depth = 0
        
        for char in param_str:
            if char in '([{':
                bracket_depth += 1
            elif char in ')]}':
                bracket_depth -= 1
            elif char == ',' and bracket_depth == 0:
                parameters.append(current_param.strip())
                current_param = ""
                continue
            
            current_param += char
        
        if current_param.strip():
            parameters.append(current_param.strip())
        
        return parameters

    def _extract_base_classes(self, signature: str) -> List[str]:
        """
        Extract base class names from a class signature.
        
        Args:
            signature: Class signature string
            
        Returns:
            List of base class names
        """
        try:
            # Example: "class MyClass(BaseClass, Mixin)" -> ["BaseClass", "Mixin"]
            start = signature.find('(')
            end = signature.rfind(')')
            
            if start == -1 or end == -1:
                return []
            
            bases_str = signature[start + 1:end].strip()
            
            if not bases_str:
                return []
            
            # Split by comma and clean up
            bases = [base.strip() for base in bases_str.split(',')]
            return [base for base in bases if base]
            
        except Exception:
            return []

    def _analyze_dependency_changes(self, package_name: str, old_version: str, new_version: str) -> List[str]:
        """
        Analyze dependency changes between package versions.
        
        Args:
            package_name: Name of the package
            old_version: Older version
            new_version: Newer version
            
        Returns:
            List of strings describing dependency changes
        """
        dependency_changes = []
        
        try:
            # Get package info for both versions
            old_info = self.package_manager.get_package_info(package_name, old_version)
            new_info = self.package_manager.get_package_info(package_name, new_version)
            
            # Create dependency lookup dictionaries
            old_deps = {dep.name: dep for dep in old_info.dependencies}
            new_deps = {dep.name: dep for dep in new_info.dependencies}
            
            # Check for removed dependencies
            for dep_name in old_deps:
                if dep_name not in new_deps:
                    dependency_changes.append(f"Removed dependency: {dep_name}")
            
            # Check for added dependencies
            for dep_name in new_deps:
                if dep_name not in old_deps:
                    new_dep = new_deps[dep_name]
                    dependency_changes.append(
                        f"Added dependency: {dep_name} {new_dep.version_spec}"
                    )
            
            # Check for version constraint changes
            for dep_name in old_deps:
                if dep_name in new_deps:
                    old_dep = old_deps[dep_name]
                    new_dep = new_deps[dep_name]
                    
                    if old_dep.version_spec != new_dep.version_spec:
                        dependency_changes.append(
                            f"Changed dependency version: {dep_name} "
                            f"{old_dep.version_spec} -> {new_dep.version_spec}"
                        )
            
        except Exception as e:
            logger.warning(f"Failed to analyze dependency changes: {e}")
            dependency_changes.append("Could not analyze dependency changes")
        
        return dependency_changes

    def _create_element_lookup(self, api_surface: APISurface) -> Set[str]:
        """
        Create a set of element keys for quick lookup.
        
        Args:
            api_surface: API surface to create lookup for
            
        Returns:
            Set of element keys
        """
        elements = set()
        
        for element in api_surface.classes + api_surface.functions + api_surface.constants:
            elements.add(self._get_element_key(element))
        
        return elements

    def _create_element_dict(self, api_surface: APISurface) -> Dict[str, APIElement]:
        """
        Create a dictionary mapping element keys to elements.
        
        Args:
            api_surface: API surface to create dictionary for
            
        Returns:
            Dictionary mapping element keys to APIElement objects
        """
        elements = {}
        
        for element in api_surface.classes + api_surface.functions + api_surface.constants:
            key = self._get_element_key(element)
            elements[key] = element
        
        return elements

    def _get_element_key(self, element: APIElement) -> str:
        """
        Generate a unique key for an API element.
        
        Args:
            element: API element to generate key for
            
        Returns:
            Unique string key for the element
        """
        if element.parent_class:
            return f"{element.parent_class}.{element.name}:{element.type}"
        else:
            return f"{element.name}:{element.type}"

    def _is_breaking_signature_change(self, old_element: APIElement, new_element: APIElement) -> bool:
        """
        Determine if a signature change is breaking.
        
        This is a simplified heuristic that considers changes breaking if:
        - The number of required parameters appears to have increased
        - Parameter names have changed (indicating potential positional argument issues)
        - Return type annotations have changed in incompatible ways
        
        Args:
            old_element: Original API element
            new_element: Updated API element
            
        Returns:
            True if the change is likely breaking, False otherwise
        """
        # If signatures are identical, no breaking change
        if old_element.signature == new_element.signature:
            return False
        
        # Simple heuristics for breaking changes
        old_sig = old_element.signature
        new_sig = new_element.signature
        
        # Check if required parameters were added (simplified check)
        # This is a basic heuristic - a more sophisticated implementation
        # would parse the actual signatures
        
        # Count commas as a proxy for parameter count (very rough)
        old_param_count = old_sig.count(',')
        new_param_count = new_sig.count(',')
        
        # If new version has more commas and no default values added,
        # it might be a breaking change
        if new_param_count > old_param_count:
            # Check if new parameters have defaults (indicated by '=' in signature)
            # This is a very simplified check
            if '=' not in new_sig[len(old_sig):]:
                return True
        
        # Check for removed parameters (also simplified)
        if new_param_count < old_param_count:
            return True
        
        # For now, consider other signature changes as potentially breaking
        # A more sophisticated implementation would parse AST or use inspect
        return True