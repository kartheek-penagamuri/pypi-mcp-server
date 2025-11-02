#!/usr/bin/env python3
"""
CLI Application for Meeting Summarizer
Demonstrates usage of legacy OpenAI package
"""

import click
import os
from meeting_summarizer import MeetingSummarizer
from datetime import datetime

# Sample meeting notes for demo
SAMPLE_STANDUP_NOTES = """
Daily Standup - March 15, 2023

Team Members Present: Alice, Bob, Charlie, Diana

Alice:
- Completed user authentication module
- Working on password reset functionality today
- No blockers

Bob:
- Finished database migration scripts
- Starting on API endpoint testing
- Blocked on getting test database credentials from DevOps

Charlie:
- Reviewed pull requests from last sprint
- Will work on frontend component library updates
- Need clarification on new design system requirements

Diana:
- Deployed hotfix for login issue to production
- Investigating performance issues in search functionality
- No immediate blockers but may need help with optimization

Action Items:
- Bob to follow up with DevOps team for test DB access
- Charlie to schedule meeting with design team
- Diana to create performance analysis report by Friday
"""

@click.command()
@click.option('--api-key', help='OpenAI API key (or set OPENAI_API_KEY env var)')
@click.option('--notes-file', help='Path to meeting notes file')
@click.option('--use-sample', is_flag=True, help='Use sample meeting notes for demo')
@click.option('--meeting-type', default='standup', help='Type of meeting (standup, planning, etc.)')
def main(api_key, notes_file, use_sample, meeting_type):
    """
    AI-powered meeting notes summarizer using legacy OpenAI API
    """
    click.echo("🤖 Meeting Notes AI Summarizer")
    click.echo("=" * 40)
    
    # Initialize summarizer with legacy API
    summarizer = MeetingSummarizer(api_key)
    
    # Get meeting notes
    if use_sample:
        meeting_notes = SAMPLE_STANDUP_NOTES
        click.echo("📝 Using sample standup meeting notes...")
    elif notes_file and os.path.exists(notes_file):
        with open(notes_file, 'r') as f:
            meeting_notes = f.read()
        click.echo(f"📁 Loaded notes from: {notes_file}")
    else:
        click.echo("📝 Enter your meeting notes (press Ctrl+D when done):")
        meeting_notes = click.get_text_stream('stdin').read()
    
    if not meeting_notes.strip():
        click.echo("❌ No meeting notes provided!")
        return
    
    click.echo("\n🔄 Generating AI summary...")
    
    # Generate summary using legacy OpenAI API
    result = summarizer.summarize_meeting_notes(meeting_notes, meeting_type)
    
    if "error" in result:
        click.echo(f"❌ Error: {result['error']}")
        return
    
    # Display results
    click.echo("\n📊 AI SUMMARY")
    click.echo("=" * 40)
    click.echo(result["summary"])
    
    click.echo(f"\n⏰ Generated at: {result['timestamp']}")
    click.echo(f"🤖 Model used: {result['model_used']}")
    
    # Extract action items separately
    click.echo("\n🎯 Extracting action items...")
    action_items = summarizer.extract_action_items(meeting_notes)
    
    click.echo("\n📋 ACTION ITEMS")
    click.echo("=" * 40)
    for item in action_items:
        if item:
            click.echo(item)

if __name__ == "__main__":
    main()