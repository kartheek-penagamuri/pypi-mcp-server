"""Tests for API surface extraction functionality."""

import ast
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_server.api_surface_extractor import APISurfaceExtractor, ASTAPIVisitor
from mcp_server.errors import APIExtractionError
from mcp_server.migration_models import APIElement, APISurface


class TestASTAPIVisitor:
    """Test the AST visitor for extracting API elements."""
    
    def test_extract_simple_function(self):
        """Test extracting a simple function."""
        source = '''
def hello_world():
    """Say hello to the world."""
    return "Hello, World!"
'''
        tree = ast.parse(source)
        visitor = ASTAPIVisitor()
        visitor.visit(tree)
        
        assert len(visitor.functions) == 1
        func = visitor.functions[0]
        assert func.name == "hello_world"
        assert func.type == "function"
        assert func.docstring == "Say hello to the world."
        assert "def hello_world()" in func.signature
    
    def test_extract_function_with_args(self):
        """Test extracting a function with arguments."""
        source = '''
def greet(name: str, age: int = 25) -> str:
    """Greet a person."""
    return f"Hello {name}, you are {age} years old"
'''
        tree = ast.parse(source)
        visitor = ASTAPIVisitor()
        visitor.visit(tree)
        
        assert len(visitor.functions) == 1
        func = visitor.functions[0]
        assert func.name == "greet"
        assert "name: str" in func.signature
        assert "age: int=..." in func.signature
    
    def test_extract_class(self):
        """Test extracting a class definition."""
        source = '''
class Calculator:
    """A simple calculator class."""
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
    
    def _private_method(self):
        """This should not be extracted."""
        pass
'''
        tree = ast.parse(source)
        visitor = ASTAPIVisitor()
        visitor.visit(tree)
        
        assert len(visitor.classes) == 1
        cls = visitor.classes[0]
        assert cls.name == "Calculator"
        assert cls.type == "class"
        assert cls.docstring == "A simple calculator class."
        
        # Should extract public method
        methods = [f for f in visitor.functions if f.parent_class == "Calculator"]
        assert len(methods) == 1
        assert methods[0].name == "add"
        assert methods[0].type == "method"
    
    def test_extract_constants(self):
        """Test extracting module-level constants."""
        source = '''
VERSION = "1.0.0"
DEBUG = True
_PRIVATE_CONST = "hidden"
'''
        tree = ast.parse(source)
        visitor = ASTAPIVisitor()
        visitor.visit(tree)
        
        assert len(visitor.constants) == 2
        const_names = [c.name for c in visitor.constants]
        assert "VERSION" in const_names
        assert "DEBUG" in const_names
        assert "_PRIVATE_CONST" not in const_names
    
    def test_detect_deprecation_decorator(self):
        """Test detecting deprecation from decorators."""
        source = '''
@deprecated
def old_function():
    """An old function."""
    pass
'''
        tree = ast.parse(source)
        visitor = ASTAPIVisitor()
        visitor.visit(tree)
        
        assert len(visitor.functions) == 1
        func = visitor.functions[0]
        assert func.is_deprecated
        assert "deprecated" in func.deprecation_message.lower()
    
    def test_detect_deprecation_docstring(self):
        """Test detecting deprecation from docstring."""
        source = '''
def old_function():
    """
    This function is deprecated and will be removed in version 2.0.
    Use new_function() instead.
    """
    pass
'''
        tree = ast.parse(source)
        visitor = ASTAPIVisitor()
        visitor.visit(tree)
        
        assert len(visitor.functions) == 1
        func = visitor.functions[0]
        assert func.is_deprecated
        assert "deprecated" in func.deprecation_message.lower()


