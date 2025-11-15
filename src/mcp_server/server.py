# src/mcp_server/server.py
from __future__ import annotations

import argparse
import asyncio
import logging
import os
from typing import Optional, List, Dict, Any, Annotated

from mcp.server.fastmcp import FastMCP

from .project_analyzer import ProjectAnalyzer
from .package_manager import PackageManager
from .migration_analyzer import MigrationAnalyzer
from .utils import to_serializable
from .errors import MigrationAnalysisError

# Configure logging
logger = logging.getLogger(__name__)

# Server instance
mcp = FastMCP("Python Package MCP Server")

# Singletons for simple stateless server behavior
_analyzer = ProjectAnalyzer()
_pkg = PackageManager()
_migration_analyzer = MigrationAnalyzer(package_manager=_pkg)


@mcp.tool(
    description=(
        "Scan a Python project for dependency files and return parsed dependencies. "
        "Understands requirements.txt, pyproject.toml (PEP 621 + optional-dependencies), "
        "Pipfile, and a basic install_requires[] in setup.py. Results auto-refresh when "
        "the files change (mtime-based)."
    )
)
def analyze_project_dependencies(
    project_path: Annotated[Optional[str], "Absolute/relative path to the project root. Defaults to current working directory."] = None,
) -> Dict[str, Any]:
    """
    Analyze a local Python project and extract declared dependencies.

    Args:
      project_path: Path to the project directory (default: CWD).

    Returns:
      ProjectInfo JSON:
      {
        "project_path": str,
        "dependency_files": [str, ...],
        "dependencies": [
          {"name": str, "version_spec": str, "extras": [str], "source_file": str, "is_dev_dependency": bool},
          ...
        ]
      }
    """
    path = project_path or os.getcwd()
    info = _analyzer.analyze_project(path)
    return to_serializable(info)


@mcp.tool(
    description=(
        "Get comprehensive metadata for a Python package including README documentation, dependencies, "
        "author, license, and compatibility information. CRITICAL: You MUST call this tool FIRST before:\n"
        "• Migrating or upgrading any Python package\n"
        "• Implementing features from a specific package version\n"
        "• Answering questions about package capabilities, APIs, or features\n"
        "• Analyzing package dependencies or compatibility\n"
        "• Understanding breaking changes between versions\n"
        "The README often contains crucial API documentation, migration guides, and usage examples that are "
        "essential for correct implementation. Returns short summary plus full README (long_description) when available."
    )
)
def get_package_metadata(
    package_name: Annotated[str, "Package name on PyPI or installed locally (e.g., 'requests')."],
    version_spec: Annotated[Optional[str], "Optional PEP 440 specifier string, e.g., '>=2.0,<3'."] = None,
) -> Dict[str, Any]:
    """
    Retrieve package metadata (local-first, PyPI fallback).

    Returns:
      PackageInfo JSON + "install_hint"
    """
    info = _pkg.get_package_info(package_name, version_spec=version_spec)
    d = to_serializable(info)
    d["install_hint"] = f"pip install {package_name}{version_spec or ''}"
    return d


@mcp.tool(
    description=(
        "Search PyPI for packages by keywords or approximate names. "
        "Best-effort HTML search (no public PyPI JSON search API). "
        "Returns compact results (name, description, version, author). "
        "If zero results and the query looks like an exact name, it tries a direct metadata lookup."
    )
)
def search_packages(
    query: Annotated[str, "Free-text keywords or a package name (e.g., 'http client' or 'pytm')."],
    limit: Annotated[int, "Maximum number of results to return."] = 10,
    python_version: Annotated[Optional[str], "Optional Python version hint like '3.11'. Not strict."] = None,
) -> List[Dict[str, Any]]:
    """
    Search PyPI by functionality/keywords and return lightweight matches.

    Returns:
      [{"name": str, "description": str, "version": str, "author": str}, ...]
    """
    results = _pkg.search_packages(query, limit=limit, python_version=python_version)

    # Fallback: if search yields nothing, try an exact-name info fetch
    if not results and query and query.strip():
        q = query.strip()
        try:
            meta = _pkg.get_package_info(q)
            results = [  # type: ignore[assignment]
                {
                    "name": meta.name,
                    "description": meta.description,
                    "version": meta.version,
                    "author": meta.author,
                }
            ]
        except Exception:
            pass

    return [to_serializable(r) for r in results]


