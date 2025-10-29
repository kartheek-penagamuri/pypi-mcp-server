#!/usr/bin/env python3
"""
Live Package Upgrade Demo

This script demonstrates the MCP server tools by actually calling them
to analyze a package upgrade scenario. It creates a sample project and
walks through the upgrade process step by step.

Prerequisites:
- Virtual environment activated
- MCP server dependencies installed
- Run from the project root directory
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
import sys

# Add the src directory to Python path
sys.path.insert(0, 'src')

try:
    from mcp_server.server import (
        analyze_project_dependencies,
        get_package_metadata,
        get_latest_version,
        check_package_compatibility,
        analyze_package_api_surface,
        compare_package_versions,
        get_migration_resources
    )
except ImportError as e:
    print(f"❌ Failed to import MCP tools: {e}")
    print("Make sure you're running from the project root and have installed dependencies")
    sys.exit(1)


class LiveUpgradeDemo:
    """Live demonstration of package upgrade workflow."""
    
    def __init__(self):
        self.project_path = None
        
    def print_header(self, title: str):
        """Print a formatted section header."""
        print(f"\n{'='*60}")
        print(f"🔍 {title}")
        print('='*60)
        
    def print_result(self, data, title: str = "Result"):
        """Print formatted results."""
        print(f"\n📊 {title}:")
        if isinstance(data, dict):
            # Pretty print key information
            for key, value in data.items():
                if key in ['name', 'version', 'description', 'author']:
                    print(f"  {key}: {value}")
                elif key == 'dependencies' and isinstance(value, list):
                    print(f"  {key}: {len(value)} packages")
                elif key in ['breaking_changes', 'additions', 'modifications']:
                    if isinstance(value, list):
                        print(f"  {key}: {len(value)} items")
        else:
            print(f"  {data}")
    
    def create_sample_project(self) -> str:
        """Create a sample project with older package versions."""
        temp_dir = tempfile.mkdtemp(prefix="mcp_upgrade_demo_")
        self.project_path = temp_dir
        
        # Create requirements.txt with packages that have known upgrades
        requirements_content = """
requests==2.25.1
click==7.1.2
jinja2==2.11.3
"""
        
        requirements_path = Path(temp_dir) / "requirements.txt"
        requirements_path.write_text(requirements_content.strip())
        
        print(f"📁 Created demo project: {temp_dir}")
        print(f"📄 Requirements:\n{requirements_content}")
        
        return temp_dir
    
    async def run_upgrade_demo(self):
        """Run the complete upgrade demonstration."""
        print("🚀 Live Package Upgrade Demo")
        print("Demonstrating upgrade of 'requests' package using MCP tools")
        
        # Step 1: Create and analyze project
        self.print_header("Step 1: Project Analysis")
        project_path = self.create_sample_project()
        
        try:
            deps = analyze_project_dependencies(project_path)
            self.print_result(deps, "Current Dependencies")
            
            # Find requests dependency
            requests_dep = None
            for dep in deps.get('dependencies', []):
                if dep.get('name') == 'requests':
                    requests_dep = dep
                    break
            
            if requests_dep:
                current_version = requests_dep.get('version_spec', '').replace('==', '')
                print(f"📦 Found requests: {current_version}")
            else:
                current_version = "2.25.1"  # fallback
                
        except Exception as e:
            print(f"❌ Project analysis failed: {e}")
            return
        
        # Step 2: Get current package info
        self.print_header("Step 2: Current Package Information")
        try:
            current_info = get_package_metadata("requests", f"=={current_version}")
            self.print_result(current_info, f"Requests {current_version}")
        except Exception as e:
            print(f"❌ Failed to get current package info: {e}")
        
        # Step 3: Find latest version
        self.print_header("Step 3: Latest Version Discovery")
        try:
            latest_info = get_latest_version("requests")
            self.print_result(latest_info, "Latest Version")
            target_version = latest_info.get('version', '2.31.0')
            print(f"\n🎯 Upgrade path: {current_version} → {target_version}")
        except Exception as e:
            print(f"❌ Failed to get latest version: {e}")
            target_version = "2.31.0"  # fallback
        
        # Step 4: Compatibility check
        self.print_header("Step 4: Compatibility Analysis")
        try:
            compatibility = check_package_compatibility(
                "requests", 
                f"=={target_version}", 
                project_path
            )
            self.print_result(compatibility, "Compatibility Check")
            
            conflicts = compatibility.get('conflicts', [])
            if conflicts:
                print(f"⚠️  Found {len(conflicts)} potential conflicts")
            else:
                print("✅ No compatibility conflicts detected")
                
        except Exception as e:
            print(f"❌ Compatibility check failed: {e}")
        
        # Step 5: API Surface Analysis (if versions are available)
        self.print_header("Step 5: API Change Analysis")
        try:
            print(f"🔍 Comparing API: {current_version} vs {target_version}")
            comparison = await compare_package_versions("requests", current_version, target_version)
            self.print_result(comparison, "Version Comparison")
            
            # Highlight important changes
            breaking = comparison.get('breaking_changes', [])
            additions = comparison.get('additions', [])
            modifications = comparison.get('modifications', [])
            
            print(f"\n📈 Summary:")
            print(f"  Breaking changes: {len(breaking)}")
            print(f"  New features: {len(additions)}")
            print(f"  Modifications: {len(modifications)}")
            
            if breaking:
                print(f"\n⚠️  Breaking changes detected:")
                for change in breaking[:3]:  # Show first 3
                    name = change.get('element_name', 'Unknown')
                    change_type = change.get('change_type', 'Unknown')
                    print(f"    • {name}: {change_type}")
                    
        except Exception as e:
            print(f"❌ API analysis failed: {e}")
            print("This might be expected if package versions aren't available for analysis")
        
        # Step 6: Migration resources
        self.print_header("Step 6: Migration Resources")
        try:
            resources = await get_migration_resources("requests", current_version, target_version)
            self.print_result(resources, "Migration Resources")
            
            guides = resources.get('official_guides', [])
            changelogs = resources.get('changelogs', [])
            
            if guides:
                print(f"\n📚 Official guides found: {len(guides)}")
                for guide in guides[:2]:
                    print(f"  • {guide.get('title', 'Guide')}")
                    
            if changelogs:
                print(f"\n📝 Changelogs found: {len(changelogs)}")
                for log in changelogs[:2]:
                    print(f"  • {log.get('title', 'Changelog')}")
                    
        except Exception as e:
            print(f"❌ Migration resource search failed: {e}")
        
        # Step 7: Recommendations
        self.print_header("Step 7: Upgrade Recommendations")
        print("📋 Recommended next steps:")
        print("  1. 📚 Review any migration guides found above")
        print("  2. 🧪 Test the upgrade in a development environment")
        print(f"  3. 📝 Update requirements.txt: requests=={target_version}")
        print("  4. 🔄 Run: pip install -r requirements.txt")
        print("  5. ✅ Run your test suite to verify compatibility")
        
        print(f"\n🧹 Demo project created at: {project_path}")
        print("   (You can delete this directory when done)")


async def main():
    """Run the live upgrade demo."""
    demo = LiveUpgradeDemo()
    
    try:
        await demo.run_upgrade_demo()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Starting live MCP package upgrade demo...")
    print("Make sure you have activated your virtual environment!")
    
    # Check if we can import the required modules
    try:
        import mcp_server
        print("✅ MCP server modules found")
    except ImportError:
        print("❌ MCP server not found. Make sure you're in the right directory.")
        sys.exit(1)
    
    asyncio.run(main())