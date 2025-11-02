#!/usr/bin/env python3
"""
Legacy utility functions using MANY deprecated patterns across multiple packages.
This file is a goldmine of technical debt that showcases the MCP server's value.
"""

import pandas as pd
import numpy as np
import requests
import json
import warnings
from datetime import datetime
from typing import Dict, List, Any, Optional

# OLD: Global warning suppression (bad practice)
warnings.filterwarnings('ignore')

class LegacyDataAnalyzer:
    """A class full of deprecated patterns that will break in newer versions."""
    
    def __init__(self):
        # OLD: Using deprecated numpy random seed
        np.random.seed(42)
        self.data_cache = {}
    
    def load_data_with_deprecated_patterns(self, file_path: str) -> pd.DataFrame:
        """Load data using MANY deprecated pandas patterns."""
        
        # OLD: Using deprecated read_csv parameters
        try:
            df = pd.read_csv(
                file_path,
                # OLD: These parameters might be deprecated
                squeeze=True,  # Deprecated in pandas 1.4
                prefix='col_',
                mangle_dupe_cols=True,
                warn_bad_lines=True,  # Deprecated
                error_bad_lines=False,  # Deprecated
                encoding_errors='ignore'  # Might be deprecated
            )
        except:
            # Fallback with basic read
            df = pd.read_csv(file_path)
        
        return df
    
    def process_with_deprecated_methods(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process DataFrame using MANY deprecated methods."""
        
        # OLD: Using deprecated append (REMOVED in pandas 2.0)
        try:
            new_row = pd.DataFrame({'A': [999], 'B': [888]})
            df = df.append(new_row, ignore_index=True)
        except:
            # Will fail in pandas 2.0+
            pass
        
        # OLD: Using deprecated iteritems (REMOVED in pandas 2.0)
        try:
            for col_name, col_data in df.iteritems():
                print(f"Processing column {col_name} with {len(col_data)} values")
        except:
            # Will fail in pandas 2.0+
            pass
        
        # OLD: Using deprecated lookup (REMOVED in pandas 2.0)
        try:
            if len(df) >= 2 and len(df.columns) >= 2:
                result = df.lookup([0, 1], df.columns[:2])
                print(f"Lookup result: {result}")
        except:
            # Will fail in pandas 2.0+
            pass
        
        # OLD: Using deprecated mad() (REMOVED in pandas 2.0)
        try:
            for col in df.select_dtypes(include=[np.number]).columns:
                mad_val = df[col].mad()
                print(f"MAD for {col}: {mad_val}")
        except:
            # Will fail in pandas 2.0+
            pass
        
        # OLD: Using deprecated fillna with method
        try:
            df = df.fillna(method='ffill')
            df = df.fillna(method='bfill')
        except:
            # Will fail in pandas 2.0+
            df = df.ffill().bfill()
        
        # OLD: Using deprecated slice_shift (REMOVED in pandas 2.0)
        try:
            shifted = df.slice_shift(periods=1)
            print("Slice shift successful")
        except:
            # Will fail in pandas 2.0+
            pass
        
        # OLD: Using deprecated tshift (REMOVED in pandas 2.0)
        try:
            time_shifted = df.tshift(periods=1)
            print("Time shift successful")
        except:
            # Will fail in pandas 2.0+
            pass
        
        return df
    
    def deprecated_groupby_operations(self, df: pd.DataFrame) -> pd.DataFrame:
        """GroupBy operations using deprecated patterns."""
        
        if len(df.columns) < 2:
            return df
        
        # OLD: Using deprecated groupby patterns
        try:
            # This groupby pattern might be deprecated
            grouped = df.groupby(df.columns[0]).agg({
                df.columns[1]: ['mean', 'sum', 'count', 'mad']  # mad is deprecated
            })
            
            # OLD: Flattening MultiIndex columns (old way)
            grouped.columns = ['_'.join(col).strip() for col in grouped.columns.values]
            
            return grouped
        except:
            return df
    
    def deprecated_datetime_operations(self, df: pd.DataFrame) -> pd.DataFrame:
        """DateTime operations using deprecated patterns."""
        
        # Create a datetime column for testing
        df['date_col'] = pd.date_range('2020-01-01', periods=len(df), freq='D')
        
        # OLD: Using deprecated infer_datetime_format
        try:
            date_strings = ['2020-01-01', '2020-01-02', '2020-01-03']
            parsed_dates = pd.to_datetime(date_strings, infer_datetime_format=True)
            print(f"Parsed dates: {parsed_dates}")
        except:
            # Will fail in pandas 2.0+
            pass
        
        # OLD: Using deprecated datetime accessor patterns
        try:
            # Some of these might be deprecated
            df['year'] = df['date_col'].dt.year
            df['month'] = df['date_col'].dt.month
            df['day'] = df['date_col'].dt.day
        except:
            pass
        
        return df
    
    def deprecated_string_operations(self, df: pd.DataFrame) -> pd.DataFrame:
        """String operations using deprecated patterns."""
        
        # Add a string column for testing
        df['string_col'] = ['test_' + str(i) for i in range(len(df))]
        
        # OLD: String operations that might be deprecated
        try:
            # These patterns might have issues in newer pandas
            df['string_length'] = df['string_col'].str.len()
            df['string_upper'] = df['string_col'].str.upper()
            df['string_contains'] = df['string_col'].str.contains('test')
        except:
            pass
        
        return df
    
    def deprecated_numpy_operations(self, data: np.ndarray) -> Dict[str, Any]:
        """NumPy operations using deprecated patterns."""
        
        results = {}
        
        # OLD: Using deprecated numpy functions and patterns
        try:
            # These might be deprecated or have better alternatives
            results['old_sum'] = np.sum(data)
            results['old_mean'] = np.mean(data)
            results['old_std'] = np.std(data)
            results['old_var'] = np.var(data)
            
            # OLD: Deprecated numpy random functions
            np.random.seed(42)  # Old way
            results['random_sample'] = np.random.random(5).tolist()
            results['random_normal'] = np.random.normal(0, 1, 5).tolist()
            
            # OLD: Deprecated array creation patterns
            results['zeros'] = np.zeros(5).tolist()
            results['ones'] = np.ones(5).tolist()
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
    
    def deprecated_json_operations(self, data: Dict[str, Any]) -> str:
        """JSON operations using deprecated patterns."""
        
        # OLD: Using deprecated json patterns (if any)
        try:
            # This might use deprecated json library patterns
            json_str = json.dumps(data, sort_keys=True, indent=2)
            return json_str
        except:
            return "{}"
    
    def deprecated_requests_operations(self, url: str) -> Dict[str, Any]:
        """HTTP requests using deprecated patterns."""
        
        try:
            # OLD: Using deprecated requests patterns
            response = requests.get(
                url,
                timeout=10,
                # These might be deprecated or have better alternatives
                stream=False,
                verify=True,
                allow_redirects=True
            )
            
            # OLD: Deprecated response handling
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            return {'error': str(e)}

def deprecated_utility_functions():
    """Standalone functions using deprecated patterns."""
    
    # OLD: Using deprecated pandas functions
    try:
        # These might be deprecated
        sample_data = pd.DataFrame({
            'A': [1, 2, 3, None, 5],
            'B': ['a', 'b', 'c', 'd', 'e']
        })
        
        # OLD: Deprecated operations
        filled_data = sample_data.fillna(method='ffill')
        
        # OLD: Deprecated iteritems
        for name, series in filled_data.iteritems():
            print(f"Column {name}: {len(series)} values")
            
    except Exception as e:
        print(f"Deprecated operations failed: {e}")

def main():
    """Demonstrate all the deprecated patterns."""
    
    print("Running legacy code with MANY deprecated patterns...")
    print("=" * 60)
    
    analyzer = LegacyDataAnalyzer()
    
    # Create sample data
    sample_df = pd.DataFrame({
        'A': np.random.randn(10),
        'B': np.random.randn(10),
        'category': np.random.choice(['X', 'Y', 'Z'], 10)
    })
    
    # Run all deprecated operations
    try:
        processed_df = analyzer.process_with_deprecated_methods(sample_df)
        grouped_df = analyzer.deprecated_groupby_operations(processed_df)
        datetime_df = analyzer.deprecated_datetime_operations(processed_df)
        string_df = analyzer.deprecated_string_operations(datetime_df)
        
        numpy_results = analyzer.deprecated_numpy_operations(sample_df['A'].values)
        print(f"NumPy results: {numpy_results}")
        
        deprecated_utility_functions()
        
        print("=" * 60)
        print("Legacy code execution completed!")
        print("Many operations may have failed in pandas 2.0+")
        
    except Exception as e:
        print(f"Legacy code failed: {e}")

if __name__ == '__main__':
    main()