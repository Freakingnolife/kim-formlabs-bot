"""Tests for kim_llm.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestKimAssistant:
    @patch.dict("sys.modules", {"anthropic": MagicMock()})
    def test_init(self):
        # Re-import to pick up the mocked anthropic
        import importlib
        from mcp_formlabs import kim_llm
        importlib.reload(kim_llm)
        kim_llm.HAS_ANTHROPIC = True

        kim = kim_llm.KimAssistant(api_key="test-key")
        assert kim.model == "claude-sonnet-4-5-20250929"

    @patch.dict("sys.modules", {"anthropic": MagicMock()})
    def test_clear_history(self):
        import importlib
        from mcp_formlabs import kim_llm
        # Ensure module is registered before reload
        sys.modules["mcp_formlabs.kim_llm"] = kim_llm
        importlib.reload(kim_llm)
        kim_llm.HAS_ANTHROPIC = True

        kim = kim_llm.KimAssistant(api_key="test-key")
        kim.conversations[123] = [{"role": "user", "content": "hi"}]
        kim.clear_history(123)
        assert 123 not in kim.conversations

    @patch.dict("sys.modules", {"anthropic": MagicMock()})
    def test_clear_history_nonexistent(self):
        import importlib
        from mcp_formlabs import kim_llm
        sys.modules["mcp_formlabs.kim_llm"] = kim_llm
        importlib.reload(kim_llm)
        kim_llm.HAS_ANTHROPIC = True

        kim = kim_llm.KimAssistant(api_key="test-key")
        kim.clear_history(999)  # Should not raise

    def test_tools_defined(self):
        from mcp_formlabs.kim_llm import TOOLS
        assert len(TOOLS) >= 10
        tool_names = [t["name"] for t in TOOLS]
        assert "list_printers" in tool_names
        assert "get_print_progress" in tool_names
        assert "cancel_print" in tool_names
        assert "estimate_cost" in tool_names

    def test_system_prompt_exists(self):
        from mcp_formlabs.kim_llm import SYSTEM_PROMPT
        assert "Kim" in SYSTEM_PROMPT
        assert "Formlabs" in SYSTEM_PROMPT

    @patch.dict("sys.modules", {"anthropic": MagicMock()})
    @pytest.mark.asyncio
    async def test_chat_text_response(self):
        import importlib
        from mcp_formlabs import kim_llm
        importlib.reload(kim_llm)
        kim_llm.HAS_ANTHROPIC = True

        kim = kim_llm.KimAssistant(api_key="test-key")

        # Mock the response
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Hello! Your printers are all online."

        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [mock_block]

        kim.client.messages.create = MagicMock(return_value=mock_response)

        result = await kim.chat(123, "How are my printers?", AsyncMock())
        assert "printers" in result.lower()
