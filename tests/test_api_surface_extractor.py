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