class TestAPISurfaceExtractor:
    """Test the main API surface extractor."""
    
    @pytest.fixture
    def extractor(self):
        """Create an API surface extractor instance."""
        return APISurfaceExtractor()
    
    def test_analyze_ast_simple(self, extractor):
        """Test analyzing simple Python source code."""
        source = '''
"""A test module."""

VERSION = "1.0.0"

def hello():
    """Say hello."""
    return "Hello"

class Greeter:
    """A greeter class."""
    
    def greet(self, name):
        """Greet someone."""
        return f"Hello {name}"
'''
        
        api_surface = extractor.analyze_ast(source, "test_module", "1.0.0")
        
        assert api_surface.package_name == "test_module"
        assert api_surface.version == "1.0.0"
        assert api_surface.extraction_method == "ast"
        
        # Check extracted elements
        assert len(api_surface.constants) == 1
        assert api_surface.constants[0].name == "VERSION"
        
        assert len(api_surface.functions) >= 1
        func_names = [f.name for f in api_surface.functions]
        assert "hello" in func_names
        
        assert len(api_surface.classes) == 1
        assert api_surface.classes[0].name == "Greeter"
    
    def test_analyze_ast_syntax_error(self, extractor):
        """Test handling syntax errors in source code."""
        source = '''
def broken_function(
    # Missing closing parenthesis
    pass
'''
        
        with pytest.raises(APIExtractionError, match="Syntax error"):
            extractor.analyze_ast(source)
    
    @pytest.mark.asyncio
    async def test_extract_from_package_runtime_success(self, extractor):
        """Test successful runtime extraction from installed package."""
        # Mock a simple module
        mock_module = Mock()
        mock_module.__name__ = "test_package"
        mock_module.test_function = lambda: None
        mock_module.test_function.__doc__ = "A test function"
        
        with patch('importlib.import_module', return_value=mock_module):
            with patch.object(extractor, '_discover_submodules', return_value=[]):
                api_surface = await extractor.extract_from_package("test_package", "1.0.0")
                
                assert api_surface.package_name == "test_package"
                assert api_surface.version == "1.0.0"
                assert api_surface.extraction_method == "runtime"
    
    @pytest.mark.asyncio
    async def test_extract_from_package_fallback_to_ast(self, extractor):
        """Test fallback to AST analysis when package not installed."""
        # Mock import failure, then successful AST analysis
        with patch('importlib.import_module', side_effect=ImportError("Module not found")):
            with patch.object(extractor, '_extract_from_source') as mock_extract:
                mock_api_surface = APISurface(
                    package_name="test_package",
                    version="1.0.0",
                    extraction_method="ast"
                )
                mock_extract.return_value = mock_api_surface
                
                api_surface = await extractor.extract_from_package("test_package", "1.0.0")
                
                assert api_surface.extraction_method == "ast"
                mock_extract.assert_called_once_with("test_package", "1.0.0")
    
    @pytest.mark.asyncio
    async def test_download_package_source_success(self, extractor):
        """Test successful package source download."""
        mock_response_data = {
            "urls": [
                {
                    "packagetype": "sdist",
                    "url": "https://files.pythonhosted.org/packages/test.tar.gz"
                }
            ]
        }
        
        # Mock the archive content
        import io
        import tarfile
        
        # Create a minimal tar.gz content
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
            # Add a simple file
            info = tarfile.TarInfo(name='test_package/__init__.py')
            info.size = 0
            tar.addfile(info, io.BytesIO(b''))
        
        tar_content = tar_buffer.getvalue()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = [
                Mock(json=lambda: mock_response_data, raise_for_status=lambda: None),
                Mock(content=tar_content, raise_for_status=lambda: None)
            ]
            
            temp_dir = await extractor._download_package_source("test_package", "1.0.0")
            
            assert os.path.exists(temp_dir)
            # Cleanup
            extractor.cleanup_temp_directories()
    
    def test_find_package_directory(self, extractor):
        """Test finding package directory in extracted source."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a package structure
            package_dir = Path(temp_dir) / "test_package-1.0.0" / "test_package"
            package_dir.mkdir(parents=True)
            (package_dir / "__init__.py").touch()
            
            found_dir = extractor._find_package_directory(temp_dir, "test_package")
            assert found_dir == str(package_dir)
    
    def test_find_python_files(self, extractor):
        """Test finding Python files in package directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir)
            
            # Create some Python files
            (package_dir / "__init__.py").touch()
            (package_dir / "module1.py").touch()
            (package_dir / "_private.py").touch()  # Should be excluded
            
            # Create subdirectory
            subdir = package_dir / "subpackage"
            subdir.mkdir()
            (subdir / "module2.py").touch()
            
            python_files = extractor._find_python_files(str(package_dir))
            
            # Should find public Python files
            file_names = [Path(f).name for f in python_files]
            assert "module1.py" in file_names
            assert "module2.py" in file_names
            assert "_private.py" not in file_names
    
    def test_cleanup_temp_directories(self, extractor):
        """Test cleanup of temporary directories."""
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        extractor._temp_dirs.append(temp_dir)
        
        assert os.path.exists(temp_dir)
        
        extractor.cleanup_temp_directories()
        
        assert not os.path.exists(temp_dir)
        assert len(extractor._temp_dirs) == 0


