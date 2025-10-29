"""
API Surface Extractor for Python packages.

This module provides functionality to extract public API surfaces from Python
packages using both runtime introspection and AST-based source code analysis.
It identifies classes, functions, methods, and their signatures, docstrings, 
and deprecation status.
"""

from __future__ import annotations

import ast
import asyncio
import importlib
import importlib.util
import inspect
import io
import os
import shutil
import tarfile
import tempfile
import warnings
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urlparse

import httpx

from .migration_models import APIElement, APISurface
from .errors import APIExtractionError, PackageAnalysisError


class ASTAPIVisitor(ast.NodeVisitor):
    """
    AST visitor that extracts public API elements from Python source code.
    """
    
    def __init__(self):
        self.classes: List[APIElement] = []
        self.functions: List[APIElement] = []
        self.constants: List[APIElement] = []
        self._current_class: Optional[str] = None
        self._deprecation_keywords = {
            "deprecated", "deprecate", "obsolete", "legacy", "removed", "will be removed"
        }
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition nodes."""
        if not node.name.startswith('_'):  # Only public classes
            # Extract class signature
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(self._get_attribute_name(base))
            
            base_str = f"({', '.join(bases)})" if bases else ""
            signature = f"class {node.name}{base_str}"
            
            # Extract docstring
            docstring = self._extract_docstring(node)
            
            # Check for deprecation
            is_deprecated, deprecation_msg = self._check_ast_deprecation(node, docstring)
            
            class_element = APIElement(
                name=node.name,
                type="class",
                signature=signature,
                docstring=docstring,
                is_deprecated=is_deprecated,
                deprecation_message=deprecation_msg,
                source_location=f"line {node.lineno}"
            )
            
            self.classes.append(class_element)
            
            # Visit class methods
            old_class = self._current_class
            self._current_class = node.name
            self.generic_visit(node)
            self._current_class = old_class
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition nodes."""
        if not node.name.startswith('_'):  # Only public functions/methods
            # Extract function signature
            args = self._extract_function_args(node)
            signature = f"def {node.name}({args})"
            
            # Extract docstring
            docstring = self._extract_docstring(node)
            
            # Check for deprecation
            is_deprecated, deprecation_msg = self._check_ast_deprecation(node, docstring)
            
            # Determine if this is a method or standalone function
            element_type = "method" if self._current_class else "function"
            
            func_element = APIElement(
                name=node.name,
                type=element_type,
                signature=signature,
                docstring=docstring,
                is_deprecated=is_deprecated,
                deprecation_message=deprecation_msg,
                source_location=f"line {node.lineno}",
                parent_class=self._current_class or ""
            )
            
            if self._current_class:
                # This is a method - we'll add it to the functions list but mark the parent
                self.functions.append(func_element)
            else:
                # This is a standalone function
                self.functions.append(func_element)
        
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition nodes."""
        if not node.name.startswith('_'):  # Only public functions/methods
            # Extract function signature
            args = self._extract_function_args(node)
            signature = f"async def {node.name}({args})"
            
            # Extract docstring
            docstring = self._extract_docstring(node)
            
            # Check for deprecation
            is_deprecated, deprecation_msg = self._check_ast_deprecation(node, docstring)
            
            # Determine if this is a method or standalone function
            element_type = "async_method" if self._current_class else "async_function"
            
            func_element = APIElement(
                name=node.name,
                type=element_type,
                signature=signature,
                docstring=docstring,
                is_deprecated=is_deprecated,
                deprecation_message=deprecation_msg,
                source_location=f"line {node.lineno}",
                parent_class=self._current_class or ""
            )
            
            self.functions.append(func_element)
        
        self.generic_visit(node)
    
    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment nodes to find module-level constants."""
        if not self._current_class:  # Only module-level assignments
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith('_'):
                    # This is a potential public constant
                    value_str = self._get_value_string(node.value)
                    signature = f"{target.id} = {value_str}"
                    
                    const_element = APIElement(
                        name=target.id,
                        type="constant",
                        signature=signature,
                        docstring="",
                        is_deprecated=False,
                        deprecation_message="",
                        source_location=f"line {node.lineno}"
                    )
                    
                    self.constants.append(const_element)
        
        self.generic_visit(node)
    
    def _extract_docstring(self, node: Union[ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef]) -> str:
        """Extract docstring from a class or function node."""
        if (node.body and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            return node.body[0].value.value
        return ""
    
    def _extract_function_args(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> str:
        """Extract function arguments as a string."""
        args = []
        
        # Regular arguments
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {self._get_annotation_string(arg.annotation)}"
            args.append(arg_str)
        
        # *args
        if node.args.vararg:
            vararg_str = f"*{node.args.vararg.arg}"
            if node.args.vararg.annotation:
                vararg_str += f": {self._get_annotation_string(node.args.vararg.annotation)}"
            args.append(vararg_str)
        
        # **kwargs
        if node.args.kwarg:
            kwarg_str = f"**{node.args.kwarg.arg}"
            if node.args.kwarg.annotation:
                kwarg_str += f": {self._get_annotation_string(node.args.kwarg.annotation)}"
            args.append(kwarg_str)
        
        # Default values (simplified - just show that defaults exist)
        defaults_count = len(node.args.defaults)
        if defaults_count > 0:
            # Mark the last N args as having defaults
            for i in range(len(args) - defaults_count, len(args)):
                if i >= 0 and not args[i].startswith('*'):
                    args[i] += "=..."
        
        return ", ".join(args)
    
    def _get_annotation_string(self, annotation: ast.expr) -> str:
        """Convert an annotation AST node to a string."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Attribute):
            return self._get_attribute_name(annotation)
        elif isinstance(annotation, ast.Constant):
            return repr(annotation.value)
        else:
            return "..."
    
    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Get the full name of an attribute (e.g., 'typing.List')."""
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self._get_attribute_name(node.value)}.{node.attr}"
        else:
            return node.attr
    
    def _get_value_string(self, node: ast.expr) -> str:
        """Get a string representation of a value node."""
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):
            return "[...]"
        elif isinstance(node, ast.Dict):
            return "{...}"
        else:
            return "..."
    
    def _check_ast_deprecation(self, node: ast.AST, docstring: str) -> tuple[bool, str]:
        """Check for deprecation markers in AST node and docstring."""
        # Check decorators for deprecation
        if hasattr(node, 'decorator_list'):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    if decorator.id.lower() in ['deprecated', 'deprecate']:
                        return True, f"Marked with @{decorator.id} decorator"
                elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                    if decorator.func.id.lower() in ['deprecated', 'deprecate']:
                        return True, f"Marked with @{decorator.func.id}() decorator"
        
        # Check docstring for deprecation markers
        if docstring:
            docstring_lower = docstring.lower()
            for keyword in self._deprecation_keywords:
                if keyword in docstring_lower:
                    # Extract deprecation message from docstring
                    lines = docstring.split('\n')
                    for line in lines:
                        line_lower = line.lower().strip()
                        if keyword in line_lower:
                            return True, line.strip()
        
        return False, ""


