# MCP Server + AI Agent Upgrade Demo

This demo project showcases how the **Python Package MCP Server** works with an **AI coding agent** to analyze and upgrade legacy dependencies in a real-world application.

## Demo Project: Meeting Notes AI Summarizer

This is an AI-powered meeting notes summarizer that uses **OpenAI package v0.27.8** with outdated APIs. Perfect for demonstrating upgrade scenarios!

### Why This Demo Works Well

- **Real deprecated code**: Uses old `openai.Completion.create()` API
- **Security vulnerabilities**: Old `requests` version with known CVEs  
- **Breaking changes**: OpenAI v0.27.8 → v1.x requires complete rewrite
- **Practical use case**: Actually useful meeting summarizer tool

## Demo Workflow

### 1. AI Agent Analyzes the Project
Ask your AI coding agent:
> "Please analyze the dependencies in this meeting summarizer project and check for available upgrades"

The AI will use MCP tools like:
- `analyze_project_dependencies()` to scan requirements.txt
- `get_latest_version()` to check for newer versions
- `get_package_metadata()` to understand current packages

### 2. AI Agent Identifies Critical Issues
The AI will discover:
- **openai 0.27.8 → 1.40.0** (major API rewrite required)
- **requests 2.25.1 → 2.31.0** (security fixes for CVE-2023-32681)
- **click 7.1.2 → 8.1.7** (new features available)

### 3. AI Agent Analyzes Breaking Changes
Ask the AI:
> "What breaking changes will happen if I upgrade OpenAI to v1.x?"

The AI uses:
- `compare_package_versions()` to identify API changes
- `get_migration_resources()` to find upgrade guides
- Code analysis to spot deprecated patterns

### 4. AI Agent Plans the Migration
The AI will identify deprecated code patterns in `meeting_summarizer.py`:
- `openai.api_key = key` → `OpenAI(api_key=key)`
- `openai.Completion.create()` → `client.chat.completions.create()`
- `engine="text-davinci-003"` → `model="gpt-3.5-turbo"`

### 5. AI Agent Assists with Code Updates
Ask the AI:
> "Help me migrate meeting_summarizer.py to use the new OpenAI v1.x API"

The AI can:
- Rewrite the MeetingSummarizer class with modern API
- Update authentication and client initialization
- Convert Completion API calls to ChatCompletion
- Update error handling and response parsing

## Example AI Conversation

```
Human: Please analyze this meeting summarizer project and suggest upgrades

AI: I'll analyze your meeting summarizer dependencies and check for available upgrades.

🚨 CRITICAL SECURITY ISSUE FOUND:
- requests 2.25.1 has known vulnerability CVE-2023-32681
- Upgrade to requests 2.31.0+ immediately

🔄 MAJOR API CHANGES REQUIRED:
- openai 0.27.8 → 1.40.0 (complete API rewrite)

Your meeting_summarizer.py uses deprecated patterns:
- Line 12: openai.api_key = key (deprecated)
- Line 29: openai.Completion.create() (removed in v1.x)
- Line 30: engine="text-davinci-003" (legacy model name)

The new OpenAI v1.x API requires:
- Client-based initialization: OpenAI(api_key=key)
- ChatCompletion instead of Completion
- New model names like "gpt-3.5-turbo"

Would you like me to help migrate your code to the modern OpenAI API?
```

## Try It Yourself

1. **Run the current app**: `python cli_app.py --use-sample`
2. **Ask AI to analyze**: "Check this project for dependency upgrades"
3. **Request migration help**: "Help me upgrade to OpenAI v1.x API"
4. **Test the results**: Verify the upgraded code works correctly

This creates a realistic, hands-on experience showing how AI agents can guide complex dependency upgrades!