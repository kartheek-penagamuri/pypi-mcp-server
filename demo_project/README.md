# Meeting Notes AI Summarizer Demo

This demo project showcases how the **Python Package MCP Server** can help analyze and upgrade legacy dependencies in a real-world Python application.

## Project Overview

This is an AI-powered meeting notes summarizer that uses the **legacy OpenAI Python package (v0.27.8)** with deprecated APIs. It's perfect for demonstrating package upgrade scenarios because:

- Uses old `openai.Completion.create()` API (deprecated)
- Uses legacy engine names like `text-davinci-003`
- Uses outdated authentication patterns
- Has other dependencies with security vulnerabilities

## Features

- 📝 Summarize standup meeting notes with AI
- 🎯 Extract action items automatically  
- 💻 Command-line interface with sample data
- 🔧 Uses intentionally outdated packages for upgrade demo

## Installation

```bash
# Install legacy dependencies (intentionally old versions)
pip install -r requirements.txt
```

## Usage

### With Sample Data (No API Key Required)
```bash
python cli_app.py --use-sample
```

### With Your Own Notes
```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Use a notes file
python cli_app.py --notes-file sample_meeting_notes.txt

# Or enter notes interactively
python cli_app.py
```

## Legacy Code Issues

This project intentionally uses deprecated patterns that an AI agent can help identify and fix:

### 1. OpenAI API (v0.27.8 → v1.x)
- ❌ `openai.api_key = key` (deprecated)
- ❌ `openai.Completion.create()` (deprecated) 
- ❌ `engine="text-davinci-003"` (legacy)
- ✅ Should use `OpenAI(api_key=key)` client
- ✅ Should use `client.chat.completions.create()`
- ✅ Should use `model="gpt-3.5-turbo"`

### 2. Security Vulnerabilities
- ❌ `requests==2.25.1` (has known CVEs)
- ❌ Old dependencies with security issues
- ✅ Should upgrade to latest secure versions

### 3. Deprecated Patterns
- ❌ Old-style string formatting in some places
- ❌ Legacy exception handling patterns
- ✅ Should use modern Python practices

## MCP Server Demo Workflow

### 1. Analyze Current Dependencies
Ask your AI agent:
> "Analyze the dependencies in this meeting summarizer project and check for upgrades"

### 2. Identify Upgrade Opportunities
The AI will discover:
- `openai 0.27.8 → 1.40.0` (major API changes)
- `requests 2.25.1 → 2.31.0` (security fixes)
- `click 7.1.2 → 8.1.7` (new features)

### 3. Check Compatibility Issues
> "What breaking changes will happen if I upgrade OpenAI to v1.x?"

### 4. Get Migration Guidance
> "Help me migrate this code to use the new OpenAI v1.x API"

### 5. Update the Code
The AI can help rewrite `meeting_summarizer.py` to use:
- Modern OpenAI client initialization
- New ChatCompletion API instead of legacy Completion
- Updated model names and parameters
- Better error handling

## Sample Meeting Notes

The project includes sample meeting notes in `sample_meeting_notes.txt` for testing the summarization features.

## Expected AI Agent Interaction

```
Human: Please analyze this meeting summarizer project and suggest upgrades

AI: I'll analyze your meeting summarizer dependencies and check for available upgrades.

Found several critical upgrades needed:

🚨 SECURITY ISSUES:
- requests 2.25.1 → 2.31.0 (fixes CVE-2023-32681)

🔄 MAJOR API CHANGES:
- openai 0.27.8 → 1.40.0 (complete API rewrite)

The OpenAI package has breaking changes. Your current code uses:
- openai.api_key = key (deprecated)
- openai.Completion.create() (removed)
- engine="text-davinci-003" (legacy)

Would you like me to help migrate to the new OpenAI v1.x API?
```

This creates a realistic scenario where an AI agent can demonstrate the value of automated dependency analysis and guided code migration.