class APISurfaceExtractor:
    """
    Extracts public API surface information from Python packages using both
    runtime introspection and AST-based source code analysis.
    """

    def __init__(self):
        self._deprecation_keywords = {
            "deprecated", "deprecate", "obsolete", "legacy", "removed", "will be removed"
        }
        self._temp_dirs: List[str] = []  # Track temporary directories for cleanup

    async def extract_from_package(self, package_name: str, version: str) -> APISurface:
        """
        Extract API surface from a package using runtime introspection or AST analysis.
        
        First attempts runtime introspection for installed packages, then falls back
        to downloading and analyzing source code using AST parsing.
        
        Args:
            package_name: Name of the package to analyze
            version: Version of the package (for metadata)
            
        Returns:
            APISurface containing all public API elements
            
        Raises:
            APIExtractionError: If package cannot be imported or analyzed
        """
        # First try runtime introspection for installed packages
        try:
            module = importlib.import_module(package_name)
            
            # Extract API surface from the main module
            api_surface = self._extract_from_module(module, package_name, version)
            
            # Try to discover and analyze submodules
            submodules = self._discover_submodules(module, package_name)
            api_surface.modules = submodules
            
            # Extract from important submodules (limit to avoid excessive analysis)
            for submodule_name in submodules[:10]:  # Limit to first 10 submodules
                try:
                    submodule = importlib.import_module(submodule_name)
                    sub_api = self._extract_from_module(submodule, submodule_name, version)
                    
                    # Merge submodule API into main surface
                    api_surface.classes.extend(sub_api.classes)
                    api_surface.functions.extend(sub_api.functions)
                    api_surface.constants.extend(sub_api.constants)
                    
                except Exception:
                    # Skip submodules that can't be imported
                    continue
            
            api_surface.extraction_method = "runtime"
            api_surface.extraction_timestamp = datetime.now(timezone.utc).isoformat()
            
            return api_surface
            
        except ImportError:
            # Package not installed locally, try AST-based analysis
            try:
                return await self._extract_from_source(package_name, version)
            except Exception as e:
                raise APIExtractionError(
                    f"Cannot analyze package '{package_name}' version '{version}': "
                    f"Not installed locally and source analysis failed: {e}"
                ) from e
        except Exception as e:
            raise APIExtractionError(f"Failed to extract API surface from '{package_name}': {e}") from e

    def _extract_from_module(self, module: Any, module_name: str, version: str) -> APISurface:
        """
        Extract API elements from a single module using runtime introspection.
        
        Args:
            module: The imported module object
            module_name: Name of the module
            version: Version for metadata
            
        Returns:
            APISurface with extracted elements
        """
        api_surface = APISurface(
            package_name=module_name,
            version=version,
            extraction_method="runtime"
        )
        
        # Get all public attributes from the module
        public_attrs = self._get_public_attributes(module)
        
        for attr_name in public_attrs:
            try:
                attr_value = getattr(module, attr_name)
                
                # Classify and extract the attribute
                if inspect.isclass(attr_value):
                    class_element = self._extract_class(attr_value, attr_name)
                    if class_element:
                        api_surface.classes.append(class_element)
                        
                elif inspect.isfunction(attr_value):
                    func_element = self._extract_function(attr_value, attr_name)
                    if func_element:
                        api_surface.functions.append(func_element)
                        
                elif not inspect.ismodule(attr_value) and not callable(attr_value):
                    # Constants and other non-callable attributes
                    const_element = self._extract_constant(attr_value, attr_name, module)
                    if const_element:
                        api_surface.constants.append(const_element)
                        
            except Exception:
                # Skip attributes that can't be accessed
                continue
        
        return api_surface

    def _get_public_attributes(self, obj: Any) -> List[str]:
        """
        Get public attribute names from an object, filtering out private members.
        
        Args:
            obj: Object to inspect
            
        Returns:
            List of public attribute names
        """
        all_attrs = dir(obj)
        public_attrs = []
        
        for attr in all_attrs:
            # Skip private and special attributes
            if attr.startswith('_'):
                continue
                
            # Skip common non-API attributes
            if attr in {'__builtins__', '__cached__', '__file__', '__loader__', 
                       '__name__', '__package__', '__path__', '__spec__'}:
                continue
                
            public_attrs.append(attr)
        
        return public_attrs

    def _extract_class(self, cls: type, class_name: str) -> Optional[APIElement]:
        """
        Extract API information from a class.
        
        Args:
            cls: Class object to analyze
            class_name: Name of the class
            
        Returns:
            APIElement representing the class, or None if extraction fails
        """
        try:
            # Get class signature
            try:
                signature = str(inspect.signature(cls))
            except (ValueError, TypeError):
                signature = f"class {class_name}"
            
            # Get docstring
            docstring = inspect.getdoc(cls) or ""
            
            # Check for deprecation
            is_deprecated, deprecation_msg = self._check_deprecation(cls, docstring)
            
            # Get source location if available
            source_location = ""
            try:
                source_file = inspect.getfile(cls)
                source_line = inspect.getsourcelines(cls)[1]
                source_location = f"{source_file}:{source_line}"
            except (OSError, TypeError):
                pass
            
            class_element = APIElement(
                name=class_name,
                type="class",
                signature=f"class {class_name}{signature}",
                docstring=docstring,
                is_deprecated=is_deprecated,
                deprecation_message=deprecation_msg,
                source_location=source_location
            )
            
            # Extract public methods from the class
            methods = self._extract_class_methods(cls, class_name)
            
            # For now, we'll store methods as separate elements
            # In a more complete implementation, we might nest them
            
            return class_element
            
        except Exception:
            return None

    def _extract_function(self, func: Any, func_name: str) -> Optional[APIElement]:
        """
        Extract API information from a function.
        
        Args:
            func: Function object to analyze
            func_name: Name of the function
            
        Returns:
            APIElement representing the function, or None if extraction fails
        """
        try:
            # Get function signature
            try:
                signature = str(inspect.signature(func))
            except (ValueError, TypeError):
                signature = f"{func_name}(...)"
            
            # Get docstring
            docstring = inspect.getdoc(func) or ""
            
            # Check for deprecation
            is_deprecated, deprecation_msg = self._check_deprecation(func, docstring)
            
            # Get source location if available
            source_location = ""
            try:
                source_file = inspect.getfile(func)
                source_line = inspect.getsourcelines(func)[1]
                source_location = f"{source_file}:{source_line}"
            except (OSError, TypeError):
                pass
            
            return APIElement(
                name=func_name,
                type="function",
                signature=f"def {func_name}{signature}",
                docstring=docstring,
                is_deprecated=is_deprecated,
                deprecation_message=deprecation_msg,
                source_location=source_location
            )
            
        except Exception:
            return None

    def _extract_constant(self, value: Any, const_name: str, module: Any) -> Optional[APIElement]:
        """
        Extract API information from a constant or variable.
        
        Args:
            value: The constant value
            const_name: Name of the constant
            module: Module containing the constant
            
        Returns:
            APIElement representing the constant, or None if extraction fails
        """
        try:
            # Get type and value representation
            value_type = type(value).__name__
            
            # Create a simple signature showing type and value (truncated if long)
            value_repr = repr(value)
            if len(value_repr) > 100:
                value_repr = value_repr[:97] + "..."
            
            signature = f"{const_name}: {value_type} = {value_repr}"
            
            # Try to get docstring from module annotations or comments
            docstring = ""
            if hasattr(module, '__annotations__') and const_name in module.__annotations__:
                annotation = module.__annotations__[const_name]
                docstring = f"Type: {annotation}"
            
            return APIElement(
                name=const_name,
                type="constant",
                signature=signature,
                docstring=docstring,
                is_deprecated=False,
                deprecation_message="",
                source_location=""
            )
            
        except Exception:
            return None

    def _extract_class_methods(self, cls: type, class_name: str) -> List[APIElement]:
        """
        Extract public methods from a class.
        
        Args:
            cls: Class to analyze
            class_name: Name of the parent class
            
        Returns:
            List of APIElement objects representing methods
        """
        methods = []
        
        # Get all public methods
        for method_name in self._get_public_attributes(cls):
            try:
                method = getattr(cls, method_name)
                
                if inspect.ismethod(method) or inspect.isfunction(method):
                    method_element = self._extract_method(method, method_name, class_name)
                    if method_element:
                        methods.append(method_element)
                        
                elif isinstance(method, property):
                    prop_element = self._extract_property(method, method_name, class_name)
                    if prop_element:
                        methods.append(prop_element)
                        
            except Exception:
                continue
        
        return methods

    def _extract_method(self, method: Any, method_name: str, class_name: str) -> Optional[APIElement]:
        """
        Extract API information from a class method.
        
        Args:
            method: Method object to analyze
            method_name: Name of the method
            class_name: Name of the parent class
            
        Returns:
            APIElement representing the method, or None if extraction fails
        """
        try:
            # Get method signature
            try:
                signature = str(inspect.signature(method))
            except (ValueError, TypeError):
                signature = f"{method_name}(...)"
            
            # Get docstring
            docstring = inspect.getdoc(method) or ""
            
            # Check for deprecation
            is_deprecated, deprecation_msg = self._check_deprecation(method, docstring)
            
            # Determine method type
            method_type = "method"
            if method_name.startswith('__') and method_name.endswith('__'):
                method_type = "special_method"
            elif hasattr(method, '__self__') and method.__self__ is type(method.__self__):
                method_type = "classmethod"
            elif isinstance(inspect.getattr_static(type(method.__self__ if hasattr(method, '__self__') else object), method_name, None), staticmethod):
                method_type = "staticmethod"
            
            return APIElement(
                name=method_name,
                type=method_type,
                signature=f"def {method_name}{signature}",
                docstring=docstring,
                is_deprecated=is_deprecated,
                deprecation_message=deprecation_msg,
                parent_class=class_name,
                source_location=""
            )
            
        except Exception:
            return None

    def _extract_property(self, prop: property, prop_name: str, class_name: str) -> Optional[APIElement]:
        """
        Extract API information from a class property.
        
        Args:
            prop: Property object to analyze
            prop_name: Name of the property
            class_name: Name of the parent class
            
        Returns:
            APIElement representing the property, or None if extraction fails
        """
        try:
            # Get property docstring
            docstring = inspect.getdoc(prop) or ""
            if not docstring and prop.fget:
                docstring = inspect.getdoc(prop.fget) or ""
            
            # Check for deprecation
            is_deprecated, deprecation_msg = self._check_deprecation(prop, docstring)
            if not is_deprecated and prop.fget:
                is_deprecated, deprecation_msg = self._check_deprecation(prop.fget, docstring)
            
            # Create signature showing getter/setter availability
            access_parts = []
            if prop.fget:
                access_parts.append("get")
            if prop.fset:
                access_parts.append("set")
            if prop.fdel:
                access_parts.append("del")
            
            access_str = ", ".join(access_parts) if access_parts else "get"
            signature = f"property {prop_name} ({access_str})"
            
            return APIElement(
                name=prop_name,
                type="property",
                signature=signature,
                docstring=docstring,
                is_deprecated=is_deprecated,
                deprecation_message=deprecation_msg,
                parent_class=class_name,
                source_location=""
            )
            
        except Exception:
            return None

    def _check_deprecation(self, obj: Any, docstring: str) -> tuple[bool, str]:
        """
        Check if an object is deprecated by examining decorators and docstrings.
        
        Args:
            obj: Object to check for deprecation
            docstring: Docstring to search for deprecation markers
            
        Returns:
            Tuple of (is_deprecated, deprecation_message)
        """
        deprecation_message = ""
        
        # Check for deprecation decorators
        if hasattr(obj, '__annotations__') or hasattr(obj, '__wrapped__'):
            # Look for common deprecation decorator patterns
            if hasattr(obj, '__name__'):
                # This is a simplified check - in practice, you'd want to examine
                # the actual decorator objects, but that's complex with runtime introspection
                pass
        
        # Check docstring for deprecation markers
        if docstring:
            docstring_lower = docstring.lower()
            for keyword in self._deprecation_keywords:
                if keyword in docstring_lower:
                    # Extract deprecation message from docstring
                    lines = docstring.split('\n')
                    for line in lines:
                        line_lower = line.lower().strip()
                        if keyword in line_lower:
                            deprecation_message = line.strip()
                            return True, deprecation_message
        
        # Check for warnings.warn calls (this is limited in runtime introspection)
        # In a more complete implementation, you might use AST analysis for this
        
        return False, deprecation_message

    def _discover_submodules(self, module: Any, package_name: str) -> List[str]:
        """
        Discover submodules within a package.
        
        Args:
            module: Main package module
            package_name: Name of the package
            
        Returns:
            List of submodule names
        """
        submodules = []
        
        try:
            # Check if the module has a __path__ (indicating it's a package)
            if hasattr(module, '__path__'):
                import pkgutil
                
                # Use pkgutil to find submodules
                for importer, modname, ispkg in pkgutil.iter_modules(module.__path__, package_name + "."):
                    submodules.append(modname)
                    
                    # Limit the number of submodules to avoid excessive analysis
                    if len(submodules) >= 20:
                        break
            
        except Exception:
            # If submodule discovery fails, continue with just the main module
            pass
        
        return submodules

    async def _extract_from_source(self, package_name: str, version: str) -> APISurface:
        """
        Extract API surface by downloading and analyzing package source code.
        
        Args:
            package_name: Name of the package to analyze
            version: Version of the package to download
            
        Returns:
            APISurface extracted from source code analysis
            
        Raises:
            APIExtractionError: If source download or analysis fails
        """
        temp_dir = None
        try:
            # Download package source
            temp_dir = await self._download_package_source(package_name, version)
            
            # Analyze source code using AST
            api_surface = await self._analyze_source_directory(temp_dir, package_name, version)
            
            api_surface.extraction_method = "ast"
            api_surface.extraction_timestamp = datetime.now(timezone.utc).isoformat()
            
            return api_surface
            
        finally:
            # Clean up temporary directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    # Log but don't fail if cleanup fails
                    pass

    async def _download_package_source(self, package_name: str, version: str) -> str:
        """
        Download package source distribution from PyPI.
        
        Args:
            package_name: Name of the package
            version: Version to download
            
        Returns:
            Path to temporary directory containing extracted source
            
        Raises:
            APIExtractionError: If download fails
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Get package metadata from PyPI
                response = await client.get(f"https://pypi.org/pypi/{package_name}/{version}/json")
                response.raise_for_status()
                
                package_data = response.json()
                
                # Find source distribution URL
                source_url = None
                for url_info in package_data.get("urls", []):
                    if url_info.get("packagetype") == "sdist":
                        source_url = url_info.get("url")
                        break
                
                if not source_url:
                    raise APIExtractionError(f"No source distribution found for {package_name} {version}")
                
                # Download source distribution
                response = await client.get(source_url)
                response.raise_for_status()
                
                # Create temporary directory
                temp_dir = tempfile.mkdtemp(prefix=f"{package_name}_{version}_")
                self._temp_dirs.append(temp_dir)
                
                # Extract archive
                source_content = io.BytesIO(response.content)
                
                if source_url.endswith('.tar.gz') or source_url.endswith('.tgz'):
                    with tarfile.open(fileobj=source_content, mode='r:gz') as tar:
                        # Use data filter for security (Python 3.12+)
                        try:
                            tar.extractall(temp_dir, filter='data')
                        except TypeError:
                            # Fallback for older Python versions
                            tar.extractall(temp_dir)
                elif source_url.endswith('.zip'):
                    with zipfile.ZipFile(source_content) as zip_file:
                        zip_file.extractall(temp_dir)
                else:
                    raise APIExtractionError(f"Unsupported archive format: {source_url}")
                
                return temp_dir
                
            except httpx.HTTPError as e:
                raise APIExtractionError(f"Failed to download {package_name} {version}: {e}") from e
            except Exception as e:
                raise APIExtractionError(f"Error processing source for {package_name} {version}: {e}") from e

    async def _analyze_source_directory(self, source_dir: str, package_name: str, version: str) -> APISurface:
        """
        Analyze Python source files in a directory using AST parsing.
        
        Args:
            source_dir: Directory containing extracted source code
            package_name: Name of the package
            version: Version being analyzed
            
        Returns:
            APISurface extracted from source analysis
        """
        api_surface = APISurface(
            package_name=package_name,
            version=version,
            extraction_method="ast"
        )
        
        # Find the main package directory
        package_dir = self._find_package_directory(source_dir, package_name)
        if not package_dir:
            raise APIExtractionError(f"Cannot find package directory for {package_name} in source")
        
        # Analyze Python files
        python_files = self._find_python_files(package_dir)
        
        for py_file in python_files[:20]:  # Limit to avoid excessive analysis
            try:
                await self._analyze_python_file(py_file, api_surface)
            except Exception:
                # Skip files that can't be parsed
                continue
        
        return api_surface

    def _find_package_directory(self, source_dir: str, package_name: str) -> Optional[str]:
        """
        Find the main package directory within extracted source.
        
        Args:
            source_dir: Root directory of extracted source
            package_name: Name of the package to find
            
        Returns:
            Path to package directory or None if not found
        """
        # Common patterns for package directories
        candidates = [
            os.path.join(source_dir, package_name),
            os.path.join(source_dir, package_name.replace('-', '_')),
            os.path.join(source_dir, package_name.replace('_', '-')),
        ]
        
        # Also check subdirectories (for packages with version in directory name)
        for item in os.listdir(source_dir):
            item_path = os.path.join(source_dir, item)
            if os.path.isdir(item_path):
                # Check if this directory contains the package
                for candidate in [package_name, package_name.replace('-', '_'), package_name.replace('_', '-')]:
                    potential_path = os.path.join(item_path, candidate)
                    if os.path.isdir(potential_path):
                        candidates.append(potential_path)
                
                # Also check src/ subdirectory pattern
                src_path = os.path.join(item_path, 'src', package_name.replace('-', '_'))
                if os.path.isdir(src_path):
                    candidates.append(src_path)
        
        # Return the first valid candidate
        for candidate in candidates:
            if os.path.isdir(candidate) and self._is_python_package(candidate):
                return candidate
        
        return None

    def _is_python_package(self, directory: str) -> bool:
        """
        Check if a directory is a Python package (contains __init__.py or Python files).
        
        Args:
            directory: Directory to check
            
        Returns:
            True if directory appears to be a Python package
        """
        if not os.path.isdir(directory):
            return False
        
        # Check for __init__.py
        if os.path.exists(os.path.join(directory, '__init__.py')):
            return True
        
        # Check for any .py files
        for item in os.listdir(directory):
            if item.endswith('.py'):
                return True
        
        return False

    def _find_python_files(self, package_dir: str) -> List[str]:
        """
        Find all Python files in a package directory.
        
        Args:
            package_dir: Directory to search
            
        Returns:
            List of Python file paths
        """
        python_files = []
        
        for root, dirs, files in os.walk(package_dir):
            # Skip test directories and private modules
            dirs[:] = [d for d in dirs if not d.startswith('_') and d != 'tests' and d != 'test']
            
            for file in files:
                if file.endswith('.py') and not file.startswith('_'):
                    python_files.append(os.path.join(root, file))
        
        return python_files

    async def _analyze_python_file(self, file_path: str, api_surface: APISurface) -> None:
        """
        Analyze a single Python file and add its API elements to the surface.
        
        Args:
            file_path: Path to Python file to analyze
            api_surface: APISurface to add elements to
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Parse the source code
            tree = ast.parse(source_code)
            
            # Visit the AST to extract API elements
            visitor = ASTAPIVisitor()
            visitor.visit(tree)
            
            # Add extracted elements to the API surface
            api_surface.classes.extend(visitor.classes)
            api_surface.functions.extend(visitor.functions)
            api_surface.constants.extend(visitor.constants)
            
        except Exception as e:
            # Skip files that can't be parsed or read
            pass

    def cleanup_temp_directories(self) -> None:
        """
        Clean up any temporary directories created during analysis.
        """
        for temp_dir in self._temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    # Log but don't fail if cleanup fails
                    pass
        self._temp_dirs.clear()

    def analyze_ast(self, source_code: str, package_name: str = "unknown", version: str = "unknown") -> APISurface:
        """
        Analyze Python source code using AST parsing to extract API surface.
        
        Args:
            source_code: Python source code to analyze
            package_name: Name of the package (for metadata)
            version: Version of the package (for metadata)
            
        Returns:
            APISurface extracted from the source code
            
        Raises:
            APIExtractionError: If source code cannot be parsed
        """
        try:
            # Parse the source code
            tree = ast.parse(source_code)
            
            # Visit the AST to extract API elements
            visitor = ASTAPIVisitor()
            visitor.visit(tree)
            
            # Create API surface from extracted elements
            api_surface = APISurface(
                package_name=package_name,
                version=version,
                classes=visitor.classes,
                functions=visitor.functions,
                constants=visitor.constants,
                extraction_method="ast",
                extraction_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            return api_surface
            
        except SyntaxError as e:
            raise APIExtractionError(f"Syntax error in source code: {e}") from e
        except Exception as e:
            raise APIExtractionError(f"Failed to analyze source code: {e}") from e

    def __del__(self):
        """Cleanup temporary directories when object is destroyed."""
        self.cleanup_temp_directories()