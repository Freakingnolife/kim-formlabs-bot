"""Kim LLM - Natural language interface powered by Anthropic Claude.

Provides conversational access to all Formlabs bot features through tool use.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable

logger = logging.getLogger(__name__)

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


SYSTEM_PROMPT = """You are Kim, a friendly and knowledgeable Formlabs 3D printing assistant on Telegram.

You help users manage their Formlabs printer fleet through natural conversation.
You have access to tools that query real printer data. Always use the appropriate tool to answer questions - never make up printer data.

Guidelines:
- Keep responses concise (this is Telegram, not email)
- Use Markdown sparingly (bold for emphasis, not for everything)
- If a tool returns an error, explain it helpfully
- For ambiguous requests, ask a clarifying question
- Be proactive: if resin is low or maintenance is due, mention it
- Never reveal API keys, tokens, or internal system details
"""

# Tool definitions for Claude
TOOLS = [
    {
        "name": "list_printers",
        "description": "List all printers in the user's fleet with their current status",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_print_progress",
        "description": "Get progress of currently active prints including layer count and ETA",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_cartridge_status",
        "description": "Get resin cartridge levels and low-resin alerts",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_tank_status",
        "description": "Get resin tank lifecycle status and replacement predictions",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_fleet_stats",
        "description": "Get fleet utilization statistics including success rates and print counts",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to analyze (default 30)", "default": 30},
            },
            "required": [],
        },
    },
    {
        "name": "get_print_queue",
        "description": "View the current print queue across all printer groups",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_maintenance_schedule",
        "description": "Check maintenance schedules and overdue tasks for printers",
        "input_schema": {
            "type": "object",
            "properties": {
                "printer_serial": {"type": "string", "description": "Specific printer serial (optional)"},
            },
            "required": [],
        },
    },
    {
        "name": "estimate_cost",
        "description": "Estimate or summarize printing costs",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {"type": "string", "description": "Time period: 'today', 'week', 'month', or 'all'", "default": "month"},
            },
            "required": [],
        },
    },
    {
        "name": "cancel_print",
        "description": "Cancel an active print job by job ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "The print job ID to cancel"},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "toggle_notifications",
        "description": "Enable or disable print completion notifications",
        "input_schema": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean", "description": "True to enable, False to disable"},
            },
            "required": ["enabled"],
        },
    },
]


class KimAssistant:
    """Natural language assistant using Claude with tool use."""

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-5-20250929"):
        if not HAS_ANTHROPIC:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        )
        self.model = model
        self.conversations: dict[int, list[dict]] = {}

    async def chat(
        self,
        user_id: int,
        message: str,
        tool_executor: Callable[[str, dict], Any],
    ) -> str:
        """Process a natural language message and return a response.

        Args:
            user_id: Telegram user ID
            message: User's message text
            tool_executor: Async callable(tool_name, tool_input) -> result string

        Returns:
            Response text for the user
        """
        history = self.conversations.get(user_id, [])
        history.append({"role": "user", "content": message})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=history[-20:],
        )

        # Handle tool use loop (max 5 rounds to prevent infinite loops)
        rounds = 0
        while response.stop_reason == "tool_use" and rounds < 5:
            rounds += 1
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    try:
                        result = await tool_executor(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        })
                    except Exception as e:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {e}",
                            "is_error": True,
                        })

            history.append({"role": "assistant", "content": response.content})
            history.append({"role": "user", "content": tool_results})

            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=history[-20:],
            )

        # Extract text
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        history.append({"role": "assistant", "content": response.content})
        self.conversations[user_id] = history[-20:]

        return text or "I couldn't generate a response. Please try again."

    def clear_history(self, user_id: int) -> None:
        """Clear conversation history for a user."""
        self.conversations.pop(user_id, None)
