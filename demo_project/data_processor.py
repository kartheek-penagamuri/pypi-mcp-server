#!/usr/bin/env python3
"""
Data processing module using MANY older pandas/numpy patterns.
This demonstrates a realistic legacy codebase that needs comprehensive updates.
"""

import pandas as pd
import numpy as np
import requests
import warnings
from typing import Dict, List, Any
from datetime import datetime

class DataProcessor:
    """Processes data using MANY older API patterns that will break in newer versions."""
    
    def __init__(self):
        self.cache = {}
        # Old way of suppressing warnings (deprecated)
        warnings.filterwarnings('ignore')
    
    def fetch_remote_data(self, url: str) -> Dict[str, Any]:
        """Fetch data from remote API using requests (old version)."""
        
        # Using older requests patterns
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        return response.json()
    
    def process_dataframe(self, data: List[Dict]) -> pd.DataFrame:
        """Process data using MANY older pandas patterns that WILL break in pandas 2.x."""
        
        df = pd.DataFrame(data)
        
        # OLD: Using deprecated infer_datetime_format (removed in pandas 2.0)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], infer_datetime_format=True)
        
        # OLD: Using deprecated fillna with method parameter (deprecated in pandas 2.0)
        df = df.fillna(method='ffill')
        
        # OLD: Using deprecated append method (REMOVED in pandas 2.0)
        if len(df) > 0:
            extra_row = pd.DataFrame({'category': ['Extra'], 'value': [999], 'date': [datetime.now()]})
            df = df.append(extra_row, ignore_index=True)
        
        # OLD: Using deprecated iteritems (REMOVED in pandas 2.0)
        print("Column info using deprecated iteritems:")
        for name, series in df.iteritems():
            print(f"  {name}: {len(series)} values")
        
        # OLD: Using deprecated lookup method (REMOVED in pandas 2.0)
        if 'category' in df.columns and len(df) > 1:
            try:
                lookup_result = df.lookup([0, 1], ['category', 'value'])
                print(f"Lookup result: {lookup_result}")
            except:
                pass  # Will fail in newer pandas
        
        # OLD: Using deprecated mad() method (REMOVED in pandas 2.0)
        if 'value' in df.columns:
            try:
                mad_value = df['value'].mad()
                print(f"Mean Absolute Deviation: {mad_value}")
            except:
                pass  # Will fail in newer pandas
        
        # OLD: Using deprecated groupby with level parameter
        if 'category' in df.columns:
            grouped = df.groupby('category').agg({
                'value': ['mean', 'sum', 'count']
            })
            # OLD: Flatten column names (deprecated way)
            grouped.columns = ['_'.join(col).strip() for col in grouped.columns.values]
            return grouped
        
        return df
    
    def calculate_statistics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate statistics using MANY older numpy/pandas patterns."""
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        stats = {}
        for col in numeric_cols:
            # OLD: Using numpy functions directly instead of pandas methods
            stats[f'{col}_mean'] = np.mean(df[col])
            stats[f'{col}_std'] = np.std(df[col])
            stats[f'{col}_median'] = np.median(df[col])
            
            # OLD: Using deprecated percentile function
            stats[f'{col}_p25'] = np.percentile(df[col], 25)
            stats[f'{col}_p75'] = np.percentile(df[col], 75)
            
            # OLD: Using deprecated mad() method
            try:
                stats[f'{col}_mad'] = df[col].mad()
            except:
                pass  # Will fail in pandas 2.0+
        
        return stats
    
    def legacy_data_operations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Demonstrate MORE legacy pandas operations that will break."""
        
        # OLD: Using deprecated slice_shift (removed in pandas 2.0)
        try:
            shifted = df.slice_shift(periods=1)
            print("Slice shift worked (pandas < 2.0)")
        except:
            print("Slice shift failed (pandas >= 2.0)")
        
        # OLD: Using deprecated tshift (removed in pandas 2.0)
        if 'date' in df.columns:
            try:
                time_shifted = df.tshift(periods=1, freq='D')
                print("Time shift worked (pandas < 2.0)")
            except:
                print("Time shift failed (pandas >= 2.0)")
        
        # OLD: Using deprecated align with method parameter
        if len(df) > 1:
            try:
                other_df = df.iloc[:2].copy()
                aligned = df.align(other_df, method='ffill')
                print("Align with method worked (pandas < 2.0)")
            except:
                print("Align with method failed (pandas >= 2.0)")
        
        # OLD: Using deprecated replace with method parameter
        try:
            replaced = df.replace(to_replace=np.nan, method='ffill')
            print("Replace with method worked (pandas < 2.0)")
        except:
            print("Replace with method failed (pandas >= 2.0)")
        
        return df
    
    def legacy_string_operations(self, df: pd.DataFrame) -> pd.DataFrame:
        """More legacy operations that will break."""
        
        # OLD: Using deprecated string accessor patterns
        if 'category' in df.columns:
            # This pattern might have issues in newer pandas
            try:
                # OLD: Direct string operations without proper accessor
                string_lengths = df['category'].str.len()
                print(f"String lengths: {string_lengths.tolist()}")
            except:
                pass
        
        return df
    
    def legacy_numpy_operations(self, data: np.ndarray) -> Dict[str, Any]:
        """Legacy numpy operations that might be deprecated."""
        
        results = {}
        
        # OLD: Using deprecated numpy functions
        try:
            # These might be deprecated or have better alternatives
            results['sum'] = np.sum(data)
            results['mean'] = np.mean(data)
            results['std'] = np.std(data)
            
            # OLD: Using deprecated numpy random functions
            np.random.seed(42)  # Old way of setting seed
            random_sample = np.random.random(10)
            results['random_mean'] = np.mean(random_sample)
            
        except Exception as e:
            print(f"Legacy numpy operations failed: {e}")
        
        return results
    
    def export_to_csv(self, df: pd.DataFrame, filename: str) -> None:
        """Export data using older pandas CSV export patterns."""
        
        # Using older pandas to_csv parameters
        df.to_csv(
            filename,
            index=False,
            encoding='utf-8',
            float_format='%.2f'
        )

def main():
    """Demo function showing the data processor in action."""
    
    processor = DataProcessor()
    
    # Generate sample data
    sample_data = [
        {'category': 'A', 'value': np.random.rand(), 'date': '2023-01-01'},
        {'category': 'B', 'value': np.random.rand(), 'date': '2023-01-02'},
        {'category': 'A', 'value': np.random.rand(), 'date': '2023-01-03'},
        {'category': 'C', 'value': np.random.rand(), 'date': '2023-01-04'},
    ]
    
    # Process the data
    df = processor.process_dataframe(sample_data)
    print("Processed DataFrame:")
    print(df)
    
    # Calculate statistics
    stats = processor.calculate_statistics(df)
    print("\nStatistics:")
    for key, value in stats.items():
        print(f"  {key}: {value:.4f}")

if __name__ == '__main__':
    main()