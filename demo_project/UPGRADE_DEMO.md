# MCP Server + AI Agent Upgrade Demo

This demo project is designed to showcase how the **Python Package MCP Server** works with an **AI coding agent** to analyze and upgrade package dependencies.

## Demo Workflow

Instead of running a standalone script, this demonstrates the **interactive AI-assisted upgrade process**:

### 1. AI Agent Analyzes the Project
Ask your AI coding agent:
> "Please analyze the dependencies in this demo_project folder and check for available upgrades"

The AI will use MCP tools like:
- `analyze_project_dependencies()` to scan requirements.txt
- `get_latest_version()` to check for newer versions
- `get_package_metadata()` to understand current packages

### 2. AI Agent Identifies Upgrade Opportunities  
The AI will discover packages like:
- requests 2.25.1 → 2.31.0 (security fixes)
- pandas 1.3.0 → 2.1.0 (major version jump)
- flask 1.1.4 → 3.0.0 (breaking changes)

### 3. AI Agent Performs Compatibility Analysis
Ask the AI:
> "Check if upgrading pandas to the latest version would cause any conflicts"

The AI uses:
- `check_package_compatibility()` to verify version constraints
- `compare_package_versions()` to identify breaking changes
- `get_migration_resources()` to find upgrade guides

### 4. AI Agent Plans the Migration
The AI will:
- Prioritize upgrades by risk level
- Identify deprecated code patterns that need updates
- Suggest a step-by-step upgrade plan
- Find relevant migration documentation

### 5. AI Agent Assists with Code Updates
Ask the AI:
> "Help me update the deprecated pandas code in data_processor.py"

The AI can:
- Identify deprecated `fillna(method='ffill')` usage
- Suggest modern alternatives like `fillna(method='ffill')` → `ffill()`
- Update import statements and API calls
- Modify requirements.txt with new versions

## Example AI Conversation

```
Human: Please analyze the demo_project dependencies and suggest upgrades

AI: I'll analyze your demo project dependencies and check for available upgrades.

[AI uses MCP tools to analyze the project]

I found several packages that can be upgraded:
- requests: 2.25.1 → 2.31.0 (security improvements)
- pandas: 1.3.0 → 2.1.0 (major performance improvements)
- flask: 1.1.4 → 3.0.0 (breaking changes - needs careful migration)

Let me check for compatibility issues and breaking changes...

[AI uses more MCP tools for detailed analysis]

I found some deprecated code in data_processor.py that will break with pandas 2.x:
- Line 34: `df.fillna(method='ffill')` is deprecated
- Line 45: Old groupby column flattening syntax

Would you like me to help update this code for the newer pandas version?