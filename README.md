# Python Package MCP Server

A Model Context Protocol (MCP) server that gives AI coding agents real-time awareness of the Python package ecosystem. It provides project-aware dependency analysis, PyPI metadata, upgrade planning, and migration signals so assistants can recommend and implement changes with confidence.

## What It Does

- Project analysis across `requirements.txt`, `pyproject.toml`, `Pipfile`, and basic `setup.py`
- Local-first package metadata with README/long description retrieval and PyPI fallback
- PyPI package search by keywords or exact names
- Compatibility checks for adding new dependencies
- Latest-version lookup with prerelease support
- API surface analysis and version-to-version diffs for migration planning
- Upgrade planner that proposes targets and risk levels from your dependency files

## Quick Start

Prerequisites: Python 3.10+ and Git.

```bash
git clone <repository-url>
cd pypi-mcp-server
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows (PowerShell)
# or: source .venv/bin/activate  # Linux/Mac
pip install -e .
```

### Running the Server

```bash
# Windows
.\run-mcp.bat

# Mac/Linux
./run-mcp.sh

# Or directly
python -m mcp_server.server stdio
```

### Running Tests

```bash
.\run-tests.bat         # Windows helper
# or
python -m pytest tests/ -v
```

## MCP Client Configuration

Example `mcp.json` entry:

```json
{
  "servers": {
    "pypi-mcp-server": {
      "command": "C:\\path\\to\\pypi-mcp-server\\run-mcp.bat",
      "args": [],
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

Mac/Linux: set `command` to `/path/to/pypi-mcp-server/run-mcp.sh`. Claude Desktop uses the same shape in `claude_desktop_config.json`.

## Available MCP Tools

1. `analyze_project_dependencies` - find and parse dependency files in a project.
2. `get_package_metadata` - return metadata, README, and dependencies (local-first).
3. `search_packages` - keyword search on PyPI with exact-name fallback.
4. `check_package_compatibility` - detect constraint conflicts before adding a package.
5. `get_latest_version` - fetch the latest non-yanked release with optional prereleases.
6. `plan_dependency_upgrades` - build an ordered upgrade plan with inferred risk levels.
7. `analyze_package_api_surface` - inspect a package version for public API elements.
8. `compare_package_versions` - diff API surfaces between two versions.
9. `get_migration_resources` - collect links to migration guides, changelogs, and docs.

## Usage Examples

```python
analyze_project_dependencies()
get_package_metadata("requests")
search_packages("http client", limit=5)
check_package_compatibility("fastapi", ">=0.110.0")
get_latest_version("django")
plan_dependency_upgrades(project_path=".")
await analyze_package_api_surface("pydantic", "2.9.0")
await compare_package_versions("openai", "0.27.8", "1.52.0")
await get_migration_resources("fastapi", "0.95.0", "0.115.0")
```

## Development Notes

Project layout:

```
src/mcp_server/
|- server.py              # MCP tool wiring
|- package_manager.py     # PyPI client and local metadata extraction
|- project_analyzer.py    # Dependency file parsing
|- migration_analyzer.py  # API surface and migration analysis
|- migration_guide_finder.py
|- version_comparator.py  # API comparison helpers
|- api_surface_extractor.py
|- models.py              # Data structures
|- utils.py               # Utility helpers
|- errors.py              # Custom exceptions
```

Guidelines:
- Local-first before PyPI network calls.
- Async-first for I/O-heavy operations.
- Clear exception hierarchy and structured logging.
- Tests use pytest with async fixtures and network mocking.

## Troubleshooting

- Activate the virtual environment and install with `pip install -e .`.
- Verify Python 3.10+ is available.
- Run `python -m pytest tests/ -v` for a quick health check.
- The server waits for MCP protocol messages when idle; this is expected.

## Demo Project

The `demo_project` folder contains the Meeting Notes AI Summarizer showcasing the server's upgrade tooling. It now uses the modern OpenAI client SDK with an offline mode for on-stage reliability. See `demo_project/UPGRADE_DEMO.md` for a guided script.

## License

MIT License - see `LICENSE`.
