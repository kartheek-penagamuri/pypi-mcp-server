#!/usr/bin/env python3
"""CLI Application for Meeting Summarizer."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from meeting_summarizer import MeetingSummarizer


SAMPLE_PATH = Path(__file__).parent / "sample_meeting_notes.txt"


def _load_meeting_notes(notes_file: Optional[str], use_sample: bool) -> str:
    """Choose the source of meeting notes."""
    if use_sample:
        click.echo("Using bundled sample standup notes.")
        return SAMPLE_PATH.read_text(encoding="utf-8")
    if notes_file:
        path = Path(notes_file)
        if not path.exists():
            raise click.ClickException(f"Notes file not found: {notes_file}")
        click.echo(f"Loaded notes from: {notes_file}")
        return path.read_text(encoding="utf-8")
    click.echo("Enter your meeting notes (press Ctrl+D when done):")
    return click.get_text_stream("stdin").read()


@click.command()
@click.option("--api-key", help="OpenAI API key (or set OPENAI_API_KEY env var).")
@click.option("--notes-file", help="Path to meeting notes file.")
@click.option("--use-sample", is_flag=True, help="Use the bundled sample meeting notes.")
@click.option("--meeting-type", default="standup", show_default=True, help="Type of meeting (standup, planning, etc.).")
@click.option("--full-demo", is_flag=True, help="Run moderation and embeddings in addition to the summary.")
@click.option("--offline", is_flag=True, help="Force offline mode with deterministic local outputs.")
@click.option("--model", default="gpt-4o-mini", show_default=True, help="Chat model to use for summaries.")
def main(api_key, notes_file, use_sample, meeting_type, full_demo, offline, model):
    """AI-powered meeting notes summarizer."""
    click.secho("Meeting Notes AI Summarizer", fg="cyan", bold=True)
    click.echo("=" * 50)

    summarizer = MeetingSummarizer(api_key=api_key, offline=offline, default_model=model)
    if summarizer.offline:
        click.secho("Offline mode enabled (no API calls will be made).", fg="yellow")

    meeting_notes = _load_meeting_notes(notes_file, use_sample)
    if not meeting_notes.strip():
        raise click.ClickException("No meeting notes provided.")

    click.echo("\nGenerating meeting title...")
    title = summarizer.generate_meeting_title(meeting_notes)
    click.secho(f"Meeting Title: {title}", fg="green")

    if full_demo:
        click.echo("\nChecking content safety...")
        moderation = summarizer.moderate_content(meeting_notes)
        if "error" in moderation:
            click.secho(f"Moderation error: {moderation['error']}", fg="yellow")
        else:
            click.echo(f"Content flagged: {moderation['flagged']}")

    click.echo("\nGenerating AI summary...")
    result = summarizer.summarize_meeting_notes(meeting_notes, meeting_type)
    if "error" in result:
        raise click.ClickException(result["error"])

    click.echo("\nAI SUMMARY")
    click.echo("=" * 50)
    click.echo(result["summary"])
    click.echo(f"\nGenerated at: {result['timestamp']}")
    click.echo(f"Model used: {result['model_used']}")
    if result.get("tokens_used") is not None:
        click.echo(f"Tokens used: {result['tokens_used']}")

    click.echo("\nExtracting action items...")
    action_items = summarizer.extract_action_items(meeting_notes)
    click.echo("\nACTION ITEMS")
    click.echo("=" * 50)
    for item in action_items:
        if item:
            click.echo(f"- {item}")

    if full_demo:
        click.echo("\nGenerating text embeddings...")
        embeddings = summarizer.get_embeddings(meeting_notes[:500])
        if embeddings:
            click.echo(f"Generated {len(embeddings)}-dimensional embedding vector")
        else:
            click.echo("Embeddings were not generated (offline mode or API error).")


if __name__ == "__main__":
    main()