@mcp.tool(
    description=(
        "Check whether adding a new package (and optional version constraint) would "
        "conflict with the project's existing declared constraints. Reports any packages "
        "for which no single release satisfies all constraints."
    )
)
def check_package_compatibility(
    new_package: Annotated[str, "Package you want to add to the project (e.g., 'httpx')."],
    version_spec: Annotated[Optional[str], "Optional PEP 440 specifier for the candidate (e.g., '>=0.27')."] = None,
    project_path: Annotated[Optional[str], "Project root path. Defaults to current working directory."] = None,
) -> Dict[str, Any]:
    """
    Validate a candidate package/version against current project constraints.

    Returns:
      {"conflicts": [{"package": str, "reason": str, "constraints": [str, ...]}, ...]}
    """
    path = project_path or os.getcwd()
    info = _analyzer.analyze_project(path)
    out = _pkg.check_compatibility(info.dependencies, new_package, version_spec)
    return to_serializable(out)


@mcp.tool(
    description=(
        "Return the latest available version of a package on PyPI. "
        "By default prereleases are skipped; set allow_prerelease=True to include them."
    )
)
def get_latest_version(
    package_name: Annotated[str, "Package name on PyPI (e.g., 'pytm')."],
    allow_prerelease: Annotated[bool, "Include prerelease versions if True."] = False,
) -> Dict[str, Any]:
    """
    Get the latest (non-yanked) version string for a package from PyPI.

    Returns:
      {"name": str, "version": str, "is_prerelease": bool, "source": "pypi"}
    """
    latest = _pkg.get_latest_version(package_name, allow_prerelease=allow_prerelease)
    return to_serializable(latest)


@mcp.tool(
    description=(
        "Analyze the public API surface of a specific package version. "
        "Extracts classes, functions, constants, and modules with their signatures "
        "and documentation. Uses runtime inspection when possible, falls back to "
        "AST analysis for unavailable packages. Results are cached for performance."
    )
)
async def analyze_package_api_surface(
    package_name: Annotated[str, "Package name to analyze (e.g., 'requests')."],
    version: Annotated[str, "Specific version to analyze (e.g., '2.28.0')."],
) -> Dict[str, Any]:
    """
    Analyze the public API surface of a package version.

    Args:
      package_name: Name of the package to analyze
      version: Specific version to analyze

    Returns:
      APISurface JSON:
      {
        "package_name": str,
        "version": str,
        "classes": [{"name": str, "type": str, "signature": str, "docstring": str, ...}, ...],
        "functions": [{"name": str, "type": str, "signature": str, "docstring": str, ...}, ...],
        "constants": [{"name": str, "type": str, "signature": str, "docstring": str, ...}, ...],
        "modules": [str, ...],
        "extraction_method": str,
        "extraction_timestamp": str
      }
    """
    try:
        logger.info(f"Analyzing API surface for {package_name} {version}")
        api_surface = await _migration_analyzer.analyze_api_surface(package_name, version)
        return to_serializable(api_surface)
    except MigrationAnalysisError as e:
        logger.error(f"Migration analysis failed for {package_name} {version}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error analyzing API surface for {package_name} {version}: {e}")
        raise MigrationAnalysisError(f"Failed to analyze API surface: {e}") from e


