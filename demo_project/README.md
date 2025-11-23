# Meeting Notes AI Summarizer

An AI-powered tool to automatically summarize meeting notes using the modern OpenAI Python SDK (client-based) with a deterministic offline fallback for demos.

## Features

- Generates concise summaries and meeting titles
- Extracts high-signal action items
- Optional content moderation and embeddings (full demo mode)
- Offline/demo mode for environments without an API key
- Ships with sample notes for quick runs

## Installation

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# or: source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

## Usage

```bash
# Run with sample notes (uses API if key is present)
python cli_app.py --use-sample

# Run full demo (moderation + embeddings)
python cli_app.py --use-sample --full-demo

# Force offline demo (no API calls)
python cli_app.py --use-sample --offline

# Summarize your own meeting notes
python cli_app.py --notes-file my_meeting.txt --meeting-type planning
```

## Example Output (offline demo)

```
Meeting Notes AI Summarizer
==================================================
Using bundled sample standup notes.

Generating meeting title...
Meeting Title: Daily Standup - March 15, 2023

Generating AI summary...
AI SUMMARY
==================================================
Daily Standup - March 15, 2023

Key points:
- Detected meeting type: standup
- Participants and discussion parsed locally.

Action items:
- Bob to follow up with DevOps team for test DB access
- Charlie to schedule meeting with design team

Generated at: 2025-11-15T12:00:00
Model used: local-fallback

Extracting action items...
ACTION ITEMS
==================================================
- Bob to follow up with DevOps team for test DB access
- Charlie to schedule meeting with design team
- Diana to create performance analysis report by Friday
```

## Requirements

- Python 3.10+
- OpenAI API key set as `OPENAI_API_KEY` (optional when using `--offline`)

## Demo Workflow

See [UPGRADE_DEMO.md](UPGRADE_DEMO.md) for how to pair this demo with the MCP server to showcase dependency analysis and upgrade planning.

## License

MIT
