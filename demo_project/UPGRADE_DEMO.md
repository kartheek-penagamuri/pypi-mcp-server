# MCP Server + AI Agent Upgrade Demo

This demo project showcases how the **Python Package MCP Server** works with an **AI coding agent** to analyze and upgrade legacy dependencies in a real-world application.

## Demo Project: Meeting Notes AI Summarizer

This is an AI-powered meeting notes summarizer that uses **OpenAI package v0.27.8**. It's perfect for demonstrating upgrade scenarios because it uses older API patterns that have changed in newer versions.

## Why This Demo Works Well

- **Real deprecated code**: Uses older OpenAI API patterns
- **Security vulnerabilities**: Old `requests` version with known CVEs  
- **Breaking changes**: OpenAI v0.27.8 → v2.8.0 requires significant updates
- **Practical use case**: Actually useful meeting summarizer tool
- **Multiple APIs**: Uses various OpenAI endpoints (chat, completion, embeddings, moderation)

## Demo Workflow

### 1. Run the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run with all features
python cli_app.py --use-sample --full-demo
```

### 2. AI Agent Analyzes the Project

Ask your AI coding agent:
> "Please analyze the dependencies in this meeting summarizer project and check for available upgrades"

The AI will use MCP tools like:
- `analyze_project_dependencies()` to scan requirements.txt
- `get_latest_version()` to check for newer versions
- `get_package_metadata()` to understand current packages

### 3. AI Agent Identifies Issues

The AI will discover:
- **openai 0.27.8 → 2.8.0** (major API changes)
- **requests 2.25.1 → 2.31.0** (security fixes for CVE-2023-32681)
- **click 7.1.2 → 8.1.7** (new features available)
- **python-dateutil 2.8.1 → 2.9.0** (minor updates)

### 4. AI Agent Analyzes Breaking Changes

Ask the AI:
> "What are the breaking changes in the latest version of openai compared to the version used in this repository?"

The AI uses:
- `compare_package_versions()` to identify API changes
- Discovers changes in authentication, API calls, response structures, and error handling
- Identifies which code patterns need updating

### 5. AI Agent Plans the Migration

The AI will identify code patterns that need updating:
- Module-level configuration → Client-based initialization
- Old API method names → New API method names
- Parameter changes (e.g., `engine` → `model`)
- Response structure changes
- Error handling updates

### 6. AI Agent Assists with Code Updates

Ask the AI:
> "Help me migrate this code to use the new OpenAI v2.8.0 API"

The AI can:
- Rewrite the MeetingSummarizer class with modern API
- Update authentication and client initialization
- Convert API calls to new patterns
- Update error handling and response parsing
- Provide migration guidance for each change

## Example AI Conversation

```
Human: What are the breaking changes in the latest version of openai compared to the version used in this repository?

AI: I'll analyze the breaking changes between OpenAI v0.27.8 (current) and v2.8.0 (latest).

Found significant breaking changes:

🚨 MAJOR API CHANGES:
- Module-level configuration (openai.api_key) has been replaced with client-based initialization
- ChatCompletion.create() has been replaced with client.chat.completions.create()
- Completion.create() has been replaced (legacy API removed)
- Embedding.create() has been replaced with client.embeddings.create()
- Moderation.create() has been replaced with client.moderations.create()

Additional changes:
- 'engine' parameter renamed to 'model' throughout
- Response objects changed from dict-like to Pydantic models
- Error classes restructured
- Authentication pattern completely changed

Your code will need updates in:
- meeting_summarizer.py (lines 15, 42, 75, 89, 110, 125)
- All API initialization and calls need to be rewritten

Would you like me to help create a migration plan?
```

## Try It Yourself

1. **Run the current app**: `python cli_app.py --use-sample --full-demo`
2. **Ask AI to analyze**: "Check this project for dependency upgrades"
3. **Request breaking changes**: "What are the breaking changes in the latest version of openai?"
4. **Get migration help**: "Help me migrate to OpenAI v2.8.0 API"
5. **Test the results**: Verify the upgraded code works correctly

## What Makes This Demo Compelling

1. **Real-world complexity**: Multiple API patterns that need updating
2. **Security implications**: Old requests library has CVEs
3. **MCP Server value**: AI discovers breaking changes automatically
4. **Practical outcome**: Working meeting summarizer that's relatable
5. **Clear transformation**: Easy to see before/after migration

This creates a realistic, hands-on experience showing how AI agents can guide complex dependency upgrades!
