#!/usr/bin/env python3
"""
Simple Package Upgrade Demo

A minimal example showing how to use the MCP server tools to analyze
a package upgrade scenario. This demo focuses on upgrading requests
from an older version to the latest.

Run this after starting the MCP server to see the tools in action.
"""

import asyncio
import json
import tempfile
from pathlib import Path


def create_sample_requirements():
    """Create a sample requirements.txt with older package versions."""
    temp_dir = tempfile.mkdtemp(prefix="upgrade_demo_")
    requirements_content = """
requests==2.25.1
urllib3==1.26.5
certifi==2020.12.5
"""
    
    requirements_path = Path(temp_dir) / "requirements.txt"
    requirements_path.write_text(requirements_content.strip())
    
    print(f"📁 Created sample project at: {temp_dir}")
    print(f"📄 requirements.txt contains:\n{requirements_content}")
    
    return temp_dir


async def demo_package_upgrade():
    """Demonstrate package upgrade analysis workflow."""
    
    print("🚀 Package Upgrade Demo: requests 2.25.1 → latest")
    print("="*50)
    
    # Create sample project
    project_path = create_sample_requirements()
    
    # Note: In a real MCP client, these would be MCP tool calls
    # For this demo, we'll show the expected workflow
    
    print("\n🔍 Step 1: Analyze current project dependencies")
    print("MCP Tool Call: analyze_project_dependencies()")
    print("Expected result: List of current dependencies from requirements.txt")
    
    print("\n🔍 Step 2: Get current package info")
    print("MCP Tool Call: get_package_metadata('requests', '==2.25.1')")
    print("Expected result: Metadata for requests 2.25.1")
    
    print("\n🔍 Step 3: Find latest version")
    print("MCP Tool Call: get_latest_version('requests')")
    print("Expected result: Latest requests version (likely 2.31.x)")
    
    print("\n🔍 Step 4: Check compatibility")
    print("MCP Tool Call: check_package_compatibility('requests', '>=2.31.0')")
    print("Expected result: Compatibility analysis with other dependencies")
    
    print("\n🔍 Step 5: Compare API surfaces")
    print("MCP Tool Call: compare_package_versions('requests', '2.25.1', '2.31.0')")
    print("Expected result: Breaking changes, additions, modifications")
    
    print("\n🔍 Step 6: Find migration resources")
    print("MCP Tool Call: get_migration_resources('requests', '2.25.1', '2.31.0')")
    print("Expected result: Links to changelogs, migration guides")
    
    print(f"\n✅ Demo complete! Sample project created at: {project_path}")
    print("\nTo run with actual MCP tools:")
    print("1. Start the MCP server: python -m mcp_server.server")
    print("2. Connect your MCP client")
    print("3. Call the tools with the parameters shown above")
    
    return project_path


def create_mcp_client_example():
    """Create an example of how to call these tools from an MCP client."""
    
    example_calls = {
        "analyze_project": {
            "tool": "analyze_project_dependencies",
            "parameters": {
                "project_path": "/path/to/your/project"
            }
        },
        "get_metadata": {
            "tool": "get_package_metadata", 
            "parameters": {
                "package_name": "requests",
                "version_spec": "==2.25.1"
            }
        },
        "get_latest": {
            "tool": "get_latest_version",
            "parameters": {
                "package_name": "requests"
            }
        },
        "check_compatibility": {
            "tool": "check_package_compatibility",
            "parameters": {
                "new_package": "requests",
                "version_spec": ">=2.31.0",
                "project_path": "/path/to/your/project"
            }
        },
        "compare_versions": {
            "tool": "compare_package_versions",
            "parameters": {
                "package_name": "requests",
                "old_version": "2.25.1", 
                "new_version": "2.31.0"
            }
        },
        "migration_resources": {
            "tool": "get_migration_resources",
            "parameters": {
                "package_name": "requests",
                "old_version": "2.25.1",
                "new_version": "2.31.0"
            }
        }
    }
    
    return example_calls


if __name__ == "__main__":
    # Run the demo
    project_path = asyncio.run(demo_package_upgrade())
    
    print("\n" + "="*50)
    print("📋 MCP Tool Call Examples")
    print("="*50)
    
    examples = create_mcp_client_example()
    for step, call_info in examples.items():
        print(f"\n{step}:")
        print(f"  Tool: {call_info['tool']}")
        print(f"  Parameters: {json.dumps(call_info['parameters'], indent=4)}")