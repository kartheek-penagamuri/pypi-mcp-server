#!/usr/bin/env python3
"""
CLI Application for Meeting Summarizer
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
@click.option('--full-demo', is_flag=True, help='Run full demo with all features')
def main(api_key, notes_file, use_sample, meeting_type, full_demo):
    """
    AI-powered meeting notes summarizer
    """
    click.echo("🤖 Meeting Notes AI Summarizer")
    click.echo("=" * 50)
    
    summarizer = MeetingSummarizer(api_key)
    
    # Get meeting notes
    if use_sample:
        meeting_notes = SAMPLE_STANDUP_NOTES
        click.echo("\n📝 Using sample standup meeting notes...")
    elif notes_file and os.path.exists(notes_file):
        with open(notes_file, 'r') as f:
            meeting_notes = f.read()
        click.echo(f"\n📁 Loaded notes from: {notes_file}")
    else:
        click.echo("\n📝 Enter your meeting notes (press Ctrl+D when done):")
        meeting_notes = click.get_text_stream('stdin').read()
    
    if not meeting_notes.strip():
        click.echo("❌ No meeting notes provided!")
        return
    
    click.echo("\n🔄 Generating meeting title...")
    title = summarizer.generate_meeting_title(meeting_notes)
    click.echo(f"📌 Meeting Title: {title}")
    
    if full_demo:
        click.echo("\n🔄 Checking content safety...")
        moderation = summarizer.moderate_content(meeting_notes)
        if "error" not in moderation:
            click.echo(f"✅ Content flagged: {moderation['flagged']}")
    
    click.echo("\n🔄 Generating AI summary...")
    result = summarizer.summarize_meeting_notes(meeting_notes, meeting_type)
    
    if "error" in result:
        click.echo(f"❌ Error: {result['error']}")
        return
    
    # Display results
    click.echo("\n📊 AI SUMMARY")
    click.echo("=" * 50)
    click.echo(result["summary"])
    
    click.echo(f"\n⏰ Generated at: {result['timestamp']}")
    click.echo(f"🤖 Model used: {result['model_used']}")
    if "tokens_used" in result:
        click.echo(f"🎫 Tokens used: {result['tokens_used']}")
    
    click.echo("\n🔄 Extracting action items...")
    action_items = summarizer.extract_action_items(meeting_notes)
    
    click.echo("\n📋 ACTION ITEMS")
    click.echo("=" * 50)
    for item in action_items:
        if item:
            click.echo(item)
    
    if full_demo:
        click.echo("\n🔄 Generating text embeddings...")
        embeddings = summarizer.get_embeddings(meeting_notes[:500])
        if embeddings:
            click.echo(f"✅ Generated {len(embeddings)}-dimensional embedding vector")

if __name__ == "__main__":
    main()