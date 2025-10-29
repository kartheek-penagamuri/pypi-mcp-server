# Package Upgrade Demo Scripts

This directory contains demonstration scripts showcasing the Python Package MCP Server's package upgrade analysis capabilities.

## Demo Scripts

### 1. `demo_simple_upgrade.py` - Conceptual Demo
A simple walkthrough that shows the upgrade workflow without actually calling the MCP tools. Good for understanding the process.

```bash
python demo_simple_upgrade.py
```

### 2. `demo_live_upgrade.py` - Live Demo ⭐ **Recommended**
Actually calls the MCP server tools to demonstrate a real package upgrade scenario (requests 2.25.1 → latest).

```bash
# Make sure you're in the project root with venv activated
python demo_live_upgrade.py
```

### 3. `demo_package_upgrade.py` - Comprehensive Demo
Full-featured demo showing Django upgrade scenario with detailed analysis.

```bash
python demo_package_upgrade.py
```

## What the Demo Shows

The demos walk through a complete package upgrade workflow:

1. **📁 Project Analysis** - Scan current dependencies
2. **📦 Package Info** - Get metadata for current version
3. **🔍 Version Discovery** - Find latest available version
4. **⚖️ Compatibility Check** - Verify no conflicts with other packages
5. **🔬 API Analysis** - Compare API surfaces between versions
6. **📚 Migration Resources** - Find upgrade guides and changelogs
7. **📋 Recommendations** - Generate actionable upgrade plan

## MCP Tools Demonstrated

- `analyze_project_dependencies()` - Parse requirements.txt/pyproject.toml
- `get_package_metadata()` - Get package information
- `get_latest_version()` - Find newest version on PyPI
- `check_package_compatibility()` - Validate version constraints
- `analyze_package_api_surface()` - Extract API elements
- `compare_package_versions()` - Identify breaking changes
- `get_migration_resources()` - Find upgrade documentation

## Prerequisites

1. **Virtual Environment**: Activate your Python virtual environment
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

2. **Dependencies**: Install the MCP server dependencies
   ```bash
   pip install -e .
   ```

3. **Working Directory**: Run from the project root directory

## Sample Output

The live demo will show output like:

```
🚀 Live Package Upgrade Demo
Demonstrating upgrade of 'requests' package using MCP tools

============================================================
🔍 Step 1: Project Analysis
============================================================
📁 Created demo project: /tmp/mcp_upgrade_demo_xyz
📄 Requirements:
requests==2.25.1
click==7.1.2
jinja2==2.11.3

📊 Current Dependencies:
  dependencies: 3 packages
📦 Found requests: 2.25.1

============================================================
🔍 Step 2: Current Package Information
============================================================
📊 Requests 2.25.1:
  name: requests
  version: 2.25.1
  description: Python HTTP for Humans.
  author: Kenneth Reitz

🎯 Upgrade path: 2.25.1 → 2.31.0
```

## Use Cases

These demos are perfect for:

- **Understanding the MCP server capabilities**
- **Testing the package upgrade workflow**
- **Demonstrating to stakeholders**
- **Learning the tool APIs**
- **Debugging MCP server issues**

## Troubleshooting

**Import Errors**: Make sure you're running from the project root and have installed dependencies:
```bash
pip install -e .
```

**Network Issues**: Some tools require internet access to query PyPI. The tools gracefully handle network failures.

**Missing Packages**: The API analysis tools work best with packages that are available locally or on PyPI.

## Next Steps

After running the demos:

1. Try with your own project by changing the `project_path` parameter
2. Test different packages and version ranges
3. Integrate the MCP tools into your own upgrade workflows
4. Use the tools via MCP protocol in your preferred AI assistant

## Real MCP Usage

In production, these tools would be called via the MCP protocol from an AI assistant:

```json
{
  "method": "tools/call",
  "params": {
    "name": "analyze_project_dependencies",
    "arguments": {
      "project_path": "/path/to/your/project"
    }
  }
}
```

The demos show the direct Python API calls for easier testing and development.