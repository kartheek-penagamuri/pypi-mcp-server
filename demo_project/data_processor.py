#!/usr/bin/env python3
"""
Data processing module using older pandas/numpy patterns.
This demonstrates code that might need updates when upgrading packages.
"""

import pandas as pd
import numpy as np
import requests
from typing import Dict, List, Any

class DataProcessor:
    """Processes data using older API patterns that might change in newer versions."""
    
    def __init__(self):
        self.cache = {}
    
    def fetch_remote_data(self, url: str) -> Dict[str, Any]:
        """Fetch data from remote API using requests (old version)."""
        
        # Using older requests patterns
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        return response.json()
    
    def process_dataframe(self, data: List[Dict]) -> pd.DataFrame:
        """Process data using older pandas patterns."""
        
        df = pd.DataFrame(data)
        
        # Using older pandas API patterns that might be deprecated
        if 'date' in df.columns:
            # Old way of handling datetime conversion
            df['date'] = pd.to_datetime(df['date'], infer_datetime_format=True)
        
        # Old way of handling missing values
        df = df.fillna(method='ffill')  # This might be deprecated in newer pandas
        
        # Old groupby syntax
        if 'category' in df.columns:
            grouped = df.groupby('category').agg({
                'value': ['mean', 'sum', 'count']
            })
            # Flatten column names (old way)
            grouped.columns = ['_'.join(col).strip() for col in grouped.columns.values]
            return grouped
        
        return df
    
    def calculate_statistics(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate statistics using older numpy/pandas patterns."""
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        stats = {}
        for col in numeric_cols:
            # Using older numpy functions that might have newer alternatives
            stats[f'{col}_mean'] = np.mean(df[col])
            stats[f'{col}_std'] = np.std(df[col])
            stats[f'{col}_median'] = np.median(df[col])
            
            # Old way of handling percentiles
            stats[f'{col}_p25'] = np.percentile(df[col], 25)
            stats[f'{col}_p75'] = np.percentile(df[col], 75)
        
        return stats
    
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