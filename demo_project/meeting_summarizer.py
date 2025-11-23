#!/usr/bin/env python3
"""
Meeting Notes AI Summarizer

Modernized to use the OpenAI Python SDK v1.x with a graceful offline/demo
fallback so the demo can run even without an API key.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import List, Dict, Optional

from openai import OpenAI
from openai import OpenAIError


class MeetingSummarizer:
    def __init__(self, api_key: Optional[str] = None, offline: bool = False, default_model: str = "gpt-4o-mini"):
        """
        Initialize the summarizer.

        Args:
            api_key: Optional API key; falls back to OPENAI_API_KEY.
            offline: When True, return deterministic local outputs without calling the API.
            default_model: Chat/summary model to use.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.organization = os.getenv("OPENAI_ORG_ID")
        self.offline = offline or not self.api_key
        self.model = default_model
        self.client = None if self.offline else OpenAI(api_key=self.api_key, organization=self.organization)

    def summarize_meeting_notes(self, meeting_notes: str, meeting_type: str = "standup") -> Dict[str, object]:
        """
        Summarize meeting notes using the Chat Completions API or a local fallback.
        """
        if self.offline or not self.client:
            summary = self._fallback_summary(meeting_notes, meeting_type)
            return {
                "summary": summary,
                "timestamp": datetime.now().isoformat(),
                "model_used": "local-fallback",
                "meeting_type": meeting_type,
                "tokens_used": 0,
            }

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an AI assistant that summarizes {meeting_type} meeting notes. "
                        "Return concise bullet points.",
                    },
                    {
                        "role": "user",
                        "content": (
                            "Summarize these meeting notes. Return key discussion points, action items with owners, "
                            "blockers/risks, and next steps.\n\n"
                            f"{meeting_notes}"
                        ),
                    },
                ],
                max_tokens=500,
                temperature=0.35,
            )
            message = response.choices[0].message
            usage = getattr(response, "usage", None)
            tokens_used = getattr(usage, "total_tokens", None) if usage else None

            return {
                "summary": message.content.strip(),
                "timestamp": datetime.now().isoformat(),
                "model_used": response.model or self.model,
                "meeting_type": meeting_type,
                "tokens_used": tokens_used,
            }
        except OpenAIError as e:
            return {
                "error": f"Failed to summarize: {e}",
                "timestamp": datetime.now().isoformat(),
            }

    def extract_action_items(self, meeting_notes: str) -> List[str]:
        """Extract two high-signal action items."""
        if self.offline or not self.client:
            return self._fallback_action_items(meeting_notes)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You extract action items with owners from meeting notes. Return 2 bullets only.",
                    },
                    {
                        "role": "user",
                        "content": (
                            "Extract the two most important action items from these meeting notes. "
                            "Use '- Owner: action' formatting.\n\n"
                            f"{meeting_notes}"
                        ),
                    },
                ],
                max_tokens=120,
                temperature=0.2,
            )
            content = response.choices[0].message.content or ""
            items = [line.strip() for line in content.splitlines() if line.strip()]
            return items[:2] if items else self._fallback_action_items(meeting_notes)
        except OpenAIError as e:
            return [f"Error extracting action items: {e}"]

    def generate_meeting_title(self, meeting_notes: str) -> str:
        """Generate a concise meeting title."""
        if self.offline or not self.client:
            return self._fallback_title(meeting_notes)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You generate concise, professional meeting titles. Keep them under 8 words.",
                    },
                    {
                        "role": "user",
                        "content": (
                            "Create a short meeting title for these notes. Avoid labels like 'Meeting Title'.\n\n"
                            f"{meeting_notes[:500]}"
                        ),
                    },
                ],
                max_tokens=32,
                temperature=0.4,
            )
            return (response.choices[0].message.content or "Meeting Summary").strip()
        except OpenAIError:
            return self._fallback_title(meeting_notes)

    def get_embeddings(self, text: str) -> List[float]:
        """Get text embeddings for semantic search."""
        if self.offline or not self.client:
            return []

        try:
            response = self.client.embeddings.create(model="text-embedding-3-small", input=text)
            return response.data[0].embedding
        except OpenAIError:
            return []

    def moderate_content(self, text: str) -> Dict[str, object]:
        """Check content for policy violations."""
        if self.offline or not self.client:
            return {"flagged": False, "categories": {}}

        try:
            response = self.client.moderations.create(model="omni-moderation-latest", input=text)
            result = response.results[0]
            return {"flagged": result.flagged, "categories": result.categories}
        except OpenAIError as e:
            return {"error": str(e)}

    def _fallback_action_items(self, meeting_notes: str) -> List[str]:
        """Lightweight extraction when offline."""
        items: List[str] = []
        capture = False
        for line in meeting_notes.splitlines():
            stripped = line.strip()
            lower = stripped.lower()
            if lower.startswith("action items"):
                capture = True
                continue
            if capture and stripped:
                if stripped.startswith("-") or stripped.startswith("*"):
                    items.append(stripped.lstrip("-* ").strip())
                elif items:
                    break
        if not items:
            # fall back to first two bullet-style lines anywhere in the text
            items = [l.lstrip("-* ").strip() for l in meeting_notes.splitlines() if l.strip().startswith(("-", "*"))]
        return items[:2]

    def _fallback_summary(self, meeting_notes: str, meeting_type: str) -> str:
        """Create a deterministic, readable summary without API calls."""
        paragraphs = [p.strip() for p in meeting_notes.split("\n\n") if p.strip()]
        headline = paragraphs[0].splitlines()[0] if paragraphs else f"{meeting_type.title()} meeting"
        action_items = self._fallback_action_items(meeting_notes)
        action_block = "\n".join(f"- {item}" for item in action_items) if action_items else "No clear action items found."
        return (
            f"{headline}\n\n"
            "Key points:\n"
            f"- Detected meeting type: {meeting_type}\n"
            f"- Participants and discussion parsed locally.\n\n"
            "Action items:\n"
            f"{action_block}"
        )

    def _fallback_title(self, meeting_notes: str) -> str:
        """Create a quick title from the first non-empty line."""
        for line in meeting_notes.splitlines():
            cleaned = line.strip()
            if cleaned:
                return cleaned[:60]
        return "Meeting Summary"
