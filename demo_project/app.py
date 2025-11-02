#!/usr/bin/env python3
"""
Demo Flask application using older package versions.
This demonstrates a realistic project that needs package upgrades.
"""

import requests
import click
import pandas as pd
import numpy as np
from flask import Flask, render_template_string, jsonify
from jinja2 import Template

app = Flask(__name__)

# Using older API patterns that might have changed
@app.route('/')
def home():
    """Home page showing package versions and basic functionality."""
    
    # Get some data using requests (old version)
    try:
        response = requests.get('https://httpbin.org/json', timeout=5)
        api_data = response.json()
    except Exception as e:
        api_data = {"error": str(e)}
    
    # Create some data with pandas/numpy (old versions)
    data = pd.DataFrame({
        'values': np.random.rand(10),
        'categories': ['A', 'B', 'C'] * 3 + ['A']
    })
    
    # Use Jinja2 template (old version)
    template = Template("""
    <h1>Demo Project - Package Upgrade Candidate</h1>
    <h2>Current Package Versions:</h2>
    <ul>
        <li>Requests: {{ requests_version }}</li>
        <li>Flask: {{ flask_version }}</li>
        <li>Pandas: {{ pandas_version }}</li>
        <li>NumPy: {{ numpy_version }}</li>
        <li>Jinja2: {{ jinja2_version }}</li>
        <li>Click: {{ click_version }}</li>
    </ul>
    
    <h2>Sample Data ({{ data_rows }} rows):</h2>
    <pre>{{ data_preview }}</pre>
    
    <h2>API Response:</h2>
    <pre>{{ api_response }}</pre>
    
    <p><strong>Note:</strong> This project uses older package versions that could benefit from upgrades!</p>
    """)
    
    return template.render(
        requests_version=requests.__version__,
        flask_version=app.__class__.__module__.split('.')[0],  # Flask version detection
        pandas_version=pd.__version__,
        numpy_version=np.__version__,
        jinja2_version=Template.__module__.split('.')[0],
        click_version=click.__version__,
        data_rows=len(data),
        data_preview=data.head().to_string(),
        api_response=str(api_data)
    )

@app.route('/api/stats')
def api_stats():
    """API endpoint that uses pandas for data processing."""
    
    # Generate sample data
    data = pd.DataFrame({
        'timestamp': pd.date_range('2023-01-01', periods=100, freq='D'),
        'value': np.random.randn(100).cumsum()
    })
    
    # Calculate statistics (using older pandas API patterns)
    stats = {
        'count': len(data),
        'mean': float(data['value'].mean()),
        'std': float(data['value'].std()),
        'min': float(data['value'].min()),
        'max': float(data['value'].max()),
        'latest_date': data['timestamp'].max().isoformat()
    }
    
    return jsonify(stats)

@click.command()
@click.option('--port', default=5000, help='Port to run the server on')
@click.option('--debug', is_flag=True, help='Run in debug mode')
def run_server(port, debug):
    """Run the demo Flask application."""
    click.echo(f"Starting demo server on port {port}")
    click.echo("This project uses older package versions - perfect for upgrade testing!")
    
    if debug:
        click.echo("Debug mode enabled")
    
    app.run(host='0.0.0.0', port=port, debug=debug)

if __name__ == '__main__':
    run_server()