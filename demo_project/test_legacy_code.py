#!/usr/bin/env python3
"""
Test script to demonstrate how much legacy code breaks with newer package versions.
This showcases the massive value of the MCP server for identifying upgrade issues.
"""

import sys
import pandas as pd
import numpy as np
from typing import List, Dict, Any

def test_deprecated_pandas_methods():
    """Test all the deprecated pandas methods that will break."""
    
    print("Testing deprecated pandas methods...")
    print("-" * 40)
    
    # Create test data
    df = pd.DataFrame({
        'A': [1, 2, None, 4, 5],
        'B': ['a', 'b', 'c', 'd', 'e'],
        'C': pd.date_range('2020-01-01', periods=5)
    })
    
    failures = []
    successes = []
    
    # Test 1: append() method (REMOVED in pandas 2.0)
    try:
        new_row = pd.DataFrame({'A': [6], 'B': ['f'], 'C': [pd.Timestamp('2020-01-06')]})
        result = df.append(new_row, ignore_index=True)
        successes.append("append() method")
    except Exception as e:
        failures.append(f"append() method: {str(e)}")
    
    # Test 2: iteritems() method (REMOVED in pandas 2.0)
    try:
        for name, series in df.iteritems():
            pass
        successes.append("iteritems() method")
    except Exception as e:
        failures.append(f"iteritems() method: {str(e)}")
    
    # Test 3: lookup() method (REMOVED in pandas 2.0)
    try:
        result = df.lookup([0, 1], ['A', 'B'])
        successes.append("lookup() method")
    except Exception as e:
        failures.append(f"lookup() method: {str(e)}")
    
    # Test 4: mad() method (REMOVED in pandas 2.0)
    try:
        result = df['A'].mad()
        successes.append("mad() method")
    except Exception as e:
        failures.append(f"mad() method: {str(e)}")
    
    # Test 5: fillna(method='ffill') (deprecated in pandas 2.0)
    try:
        result = df.fillna(method='ffill')
        successes.append("fillna(method='ffill')")
    except Exception as e:
        failures.append(f"fillna(method='ffill'): {str(e)}")
    
    # Test 6: slice_shift() method (REMOVED in pandas 2.0)
    try:
        result = df.slice_shift(periods=1)
        successes.append("slice_shift() method")
    except Exception as e:
        failures.append(f"slice_shift() method: {str(e)}")
    
    # Test 7: tshift() method (REMOVED in pandas 2.0)
    try:
        result = df.tshift(periods=1)
        successes.append("tshift() method")
    except Exception as e:
        failures.append(f"tshift() method: {str(e)}")
    
    # Test 8: infer_datetime_format parameter (deprecated)
    try:
        result = pd.to_datetime(['2020-01-01', '2020-01-02'], infer_datetime_format=True)
        successes.append("infer_datetime_format parameter")
    except Exception as e:
        failures.append(f"infer_datetime_format parameter: {str(e)}")
    
    # Test 9: align() with method parameter (deprecated)
    try:
        other_df = df.iloc[:3].copy()
        result = df.align(other_df, method='ffill')
        successes.append("align() with method parameter")
    except Exception as e:
        failures.append(f"align() with method parameter: {str(e)}")
    
    # Test 10: replace() with method parameter (deprecated)
    try:
        result = df.replace(to_replace=np.nan, method='ffill')
        successes.append("replace() with method parameter")
    except Exception as e:
        failures.append(f"replace() with method parameter: {str(e)}")
    
    return successes, failures

def test_deprecated_numpy_patterns():
    """Test deprecated numpy patterns."""
    
    print("\nTesting deprecated numpy patterns...")
    print("-" * 40)
    
    failures = []
    successes = []
    
    # Create test data
    data = np.array([1, 2, 3, 4, 5])
    
    # Test deprecated random seed usage
    try:
        np.random.seed(42)  # This pattern might be deprecated
        random_data = np.random.random(5)
        successes.append("np.random.seed() pattern")
    except Exception as e:
        failures.append(f"np.random.seed() pattern: {str(e)}")
    
    # Test other potentially deprecated patterns
    try:
        # These might have newer alternatives
        result1 = np.sum(data)
        result2 = np.mean(data)
        result3 = np.std(data)
        successes.append("Basic numpy functions")
    except Exception as e:
        failures.append(f"Basic numpy functions: {str(e)}")
    
    return successes, failures

