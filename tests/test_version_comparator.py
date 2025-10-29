"""Tests for version comparison functionality."""

from unittest.mock import Mock, patch

import pytest

from mcp_server.migration_models import APIChange, APIElement, APISurface, VersionComparison
from mcp_server.package_manager import PackageManager
from mcp_server.version_comparator import VersionComparator
from mcp_server.errors import VersionComparisonError


class TestVersionComparator:
    """Test the VersionComparator class."""

    @pytest.fixture
    def mock_package_manager(self):
        """Create a mock package manager."""
        return Mock(spec=PackageManager)

    @pytest.fixture
    def version_comparator(self, mock_package_manager):
        """Create a version comparator with mocked dependencies."""
        return VersionComparator(mock_package_manager)

    @pytest.fixture
    def sample_old_surface(self):
        """Create a sample old API surface."""
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
                    name="old_function",
                    type="function",
                    signature="def old_function(x: int) -> str",
                    docstring="An old function."
                ),
                APIElement(
                    name="modified_function",
                    type="function",
                    signature="def modified_function(a: str) -> str",
                    docstring="A function that will be modified."
                ),
                APIElement(
                    name="to_be_deprecated",
                    type="function",
                    signature="def to_be_deprecated() -> None",
                    docstring="A function that will be deprecated.",
                    is_deprecated=False
                )
            ],
            constants=[
                APIElement(
                    name="OLD_CONSTANT",
                    type="constant",
                    signature="OLD_CONSTANT: str = 'old_value'",
                    docstring="An old constant."
                )
            ]
        )

    @pytest.fixture
    def sample_new_surface(self):
        """Create a sample new API surface."""
        return APISurface(
            package_name="test_package",
            version="2.0.0",
            classes=[
                APIElement(
                    name="TestClass",
                    type="class",
                    signature="class TestClass",
                    docstring="A test class."
                ),
                APIElement(
                    name="NewClass",
                    type="class",
                    signature="class NewClass",
                    docstring="A new class."
                )
            ],
            functions=[
                APIElement(
                    name="new_function",
                    type="function",
                    signature="def new_function(y: float) -> int",
                    docstring="A new function."
                ),
                APIElement(
                    name="modified_function",
                    type="function",
                    signature="def modified_function(a: str, b: int = 10) -> str",
                    docstring="A function that was modified."
                ),
                APIElement(
                    name="to_be_deprecated",
                    type="function",
                    signature="def to_be_deprecated() -> None",
                    docstring="A function that is now deprecated.",
                    is_deprecated=True,
                    deprecation_message="Use new_function instead"
                )
            ],
            constants=[
                APIElement(
                    name="NEW_CONSTANT",
                    type="constant",
                    signature="NEW_CONSTANT: int = 42",
                    docstring="A new constant."
                )
            ]
        )

    def test_compare_api_surfaces_basic(self, version_comparator, sample_old_surface, sample_new_surface):
        """Test basic API surface comparison."""
        comparison = version_comparator.compare_api_surfaces(sample_old_surface, sample_new_surface)
        
        assert isinstance(comparison, VersionComparison)
        assert comparison.package_name == "test_package"
        assert comparison.old_version == "1.0.0"
        assert comparison.new_version == "2.0.0"
        
        # Check that we have changes in each category
        assert len(comparison.additions) > 0
        assert len(comparison.modifications) > 0
        assert len(comparison.deprecations) > 0

    def test_compare_different_packages_raises_error(self, version_comparator):
        """Test that comparing different packages raises an error."""
        old_surface = APISurface(package_name="package_a", version="1.0.0")
        new_surface = APISurface(package_name="package_b", version="1.0.0")
        
        with pytest.raises(VersionComparisonError):
            version_comparator.compare_api_surfaces(old_surface, new_surface)

    def test_detect_additions(self, version_comparator, sample_old_surface, sample_new_surface):
        """Test detection of API additions."""
        additions = version_comparator.detect_additions(sample_old_surface, sample_new_surface)
        
        # Should detect new function, new class, and new constant
        addition_names = {change.element_name for change in additions}
        assert "new_function" in addition_names
        assert "NewClass" in addition_names
        assert "NEW_CONSTANT" in addition_names
        
        # Check that all additions have correct change type
        for addition in additions:
            assert addition.change_type == "added"
            assert addition.impact_level == "enhancement"

    def test_detect_removals(self, version_comparator, sample_old_surface, sample_new_surface):
        """Test detection of API removals."""
        old_elements = version_comparator._create_element_map(sample_old_surface)
        new_elements = version_comparator._create_element_map(sample_new_surface)
        
        removals = version_comparator._detect_removals(old_elements, new_elements)
        
        # Should detect removed function and constant
        removal_names = {change.element_name for change in removals}
        assert "old_function" in removal_names
        assert "OLD_CONSTANT" in removal_names
        
        # Check that all removals are marked as breaking
        for removal in removals:
            assert removal.change_type == "removed"
            assert removal.impact_level == "breaking"

    def test_detect_modifications(self, version_comparator, sample_old_surface, sample_new_surface):
        """Test detection of API modifications."""
        old_elements = version_comparator._create_element_map(sample_old_surface)
        new_elements = version_comparator._create_element_map(sample_new_surface)
        
        modifications = version_comparator._detect_modifications(old_elements, new_elements)
        
        # Should detect modified function
        modification_names = {change.element_name for change in modifications}
        assert "modified_function" in modification_names
        
        # Check modification details
        mod_change = next(c for c in modifications if c.element_name == "modified_function")
        assert mod_change.change_type == "modified"
        assert "def modified_function(a: str)" in mod_change.old_signature
        assert "def modified_function(a: str, b: int = 10)" in mod_change.new_signature

    def test_detect_deprecations(self, version_comparator, sample_old_surface, sample_new_surface):
        """Test detection of new deprecations."""
        deprecations = version_comparator.detect_deprecations(sample_old_surface, sample_new_surface)
        
        # Should detect newly deprecated function
        deprecation_names = {change.element_name for change in deprecations}
        assert "to_be_deprecated" in deprecation_names
        
        # Check deprecation details
        dep_change = next(c for c in deprecations if c.element_name == "to_be_deprecated")
        assert dep_change.change_type == "deprecated"
        assert dep_change.impact_level == "compatible"
        assert "Use new_function instead" in dep_change.description

    def test_assess_function_signature_change_breaking(self, version_comparator):
        """Test assessment of breaking function signature changes."""
        old_sig = "def func(a: str, b: int) -> str"
        new_sig = "def func(a: str) -> str"  # Removed parameter
        
        impact = version_comparator._assess_function_signature_change(old_sig, new_sig)
        assert impact == "breaking"

    def test_assess_function_signature_change_compatible(self, version_comparator):
        """Test assessment of compatible function signature changes."""
        old_sig = "def func(a: str) -> str"
        new_sig = "def func(a: str, b: int = 10) -> str"  # Added optional parameter
        
        impact = version_comparator._assess_function_signature_change(old_sig, new_sig)
        assert impact == "enhancement"

    def test_assess_function_signature_change_removed_default(self, version_comparator):
        """Test assessment when default value is removed (breaking)."""
        old_sig = "def func(a: str, b: int = 10) -> str"
        new_sig = "def func(a: str, b: int) -> str"  # Removed default value
        
        impact = version_comparator._assess_function_signature_change(old_sig, new_sig)
        assert impact == "breaking"

    def test_extract_parameters_simple(self, version_comparator):
        """Test parameter extraction from simple function signature."""
        signature = "def func(a: str, b: int = 10) -> str"
        params = version_comparator._extract_parameters(signature)
        
        assert len(params) == 2
        assert params[0]['name'] == 'a'
        assert not params[0]['has_default']
        assert params[1]['name'] == 'b'
        assert params[1]['has_default']

    def test_extract_parameters_complex(self, version_comparator):
        """Test parameter extraction from complex function signature."""
        signature = "def func(a: str, *args, b: int = 10, **kwargs) -> str"
        params = version_comparator._extract_parameters(signature)
        
        param_names = [p['name'] for p in params]
        assert 'a' in param_names
        assert '*args' in param_names
        assert 'b' in param_names
        assert '**kwargs' in param_names

    def test_split_parameters_nested(self, version_comparator):
        """Test parameter splitting with nested structures."""
        param_str = "a: str, b: List[Dict[str, int]], c: int = 10"
        params = version_comparator._split_parameters(param_str)
        
        assert len(params) == 3
        assert params[0] == "a: str"
        assert params[1] == "b: List[Dict[str, int]]"
        assert params[2] == "c: int = 10"

    def test_extract_base_classes(self, version_comparator):
        """Test extraction of base classes from class signature."""
        signature = "class MyClass(BaseClass, Mixin)"
        bases = version_comparator._extract_base_classes(signature)
        
        assert len(bases) == 2
        assert "BaseClass" in bases
        assert "Mixin" in bases

    def test_assess_class_signature_change(self, version_comparator):
        """Test assessment of class signature changes."""
        old_sig = "class MyClass"
        new_sig = "class MyClass(BaseClass)"  # Added base class
        
        impact = version_comparator._assess_class_signature_change(old_sig, new_sig)
        assert impact == "enhancement"

    def test_create_element_map(self, version_comparator, sample_old_surface):
        """Test creation of element map from API surface."""
        element_map = version_comparator._create_element_map(sample_old_surface)
        
        # Check that all elements are mapped correctly
        assert "TestClass" in element_map
        assert "old_function" in element_map
        assert "modified_function" in element_map
        assert "OLD_CONSTANT" in element_map

    def test_create_element_map_with_methods(self, version_comparator):
        """Test element map creation with class methods."""
        surface = APISurface(
            package_name="test",
            version="1.0.0",
            functions=[
                APIElement(
                    name="method_name",
                    type="method",
                    signature="def method_name(self) -> None",
                    parent_class="TestClass"
                )
            ]
        )
        
        element_map = version_comparator._create_element_map(surface)
        assert "TestClass.method_name" in element_map

    def test_identify_breaking_changes(self, version_comparator):
        """Test identification of breaking changes from a list of changes."""
        changes = [
            APIChange(
                element_name="func1",
                change_type="removed",
                impact_level="breaking",
                element_type="function"
            ),
            APIChange(
                element_name="func2",
                change_type="added",
                impact_level="enhancement",
                element_type="function"
            ),
            APIChange(
                element_name="func3",
                change_type="modified",
                impact_level="breaking",
                element_type="function"
            )
        ]
        
        breaking_changes = version_comparator._identify_breaking_changes(changes)
        
        assert len(breaking_changes) == 2
        breaking_names = {change.element_name for change in breaking_changes}
        assert "func1" in breaking_names
        assert "func3" in breaking_names

    @patch('mcp_server.version_comparator.VersionComparator._analyze_dependency_changes')
    def test_analyze_dependency_changes_called(self, mock_analyze_deps, version_comparator, sample_old_surface, sample_new_surface):
        """Test that dependency analysis is called during comparison."""
        mock_analyze_deps.return_value = ["Added dependency: requests >=2.0.0"]
        
        comparison = version_comparator.compare_api_surfaces(sample_old_surface, sample_new_surface)
        
        mock_analyze_deps.assert_called_once_with("test_package", "1.0.0", "2.0.0")
        assert len(comparison.dependency_changes) == 1
        assert "Added dependency: requests" in comparison.dependency_changes[0]