@mcp.tool(
    description=(
        "Compare API surfaces between two versions of a package to identify "
        "breaking changes, additions, modifications, and deprecations. "
        "Provides detailed change analysis with impact levels and descriptions. "
        "Results are cached for performance."
    )
)
async def compare_package_versions(
    package_name: Annotated[str, "Package name to compare (e.g., 'django')."],
    old_version: Annotated[str, "Older version to compare from (e.g., '3.2.0')."],
    new_version: Annotated[str, "Newer version to compare to (e.g., '4.0.0')."],
) -> Dict[str, Any]:
    """
    Compare API surfaces between two package versions.

    Args:
      package_name: Name of the package to compare
      old_version: Starting version for comparison
      new_version: Target version for comparison

    Returns:
      VersionComparison JSON:
      {
        "package_name": str,
        "old_version": str,
        "new_version": str,
        "breaking_changes": [{"element_name": str, "change_type": str, "impact_level": str, ...}, ...],
        "additions": [{"element_name": str, "change_type": str, "impact_level": str, ...}, ...],
        "modifications": [{"element_name": str, "change_type": str, "impact_level": str, ...}, ...],
        "deprecations": [{"element_name": str, "change_type": str, "impact_level": str, ...}, ...],
        "dependency_changes": [str, ...],
        "analysis_timestamp": str
      }
    """
    try:
        logger.info(f"Comparing versions for {package_name}: {old_version} -> {new_version}")
        comparison = await _migration_analyzer.compare_versions(package_name, old_version, new_version)
        return to_serializable(comparison)
    except MigrationAnalysisError as e:
        logger.error(f"Version comparison failed for {package_name} {old_version} -> {new_version}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error comparing versions for {package_name} {old_version} -> {new_version}: {e}")
        raise MigrationAnalysisError(f"Failed to compare versions: {e}") from e


@mcp.tool(
    description=(
        "Find migration resources for upgrading between package versions. "
        "Searches for official migration guides, changelogs, community resources, "
        "and documentation links. Provides fallback resources when specific "
        "migration information is unavailable. Results are cached for performance."
    )
)
async def get_migration_resources(
    package_name: Annotated[str, "Package name to find migration resources for (e.g., 'flask')."],
    old_version: Annotated[str, "Starting version for migration (e.g., '1.1.0')."],
    new_version: Annotated[str, "Target version for migration (e.g., '2.0.0')."],
) -> Dict[str, Any]:
    """
    Find migration resources for upgrading between package versions.

    Args:
      package_name: Name of the package
      old_version: Starting version
      new_version: Target version

    Returns:
      MigrationResources JSON:
      {
        "package_name": str,
        "version_range": str,
        "official_guides": [{"title": str, "url": str, "type": str, "description": str, ...}, ...],
        "changelogs": [{"title": str, "url": str, "type": str, "description": str, ...}, ...],
        "community_resources": [{"title": str, "url": str, "type": str, "description": str, ...}, ...],
        "documentation_links": [{"title": str, "url": str, "type": str, "description": str, ...}, ...],
        "search_timestamp": str
      }
    """
    try:
        logger.info(f"Finding migration resources for {package_name}: {old_version} -> {new_version}")
        resources = await _migration_analyzer.find_migration_resources(package_name, old_version, new_version)
        return to_serializable(resources)
    except MigrationAnalysisError as e:
        logger.warning(f"Migration resource discovery failed for {package_name} {old_version} -> {new_version}: {e}")
        # Return the error but don't raise it - migration resources are best-effort
        return {
            "package_name": package_name,
            "version_range": f"{old_version} -> {new_version}",
            "official_guides": [],
            "changelogs": [],
            "community_resources": [],
            "documentation_links": [],
            "search_timestamp": None,
            "error": str(e)
        }
    except Exception as e:
        logger.warning(f"Unexpected error finding migration resources for {package_name} {old_version} -> {new_version}: {e}")
        # Return minimal fallback on unexpected error
        return {
            "package_name": package_name,
            "version_range": f"{old_version} -> {new_version}",
            "official_guides": [],
            "changelogs": [],
            "community_resources": [{
                "title": f"{package_name} - PyPI Project Page",
                "url": f"https://pypi.org/project/{package_name}/",
                "type": "documentation",
                "description": "PyPI project page - check description and project links for migration information",
                "source": "pypi"
            }],
            "documentation_links": [],
            "search_timestamp": None,
            "error": f"Resource discovery failed: {e}"
        }


async def cleanup_resources():
    """Clean up migration analyzer resources on shutdown."""
    try:
        await _migration_analyzer.cleanup()
    except Exception as e:
        logger.warning(f"Error during resource cleanup: {e}")


def main():
    parser = argparse.ArgumentParser(description="Run the Python Package MCP Server")
    parser.add_argument(
        "transport",
        nargs="?",
        default="stdio",
        help="Transport to run (stdio or streamable-http)",
    )
    args = parser.parse_args()
    
    # Set up cleanup handler
    import atexit
    atexit.register(lambda: asyncio.run(cleanup_resources()))
    
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()