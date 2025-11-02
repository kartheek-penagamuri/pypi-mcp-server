#!/usr/bin/env python3
"""
CLI tool using older Click patterns.
Demonstrates command-line interface that might benefit from package upgrades.
"""

import click
import requests
import pandas as pd
import json
from pathlib import Path
from data_processor import DataProcessor

@click.group()
@click.version_option(version='1.0.0')
def cli():
    """Demo CLI tool using older package versions."""
    pass

@cli.command()
@click.argument('url')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', 'output_format', type=click.Choice(['json', 'csv']), 
              default='json', help='Output format')
def fetch(url, output, output_format):
    """Fetch data from a URL and save it."""
    
    click.echo(f"Fetching data from: {url}")
    
    try:
        # Using older requests patterns
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        click.echo(f"✓ Successfully fetched {len(data) if isinstance(data, list) else 1} records")
        
        if output:
            if output_format == 'json':
                with open(output, 'w') as f:
                    json.dump(data, f, indent=2)
            elif output_format == 'csv':
                df = pd.DataFrame(data if isinstance(data, list) else [data])
                df.to_csv(output, index=False)
            
            click.echo(f"✓ Data saved to: {output}")
        else:
            click.echo("Data preview:")
            if isinstance(data, list):
                for i, item in enumerate(data[:3]):
                    click.echo(f"  [{i}]: {item}")
                if len(data) > 3:
                    click.echo(f"  ... and {len(data) - 3} more items")
            else:
                click.echo(f"  {data}")
                
    except requests.RequestException as e:
        click.echo(f"✗ Error fetching data: {e}", err=True)
        raise click.Abort()

@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--stats', is_flag=True, help='Show statistics')
@click.option('--head', type=int, default=5, help='Number of rows to show')
def analyze(input_file, stats, head):
    """Analyze a CSV or JSON data file."""
    
    click.echo(f"Analyzing file: {input_file}")
    
    try:
        file_path = Path(input_file)
        
        if file_path.suffix.lower() == '.json':
            with open(file_path) as f:
                data = json.load(f)
            df = pd.DataFrame(data if isinstance(data, list) else [data])
        elif file_path.suffix.lower() == '.csv':
            df = pd.read_csv(file_path)
        else:
            click.echo("✗ Unsupported file format. Use .json or .csv", err=True)
            raise click.Abort()
        
        click.echo(f"✓ Loaded {len(df)} rows, {len(df.columns)} columns")
        
        # Show data preview
        click.echo(f"\nFirst {head} rows:")
        click.echo(df.head(head).to_string())
        
        if stats:
            processor = DataProcessor()
            statistics = processor.calculate_statistics(df)
            
            click.echo("\nStatistics:")
            for key, value in statistics.items():
                click.echo(f"  {key}: {value:.4f}")
        
    except Exception as e:
        click.echo(f"✗ Error analyzing file: {e}", err=True)
        raise click.Abort()

@cli.command()
@click.option('--rows', type=int, default=100, help='Number of rows to generate')
@click.option('--output', '-o', type=click.Path(), required=True, help='Output file path')
def generate(rows, output):
    """Generate sample data for testing."""
    
    click.echo(f"Generating {rows} rows of sample data...")
    
    import numpy as np
    
    # Generate sample data using older numpy patterns
    data = {
        'id': range(1, rows + 1),
        'category': np.random.choice(['A', 'B', 'C'], rows),
        'value': np.random.randn(rows),
        'timestamp': pd.date_range('2023-01-01', periods=rows, freq='H')
    }
    
    df = pd.DataFrame(data)
    
    # Save using older pandas patterns
    output_path = Path(output)
    if output_path.suffix.lower() == '.csv':
        df.to_csv(output_path, index=False)
    elif output_path.suffix.lower() == '.json':
        df.to_json(output_path, orient='records', date_format='iso')
    else:
        click.echo("✗ Output file must have .csv or .json extension", err=True)
        raise click.Abort()
    
    click.echo(f"✓ Generated data saved to: {output}")

if __name__ == '__main__':
    cli()