# Meeting Notes AI Summarizer

An AI-powered tool to automatically summarize meeting notes using OpenAI.

## Features

- Summarize standup meetings, planning sessions, and other meeting types
- Generate meeting titles automatically
- Extract key action items
- Check content safety
- Generate text embeddings for semantic search
- Simple CLI interface with sample data

## Installation

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows CMD:
venv\Scripts\activate.bat
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Run with sample notes
python cli_app.py --use-sample

# Run full demo with all features
python cli_app.py --use-sample --full-demo

# Summarize your own meeting notes
python cli_app.py --notes-file my_meeting.txt

# Specify meeting type
python cli_app.py --use-sample --meeting-type planning
```

## Example Output

```
🤖 Meeting Notes AI Summarizer
==================================================

📝 Using sample standup meeting notes...

🔄 Generating meeting title...
📌 Meeting Title: Daily Standup - Team Progress Update

🔄 Generating AI summary...

📊 AI SUMMARY
==================================================
Key Discussion Points:
- Alice completed user authentication module
- Bob finished database migration scripts
- Charlie reviewed pull requests
- Diana deployed hotfix and investigating performance issues

Action Items:
- Bob to follow up with DevOps for test database credentials
- Charlie to schedule meeting with design team
- Diana to create performance analysis report by Friday

Blockers:
- Bob blocked on test database access
- Charlie needs clarification on design system requirements

⏰ Generated at: 2023-03-15T10:30:00
🤖 Model used: gpt-3.5-turbo
🎫 Tokens used: 487

🔄 Extracting action items...

📋 ACTION ITEMS
==================================================
- Bob to follow up with DevOps team for test DB access
- Charlie to schedule meeting with design team
```

## Requirements

- Python 3.7+
- OpenAI API key (set as `OPENAI_API_KEY` environment variable)

## Demo Workflow

See [UPGRADE_DEMO.md](UPGRADE_DEMO.md) for information about using this project to demonstrate dependency analysis and upgrade planning with AI agents.

## License

MIT