# Import os for file operations
import os


class TestAPISurfaceExtractionMockPackages:
    """Test API surface extraction with comprehensive mock packages."""

    @pytest.fixture
    def extractor(self):
        """Create an API surface extractor instance."""
        return APISurfaceExtractor()

    def test_extract_complex_class_hierarchy(self, extractor):
        """Test extracting complex class hierarchies with inheritance."""
        source = '''
"""Complex package with inheritance hierarchy."""

class BaseClass:
    """Base class for all components."""
    
    def __init__(self, name: str):
        self.name = name
    
    def get_name(self) -> str:
        """Get the component name."""
        return self.name
    
    @property
    def display_name(self) -> str:
        """Display name property."""
        return f"Component: {self.name}"

class AdvancedComponent(BaseClass):
    """Advanced component with additional features."""
    
    def __init__(self, name: str, version: str = "1.0"):
        super().__init__(name)
        self.version = version
    
    def get_info(self) -> dict:
        """Get component information."""
        return {"name": self.name, "version": self.version}
    
    @classmethod
    def create_default(cls) -> 'AdvancedComponent':
        """Create a default component."""
        return cls("default")
    
    @staticmethod
    def validate_name(name: str) -> bool:
        """Validate component name."""
        return len(name) > 0

class SpecializedComponent(AdvancedComponent):
    """Specialized component for specific use cases."""
    
    def __init__(self, name: str, version: str = "2.0", features: list = None):
        super().__init__(name, version)
        self.features = features or []
    
    def add_feature(self, feature: str) -> None:
        """Add a feature to the component."""
        self.features.append(feature)
'''
        
        api_surface = extractor.analyze_ast(source, "complex_package", "1.0.0")
        
        # Should extract all classes
        assert len(api_surface.classes) == 3
        class_names = {cls.name for cls in api_surface.classes}
        assert class_names == {"BaseClass", "AdvancedComponent", "SpecializedComponent"}
        
        # Should extract all methods (including inherited ones visible in each class)
        methods = [f for f in api_surface.functions if f.type == "method"]
        method_signatures = {f.signature for f in methods}
        
        # Check for key methods
        assert any("get_name" in sig for sig in method_signatures)
        assert any("get_info" in sig for sig in method_signatures)
        assert any("add_feature" in sig for sig in method_signatures)
        
        # Check for class methods and static methods
        assert any("create_default" in sig for sig in method_signatures)
        assert any("validate_name" in sig for sig in method_signatures)

    def test_extract_decorators_and_annotations(self, extractor):
        """Test extraction of functions with decorators and type annotations."""
        source = '''
"""Package with decorators and type annotations."""

from typing import List, Dict, Optional, Union
from functools import wraps
import asyncio

def deprecated(func):
    """Deprecation decorator."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

class APIClient:
    """API client with various decorated methods."""
    
    @property
    def base_url(self) -> str:
        """Base URL for API calls."""
        return "https://api.example.com"
    
    @staticmethod
    def validate_token(token: str) -> bool:
        """Validate API token."""
        return len(token) > 10
    
    @classmethod
    def from_config(cls, config: Dict[str, str]) -> 'APIClient':
        """Create client from configuration."""
        return cls()
    
    async def fetch_data(self, endpoint: str, params: Optional[Dict[str, str]] = None) -> Dict[str, any]:
        """Fetch data from API endpoint."""
        await asyncio.sleep(0.1)
        return {"data": "example"}
    
    @deprecated
    def old_method(self, data: List[str]) -> Union[str, None]:
        """Old method that should be deprecated."""
        return data[0] if data else None

@deprecated
def legacy_function(items: List[Dict[str, int]]) -> Optional[int]:
    """
    Legacy function that is deprecated.
    
    This function is deprecated and will be removed in version 2.0.
    Use new_function() instead.
    """
    return sum(item.get('value', 0) for item in items)

async def async_process(data: List[str]) -> List[Dict[str, str]]:
    """Asynchronously process data."""
    await asyncio.sleep(0.1)
    return [{"processed": item} for item in data]
'''
        
        api_surface = extractor.analyze_ast(source, "decorated_package", "1.0.0")
        
        # Should detect deprecation from decorator
        deprecated_functions = [f for f in api_surface.functions if f.is_deprecated]
        assert len(deprecated_functions) >= 2
        
        deprecated_names = {f.name for f in deprecated_functions}
        assert "legacy_function" in deprecated_names
        assert "old_method" in deprecated_names
        
        # Should extract async functions
        async_functions = [f for f in api_surface.functions if "async def" in f.signature]
        assert len(async_functions) >= 2
        
        async_names = {f.name for f in async_functions}
        assert "fetch_data" in async_names
        assert "async_process" in async_names
        
        # Should extract properties, class methods, static methods
        properties = [f for f in api_surface.functions if f.type == "property"]
        assert len(properties) >= 1
        assert any(p.name == "base_url" for p in properties)

    def test_extract_module_level_elements(self, extractor):
        """Test extraction of module-level constants, variables, and imports."""
        source = '''
"""Package with module-level elements."""

import os
import sys
from typing import Dict, List
from collections import defaultdict

# Module-level constants
VERSION = "1.2.3"
DEBUG = False
MAX_CONNECTIONS = 100
DEFAULT_CONFIG = {
    "timeout": 30,
    "retries": 3
}

# Module-level variables (should not be extracted as they're not constants)
_private_var = "hidden"
current_state = "initialized"

# Type aliases
ConfigDict = Dict[str, any]
ItemList = List[Dict[str, str]]

def get_version() -> str:
    """Get the package version."""
    return VERSION

def configure(config: ConfigDict) -> None:
    """Configure the package."""
    global current_state
    current_state = "configured"

class ConfigManager:
    """Manages package configuration."""
    
    DEFAULT_TIMEOUT = 30  # Class-level constant
    
    def __init__(self, config: ConfigDict):
        self.config = config
    
    def get_timeout(self) -> int:
        """Get configured timeout."""
        return self.config.get("timeout", self.DEFAULT_TIMEOUT)
'''
        
        api_surface = extractor.analyze_ast(source, "module_package", "1.0.0")
        
        # Should extract module-level constants
        constants = api_surface.constants
        constant_names = {c.name for c in constants}
        
        # Should include public constants
        assert "VERSION" in constant_names
        assert "DEBUG" in constant_names
        assert "MAX_CONNECTIONS" in constant_names
        assert "DEFAULT_CONFIG" in constant_names
        
        # Should not include private variables
        assert "_private_var" not in constant_names
        assert "current_state" not in constant_names
        
        # Should extract functions
        functions = [f for f in api_surface.functions if f.type == "function"]
        function_names = {f.name for f in functions}
        assert "get_version" in function_names
        assert "configure" in function_names

    def test_extract_error_handling_patterns(self, extractor):
        """Test extraction of error handling and exception classes."""
        source = '''
"""Package with custom exceptions and error handling."""

class PackageError(Exception):
    """Base exception for package errors."""
    
    def __init__(self, message: str, error_code: int = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code

class ValidationError(PackageError):
    """Raised when validation fails."""
    
    def __init__(self, field: str, value: any, message: str = None):
        self.field = field
        self.value = value
        super().__init__(message or f"Invalid value for {field}: {value}")

class NetworkError(PackageError):
    """Raised when network operations fail."""
    pass

def validate_input(data: dict) -> None:
    """
    Validate input data.
    
    Raises:
        ValidationError: If data is invalid
        PackageError: If validation system fails
    """
    if not isinstance(data, dict):
        raise ValidationError("data", data, "Must be a dictionary")
    
    if "required_field" not in data:
        raise ValidationError("required_field", None, "Required field missing")

def safe_operation(callback: callable) -> any:
    """
    Safely execute an operation with error handling.
    
    Args:
        callback: Function to execute
        
    Returns:
        Result of callback or None if error occurred
        
    Raises:
        PackageError: If callback raises PackageError
    """
    try:
        return callback()
    except PackageError:
        raise  # Re-raise package errors
    except Exception as e:
        raise PackageError(f"Unexpected error: {e}") from e
'''
        
        api_surface = extractor.analyze_ast(source, "error_package", "1.0.0")
        
        # Should extract exception classes
        exception_classes = [c for c in api_surface.classes if "Error" in c.name or "Exception" in c.name]
        assert len(exception_classes) >= 3
        
        exception_names = {c.name for c in exception_classes}
        assert "PackageError" in exception_names
        assert "ValidationError" in exception_names
        assert "NetworkError" in exception_names
        
        # Should extract functions with proper docstrings including raises info
        functions = [f for f in api_surface.functions if f.type == "function"]
        validate_func = next((f for f in functions if f.name == "validate_input"), None)
        assert validate_func is not None
        assert "ValidationError" in validate_func.docstring
        assert "PackageError" in validate_func.docstring

    @pytest.mark.asyncio
    async def test_mock_package_runtime_extraction(self, extractor):
        """Test runtime extraction from mock package objects."""
        # Create a comprehensive mock package
        mock_package = Mock()
        mock_package.__name__ = "mock_runtime_package"
        mock_package.__version__ = "2.0.0"
        mock_package.__doc__ = "A comprehensive mock package for testing"
        
        # Add functions
        def sample_function(x: int, y: str = "default") -> str:
            """A sample function with parameters."""
            return f"{x}: {y}"
        
        async def async_function(data: list) -> dict:
            """An async function."""
            return {"processed": len(data)}
        
        mock_package.sample_function = sample_function
        mock_package.async_function = async_function
        
        # Add classes
        class SampleClass:
            """A sample class for testing."""
            
            CLASS_CONSTANT = "constant_value"
            
            def __init__(self, name: str):
                self.name = name
            
            def get_name(self) -> str:
                """Get the instance name."""
                return self.name
            
            @classmethod
            def create_default(cls):
                """Create a default instance."""
                return cls("default")
            
            @property
            def display_name(self) -> str:
                """Get display name."""
                return f"Sample: {self.name}"
        
        mock_package.SampleClass = SampleClass
        
        # Add constants
        mock_package.VERSION = "2.0.0"
        mock_package.DEBUG_MODE = False
        mock_package.CONFIG = {"key": "value"}
        
        # Mock the import and inspection
        with patch('importlib.import_module', return_value=mock_package):
            with patch.object(extractor, '_discover_submodules', return_value=[]):
                api_surface = await extractor.extract_from_package("mock_runtime_package", "2.0.0")
        
        assert api_surface.package_name == "mock_runtime_package"
        assert api_surface.version == "2.0.0"
        assert api_surface.extraction_method == "runtime"
        
        # Should extract functions
        function_names = {f.name for f in api_surface.functions if f.type == "function"}
        assert "sample_function" in function_names
        assert "async_function" in function_names
        
        # Should extract classes
        class_names = {c.name for c in api_surface.classes}
        assert "SampleClass" in class_names
        
        # Should extract constants
        constant_names = {c.name for c in api_surface.constants}
        assert "VERSION" in constant_names
        assert "DEBUG_MODE" in constant_names
        assert "CONFIG" in constant_names

    def test_ast_parsing_edge_cases(self, extractor):
        """Test AST parsing with edge cases and complex syntax."""
        source = '''
"""Package with edge cases and complex syntax."""

from __future__ import annotations
from typing import TypeVar, Generic, Protocol, runtime_checkable

T = TypeVar('T')
U = TypeVar('U', bound=str)

@runtime_checkable
class Processable(Protocol):
    """Protocol for processable objects."""
    
    def process(self) -> str:
        """Process the object."""
        ...

class GenericContainer(Generic[T]):
    """Generic container class."""
    
    def __init__(self, item: T):
        self.item = item
    
    def get_item(self) -> T:
        """Get the contained item."""
        return self.item
    
    def transform(self, func: callable[[T], U]) -> GenericContainer[U]:
        """Transform the contained item."""
        return GenericContainer(func(self.item))

# Complex function with multiple decorators
@staticmethod
@property  # This is invalid but should be handled gracefully
def complex_decorated_function():
    """Function with invalid decorator combination."""
    pass

# Function with complex type hints
def process_mapping(
    data: dict[str, list[tuple[int, str]]],
    processor: callable[[tuple[int, str]], dict[str, any]] = None
) -> dict[str, list[dict[str, any]]]:
    """Process complex nested data structures."""
    return {}

# Class with metaclass
class MetaClass(type):
    """Metaclass for special classes."""
    pass

class SpecialClass(metaclass=MetaClass):
    """Class with custom metaclass."""
    
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

# Nested classes
class OuterClass:
    """Outer class containing nested classes."""
    
    class InnerClass:
        """Inner class."""
        
        def inner_method(self) -> str:
            """Method in inner class."""
            return "inner"
    
    class AnotherInner:
        """Another inner class."""
        pass

# Function with yield (generator)
def data_generator(items: list[str]) -> Generator[str, None, None]:
    """Generate processed items."""
    for item in items:
        yield f"processed: {item}"

# Async generator
async def async_data_generator(items: list[str]) -> AsyncGenerator[str, None]:
    """Asynchronously generate processed items."""
    for item in items:
        yield f"async processed: {item}"
'''
        
        # Should handle complex syntax without crashing
        api_surface = extractor.analyze_ast(source, "edge_case_package", "1.0.0")
        
        # Should extract classes despite complex inheritance
        class_names = {c.name for c in api_surface.classes}
        assert "GenericContainer" in class_names
        assert "SpecialClass" in class_names
        assert "OuterClass" in class_names
        
        # Should extract functions with complex signatures
        function_names = {f.name for f in api_surface.functions if f.type == "function"}
        assert "process_mapping" in function_names
        assert "data_generator" in function_names
        assert "async_data_generator" in function_names
        
        # Should handle protocols and type variables gracefully
        # (They might be extracted as classes or ignored, both are acceptable)

    def test_large_package_simulation(self, extractor):
        """Test extraction performance with a large simulated package."""
        # Generate a large package source
        classes = []
        functions = []
        constants = []
        
        # Generate many classes
        for i in range(50):
            class_def = f'''
class LargeClass{i}:
    """Class number {i} in large package."""
    
    CLASS_CONSTANT_{i} = {i}
    
    def __init__(self, value: int = {i}):
        self.value = value
    
    def method_{i}(self, param: str) -> str:
        """Method {i} for class {i}."""
        return f"{{param}}_{i}"
    
    @property
    def property_{i}(self) -> int:
        """Property {i}."""
        return self.value + {i}
'''
            classes.append(class_def)
        
        # Generate many functions
        for i in range(100):
            func_def = f'''
def function_{i}(arg1: int, arg2: str = "default_{i}") -> dict:
    """Function number {i}."""
    return {{"result": arg1 + {i}, "message": arg2}}
'''
            functions.append(func_def)
        
        # Generate many constants
        for i in range(30):
            constants.append(f'CONSTANT_{i} = "value_{i}"')
        
        # Combine into large source
        large_source = f'''
"""Large package for performance testing."""

{chr(10).join(constants)}

{chr(10).join(functions)}

{chr(10).join(classes)}
'''
        
        import time
        start_time = time.time()
        
        api_surface = extractor.analyze_ast(large_source, "large_package", "1.0.0")
        
        extraction_time = time.time() - start_time
        
        # Should complete within reasonable time (< 5 seconds)
        assert extraction_time < 5.0, f"Large package extraction took {extraction_time}s"
        
        # Should extract all elements
        assert len(api_surface.classes) == 50
        assert len(api_surface.constants) >= 30  # Module constants + class constants
        
        # Should extract functions and methods
        functions_and_methods = api_surface.functions
        assert len(functions_and_methods) >= 100  # Functions + methods + properties


# Import os for file operations
import os