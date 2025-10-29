#!/usr/bin/env python3
"""
Demo: Package Upgrade Scenario using Python Package MCP Server

This script demonstrates a realistic package upgrade workflow using the MCP server tools.
It simulates upgrading Django from 3.2 to 4.2 in a sample project.

Usage:
    python demo_package_upgrade.py

Requirements:
    - MCP server running with the Python Package tools available
    - Sample project with requirements.txt or pyproject.toml
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any

# Import MCP tools (these would normally be called via MCP protocol)
# For demo purposes, we'll import them directly
import sys
sys.path.append('src')

from mcp_server.server import (
    analyze_project_dependencies,
    get_package_metadata, 
    get_latest_version,
    check_package_compatibility,
    analyze_package_api_surface,
    compare_package_versions,
    get_migration_resources
)


class PackageUpgradeDemo:
    """Demonstrates a complete package upgrade workflow."""
    
    def __init__(self):
        self.demo_project_path = None
        
    def create_sample_project(self) -> str:
        """Create a sample Django project for the demo."""
        # Create temporary directory for demo project
        temp_dir = tempfile.mkdtemp(prefix="django_upgrade_demo_")
        self.demo_project_path = temp_dir
        
        # Create requirements.txt with older Django version
        requirements_content = """
Django==3.2.0
psycopg2-binary==2.8.6
celery==5.1.0
redis==3.5.3
pillow==8.2.0
requests==2.25.1
"""
        
        requirements_path = Path(temp_dir) / "requirements.txt"
        requirements_path.write_text(requirements_content.strip())
        
        # Create a simple Django settings file to show API usage
        settings_content = '''
"""Django settings for demo project."""
import os
from django.conf import settings

# Basic Django settings
SECRET_KEY = 'demo-key-not-for-production'
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'demo_db',
    }
}

# Example of Django 3.2 API usage that might change
USE_TZ = True
USE_L10N = True  # Deprecated in Django 4.0
'''
        
        settings_path = Path(temp_dir) / "settings.py"
        settings_path.write_text(settings_content)
        
        print(f"📁 Created demo project at: {temp_dir}")
        return temp_dir
    
    def print_section(self, title: str):
        """Print a formatted section header."""
        print(f"\n{'='*60}")
        print(f"🔍 {title}")
        print('='*60)
    
    def print_json(self, data: Dict[str, Any], title: str = ""):
        """Pretty print JSON data."""
        if title:
            print(f"\n📊 {title}:")
        print(json.dumps(data, indent=2, default=str))
    
    async def run_demo(self):
        """Run the complete package upgrade demo."""
        print("🚀 Python Package MCP Server - Package Upgrade Demo")
        print("This demo shows upgrading Django from 3.2.0 to 4.2.x")
        
        # Step 1: Create sample project
        self.print_section("Step 1: Analyze Current Project")
        project_path = self.create_sample_project()
        
        # Analyze current dependencies
        current_deps = analyze_project_dependencies(project_path)
        self.print_json(current_deps, "Current Project Dependencies")
        
        # Step 2: Check current Django version info
        self.print_section("Step 2: Current Django Information")
        django_current = get_package_metadata("Django", "==3.2.0")
        self.print_json(django_current, "Django 3.2.0 Metadata")
        
        # Step 3: Find latest Django version
        self.print_section("Step 3: Find Latest Django Version")
        django_latest = get_latest_version("Django")
        self.print_json(django_latest, "Latest Django Version")
        
        target_version = django_latest['version']
        print(f"\n🎯 Target upgrade: Django 3.2.0 → {target_version}")
        
        # Step 4: Check compatibility with new Django version
        self.print_section("Step 4: Compatibility Check")
        compatibility = check_package_compatibility(
            "Django", 
            f"=={target_version}", 
            project_path
        )
        self.print_json(compatibility, "Compatibility Analysis")
        
        # Step 5: Analyze API changes between versions
        self.print_section("Step 5: API Surface Analysis")
        
        print("📋 Analyzing Django 3.2.0 API surface...")
        api_old = await analyze_package_api_surface("Django", "3.2.0")
        print(f"✅ Found {len(api_old.get('classes', []))} classes, {len(api_old.get('functions', []))} functions")
        
        print(f"📋 Analyzing Django {target_version} API surface...")
        api_new = await analyze_package_api_surface("Django", target_version)
        print(f"✅ Found {len(api_new.get('classes', []))} classes, {len(api_new.get('functions', []))} functions")
        
        # Step 6: Compare versions for breaking changes
        self.print_section("Step 6: Version Comparison & Breaking Changes")
        version_comparison = await compare_package_versions("Django", "3.2.0", target_version)
        self.print_json(version_comparison, "Version Comparison Results")
        
        # Highlight critical changes
        breaking_changes = version_comparison.get('breaking_changes', [])
        if breaking_changes:
            print(f"\n⚠️  Found {len(breaking_changes)} breaking changes:")
            for change in breaking_changes[:5]:  # Show first 5
                print(f"  • {change.get('element_name', 'Unknown')}: {change.get('change_type', 'Unknown change')}")
        
        # Step 7: Find migration resources
        self.print_section("Step 7: Migration Resources")
        migration_resources = await get_migration_resources("Django", "3.2.0", target_version)
        self.print_json(migration_resources, "Migration Resources")
        
        # Step 8: Generate upgrade recommendations
        self.print_section("Step 8: Upgrade Recommendations")
        self.generate_upgrade_plan(current_deps, version_comparison, migration_resources)
        
        # Cleanup
        print(f"\n🧹 Demo complete. Temporary files at: {project_path}")
        print("   (You can delete this directory when done)")
    
    def generate_upgrade_plan(self, current_deps: Dict, comparison: Dict, resources: Dict):
        """Generate actionable upgrade recommendations."""
        print("📋 Recommended Upgrade Plan:")
        print("\n1. 📚 Review Migration Resources:")
        
        official_guides = resources.get('official_guides', [])
        if official_guides:
            for guide in official_guides[:3]:  # Show top 3
                print(f"   • {guide.get('title', 'Migration Guide')}")
                print(f"     {guide.get('url', 'No URL')}")
        else:
            print("   • Check Django release notes and documentation")
        
        print("\n2. ⚠️  Address Breaking Changes:")
        breaking_changes = comparison.get('breaking_changes', [])
        if breaking_changes:
            critical_changes = [c for c in breaking_changes if c.get('impact_level') == 'high']
            for change in critical_changes[:3]:  # Show top 3 critical
                print(f"   • {change.get('element_name', 'Unknown')}: {change.get('description', 'Breaking change')}")
        else:
            print("   • No critical breaking changes detected")
        
        print("\n3. 🔄 Update Dependencies:")
        print("   • Update requirements.txt: Django==4.2.7")
        print("   • Run: pip install -r requirements.txt")
        print("   • Test thoroughly in development environment")
        
        print("\n4. 🧪 Testing Strategy:")
        print("   • Run existing test suite")
        print("   • Check for deprecation warnings")
        print("   • Verify database migrations work correctly")
        print("   • Test admin interface and user-facing features")
        
        print("\n5. 📝 Code Updates:")
        modifications = comparison.get('modifications', [])
        if modifications:
            print("   • Review modified APIs:")
            for mod in modifications[:3]:  # Show top 3
                print(f"     - {mod.get('element_name', 'Unknown')}")
        
        deprecations = comparison.get('deprecations', [])
        if deprecations:
            print("   • Address deprecations:")
            for dep in deprecations[:3]:  # Show top 3
                print(f"     - {dep.get('element_name', 'Unknown')}")


async def main():
    """Run the package upgrade demo."""
    demo = PackageUpgradeDemo()
    try:
        await demo.run_demo()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the async demo
    asyncio.run(main())