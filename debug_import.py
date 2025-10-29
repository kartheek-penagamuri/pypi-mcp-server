import sys
import traceback
sys.path.insert(0, 'src')

try:
    print("Attempting to import version_comparator...")
    import mcp_server.version_comparator as vc
    print(f"Import successful. Contents: {dir(vc)}")
    print(f"VersionComparator in module: {'VersionComparator' in dir(vc)}")
except Exception as e:
    print(f"Import failed with error: {e}")
    traceback.print_exc()

# Try to execute the file directly
try:
    print("\nTrying to execute file directly...")
    with open('src/mcp_server/version_comparator.py', 'r') as f:
        code = f.read()
    
    # Create a new namespace
    namespace = {}
    exec(code, namespace)
    print(f"Direct execution successful. Contents: {[k for k in namespace.keys() if not k.startswith('_')]}")
    
except Exception as e:
    print(f"Direct execution failed: {e}")
    traceback.print_exc()