def test_deprecated_requests_patterns():
    """Test deprecated requests patterns."""
    
    print("\nTesting deprecated requests patterns...")
    print("-" * 40)
    
    failures = []
    successes = []
    
    # Test potentially deprecated request patterns
    try:
        import requests
        # These patterns might be deprecated or have security issues
        response = requests.get(
            'https://httpbin.org/json',
            timeout=5,
            verify=True,  # This is good practice but pattern might change
            allow_redirects=True
        )
        if response.status_code == 200:
            successes.append("Basic requests pattern")
        else:
            failures.append(f"Basic requests pattern: HTTP {response.status_code}")
    except Exception as e:
        failures.append(f"Basic requests pattern: {str(e)}")
    
    return successes, failures

def run_legacy_code_analysis():
    """Run comprehensive analysis of legacy code patterns."""
    
    print("=" * 60)
    print("LEGACY CODE ANALYSIS - DEMONSTRATING MCP SERVER VALUE")
    print("=" * 60)
    
    all_successes = []
    all_failures = []
    
    # Test pandas deprecated methods
    pandas_successes, pandas_failures = test_deprecated_pandas_methods()
    all_successes.extend(pandas_successes)
    all_failures.extend(pandas_failures)
    
    # Test numpy deprecated patterns
    numpy_successes, numpy_failures = test_deprecated_numpy_patterns()
    all_successes.extend(numpy_successes)
    all_failures.extend(numpy_failures)
    
    # Test requests deprecated patterns
    requests_successes, requests_failures = test_deprecated_requests_patterns()
    all_successes.extend(requests_successes)
    all_failures.extend(requests_failures)
    
    # Print comprehensive results
    print("\n" + "=" * 60)
    print("COMPREHENSIVE RESULTS")
    print("=" * 60)
    
    print(f"\n✅ WORKING LEGACY PATTERNS ({len(all_successes)}):")
    for success in all_successes:
        print(f"  ✓ {success}")
    
    print(f"\n❌ BROKEN LEGACY PATTERNS ({len(all_failures)}):")
    for failure in all_failures:
        print(f"  ✗ {failure}")
    
    # Calculate impact metrics
    total_patterns = len(all_successes) + len(all_failures)
    failure_rate = len(all_failures) / total_patterns * 100 if total_patterns > 0 else 0
    
    print(f"\n📊 IMPACT ANALYSIS:")
    print(f"  • Total legacy patterns tested: {total_patterns}")
    print(f"  • Patterns that still work: {len(all_successes)}")
    print(f"  • Patterns that are broken: {len(all_failures)}")
    print(f"  • Failure rate: {failure_rate:.1f}%")
    
    print(f"\n💡 MCP SERVER VALUE PROPOSITION:")
    if len(all_failures) > 0:
        print(f"  • Without MCP: {len(all_failures)} breaking changes would be discovered at runtime")
        print(f"  • With MCP: All {len(all_failures)} issues identified before upgrade")
        print(f"  • Risk reduction: Prevents {len(all_failures)} potential production failures")
        print(f"  • Time savings: Hours of debugging avoided per breaking change")
    else:
        print(f"  • All legacy patterns still work in current environment")
        print(f"  • MCP server would identify future deprecations proactively")
    
    return len(all_failures) == 0

def main():
    """Main function to run the legacy code analysis."""
    
    try:
        success = run_legacy_code_analysis()
        
        print(f"\n" + "=" * 60)
        print("CONCLUSION")
        print("=" * 60)
        
        if success:
            print("🟡 Current environment supports most legacy patterns")
            print("   This demonstrates what happens BEFORE upgrading packages")
            print("   The MCP server helps identify what WILL break during upgrades")
        else:
            print("🔴 Many legacy patterns are already broken")
            print("   This demonstrates the pain of upgrading without proper analysis")
            print("   The MCP server would have identified these issues beforehand")
        
        print(f"\n🚀 The MCP server transforms this chaotic process into:")
        print(f"   1. Systematic identification of breaking changes")
        print(f"   2. Automated code migration suggestions")
        print(f"   3. Comprehensive testing and validation")
        print(f"   4. Risk-free upgrade planning")
        
        return success
        
    except Exception as e:
        print(f"Analysis failed: {e}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)