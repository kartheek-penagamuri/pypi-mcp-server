# Demo Project - Package Upgrade Candidate

This is a sample Python project that uses **older versions** of popular packages. It's designed to demonstrate how the Python Package MCP Server can help identify and plan package upgrades.

## Current Package Versions (Intentionally Old)

- **requests**: 2.25.1 (current latest: ~2.31.0)
- **flask**: 1.1.4 (current latest: ~3.0.0) 
- **pandas**: 1.3.0 (current latest: ~2.1.0)
- **numpy**: 1.21.0 (current latest: ~1.25.0)
- **jinja2**: 2.11.3 (current latest: ~3.1.0)
- **click**: 7.1.2 (current latest: ~8.1.0)

## Project Structure

```
demo_project/
├── requirements.txt      # Old package versions
├── app.py               # Flask web application
├── data_processor.py    # Data processing with pandas/numpy
├── cli_tool.py          # Command-line tool with Click
└── README.md           # This file
```

## What This Project Does

### 1. Web Application (`app.py`)
- Simple Flask web server
- Uses requests to fetch external data
- Processes data with pandas/numpy
- Renders templates with Jinja2
- Shows current package versions

### 2. Data Processor (`data_processor.py`)
- Fetches data from APIs using requests
- Processes DataFrames with older pandas patterns
- Uses deprecated pandas methods (like `fillna(method='ffill')`)
- Calculates statistics with older numpy functions

### 3. CLI Tool (`cli_tool.py`)
- Command-line interface built with Click
- Fetch data from URLs
- Analyze CSV/JSON files
- Generate sample datasets

## Running the Demo

### Setup
```bash
cd demo_project
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Web Application
```bash
python app.py --port 5000
# Visit http://localhost:5000
```

### CLI Tool
```bash
# Generate sample data
python cli_tool.py generate --rows 50 --output sample.csv

# Analyze the data
python cli_tool.py analyze sample.csv --stats

# Fetch external data
python cli_tool.py fetch https://httpbin.org/json --output api_data.json
```

## Package Upgrade Opportunities

This project is perfect for demonstrating package upgrades because:

### 1. **Security Issues**
- Older versions may have known vulnerabilities
- Newer versions include security patches

### 2. **Deprecated APIs**
- `pandas.fillna(method='ffill')` is deprecated
- Some numpy functions have newer alternatives
- Flask 1.x to 2.x/3.x has breaking changes

### 3. **Performance Improvements**
- Newer pandas/numpy versions are faster
- Better memory usage in recent versions

### 4. **New Features**
- Missing out on new functionality
- Better type hints and error messages

## Using with MCP Server + AI Agent

This project demonstrates the **AI-assisted package upgrade workflow**:

### 1. Ask AI to Analyze Dependencies
> "Please analyze the dependencies in this demo_project and check for upgrades"

The AI agent will use MCP tools to:
- Scan requirements.txt for current versions
- Check PyPI for latest versions  
- Identify upgrade opportunities

### 2. Request Compatibility Analysis
> "Check if upgrading pandas to 2.x would cause conflicts"

The AI will:
- Verify version constraints across all dependencies
- Identify potential breaking changes
- Find migration documentation

### 3. Get Code Update Assistance  
> "Help me update the deprecated pandas code for version 2.x"

The AI can:
- Identify deprecated API usage
- Suggest modern alternatives
- Update the actual code files
- Modify requirements.txt

This showcases how MCP tools enable AI agents to provide intelligent, context-aware package upgrade assistance.

## Expected Upgrade Challenges

When upgrading this project, you might encounter:

- **Pandas**: `fillna(method=)` parameter removed
- **Flask**: Blueprint registration changes
- **NumPy**: Some function signatures changed
- **Click**: Type annotation improvements
- **Jinja2**: Security and API updates

This makes it an excellent test case for the MCP server's upgrade analysis capabilities!

## Testing the MCP Server

Use this project to test:
- Dependency parsing accuracy
- Version comparison logic
- API change detection
- Migration guide discovery
- Compatibility checking

The intentionally old versions ensure there are real upgrade paths and potential issues to discover.