class TestVersionComparatorIntegration:
    """Integration tests for version comparator with real-like scenarios."""

    @pytest.fixture
    def version_comparator(self):
        """Create a version comparator with real package manager."""
        mock_pm = Mock(spec=PackageManager)
        return VersionComparator(mock_pm)

    def test_real_package_scenario(self, version_comparator):
        """Test with a realistic package evolution scenario."""
        # Simulate a package that added async support
        old_surface = APISurface(
            package_name="example_lib",
            version="1.0.0",
            functions=[
                APIElement(
                    name="fetch_data",
                    type="function",
                    signature="def fetch_data(url: str) -> dict",
                    docstring="Fetch data synchronously."
                ),
                APIElement(
                    name="process_data",
                    type="function",
                    signature="def process_data(data: dict) -> str",
                    docstring="Process the data."
                )
            ]
        )
        
        new_surface = APISurface(
            package_name="example_lib",
            version="2.0.0",
            functions=[
                APIElement(
                    name="fetch_data",
                    type="function",
                    signature="def fetch_data(url: str) -> dict",
                    docstring="Fetch data synchronously. Deprecated: use async_fetch_data.",
                    is_deprecated=True,
                    deprecation_message="Use async_fetch_data instead"
                ),
                APIElement(
                    name="async_fetch_data",
                    type="async_function",
                    signature="async def async_fetch_data(url: str) -> dict",
                    docstring="Fetch data asynchronously."
                ),
                APIElement(
                    name="process_data",
                    type="function",
                    signature="def process_data(data: dict, format: str = 'json') -> str",
                    docstring="Process the data with optional format."
                )
            ]
        )
        
        comparison = version_comparator.compare_api_surfaces(old_surface, new_surface)
        
        # Should detect addition of async function
        addition_names = {change.element_name for change in comparison.additions}
        assert "async_fetch_data" in addition_names
        
        # Should detect deprecation of sync function
        deprecation_names = {change.element_name for change in comparison.deprecations}
        assert "fetch_data" in deprecation_names
        
        # Should detect modification of process_data (added optional parameter)
        modification_names = {change.element_name for change in comparison.modifications}
        assert "process_data" in modification_names
        
        # The modification should be compatible (added optional parameter)
        process_mod = next(c for c in comparison.modifications if c.element_name == "process_data")
        assert process_mod.impact_level == "enhancement"

    def test_breaking_change_scenario(self, version_comparator):
        """Test detection of breaking changes in a major version update."""
        old_surface = APISurface(
            package_name="breaking_lib",
            version="1.5.0",
            classes=[
                APIElement(
                    name="Client",
                    type="class",
                    signature="class Client(BaseClient)",
                    docstring="Main client class."
                )
            ],
            functions=[
                APIElement(
                    name="connect",
                    type="function",
                    signature="def connect(host: str, port: int = 8080, timeout: int = 30) -> Connection",
                    docstring="Connect to server."
                )
            ]
        )
        
        new_surface = APISurface(
            package_name="breaking_lib",
            version="2.0.0",
            classes=[
                APIElement(
                    name="Client",
                    type="class",
                    signature="class Client",  # Removed base class
                    docstring="Main client class."
                )
            ],
            functions=[
                APIElement(
                    name="connect",
                    type="function",
                    signature="def connect(host: str, port: int, timeout: int = 30) -> Connection",
                    docstring="Connect to server."
                )
            ]
        )
        
        comparison = version_comparator.compare_api_surfaces(old_surface, new_surface)
        
        # Should detect breaking changes
        assert len(comparison.breaking_changes) > 0
        
        # Check specific breaking changes
        breaking_names = {change.element_name for change in comparison.breaking_changes}
        
        # Function signature change (removed default value) should be breaking
        if "connect" in breaking_names:
            connect_change = next(c for c in comparison.breaking_changes if c.element_name == "connect")
            assert connect_change.impact_level == "breaking"