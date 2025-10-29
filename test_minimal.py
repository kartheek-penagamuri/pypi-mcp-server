import sys
sys.path.insert(0, 'src')

try:
    from mcp_server.migration_models import APIChange, APIElement, APISurface, VersionComparison
    print("migration_models import OK")
except Exception as e:
    print(f"migration_models import failed: {e}")

try:
    from mcp_server.errors import VersionComparisonError
    print("errors import OK")
except Exception as e:
    print(f"errors import failed: {e}")

try:
    from mcp_server.package_manager import PackageManager
    print("package_manager import OK")
except Exception as e:
    print(f"package_manager import failed: {e}")

# Now try to define a simple class
class TestClass:
    def __init__(self):
        pass

print(f"TestClass defined: {'TestClass' in locals()}")

# Try to import the version_comparator module
try:
    import mcp_server.version_comparator as vc
    print(f"version_comparator imported, contents: {[x for x in dir(vc) if not x.startswith('_')]}")
except Exception as e:
    print(f"version_comparator import failed: {e}")