#!/usr/bin/env python3
"""
Meeting Notes AI Summarizer
AI-powered tool to summarize standup meeting notes
"""

import openai
import os
from datetime import datetime
from typing import List, Dict

class MeetingSummarizer:
    def __init__(self, api_key: str = None):
        """Initialize with OpenAI API key"""
        openai.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
    def summarize_meeting_notes(self, meeting_notes: str, meeting_type: str = "standup") -> Dict:
        """
        Summarize meeting notes using OpenAI ChatCompletion API
        """
        try:
            messages = [
                {
                    "role": "system",
                    "content": f"You are an AI assistant that summarizes {meeting_type} meeting notes."
                },
                {
                    "role": "user", 
                    "content": f"""Please summarize the following {meeting_type} meeting notes:

Meeting Notes:
{meeting_notes}

Please provide:
1. Key discussion points
2. Action items with owners
3. Blockers or concerns raised
4. Next steps"""
                }
            ]

            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.3,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            return {
                "summary": response.choices[0].message.content.strip(),
                "timestamp": datetime.now().isoformat(),
                "model_used": "gpt-3.5-turbo",
                "meeting_type": meeting_type
            }
            
        except Exception as e:
            return {
                "error": f"Failed to summarize: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def extract_action_items(self, meeting_notes: str) -> List[str]:
        """Extract action items from meeting notes"""
        messages = [
            {
                "role": "system",
                "content": "You are an AI assistant that extracts action items from meeting notes."
            },
            {
                "role": "user",
                "content": f"""Extract only the top 2 most important action items from these meeting notes. 
Be concise and list each action item on a new line starting with "- ":

{meeting_notes}

Action Items (2 bullet points only):"""
            }
        ]

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=200,
                temperature=0.1
            )
            
            action_items = response.choices[0].message.content.strip().split('\n')
            return [item.strip() for item in action_items if item.strip()]
            
        except Exception as e:
            return [f"Error extracting action items: {str(e)}"]