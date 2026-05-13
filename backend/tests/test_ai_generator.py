"""
Tests for AIGenerator — verifies it correctly triggers and handles CourseSearchTool calls.

The Anthropic client is mocked so no real API calls are made.
"""
import pytest
from unittest.mock import Mock, patch, call
from ai_generator import AIGenerator


# ---------------------------------------------------------------------------
# Helpers to build mock Anthropic response objects
# ---------------------------------------------------------------------------

def text_response(text="Here is your answer."):
    block = Mock()
    block.type = "text"
    block.text = text
    response = Mock()
    response.stop_reason = "end_turn"
    response.content = [block]
    return response


def tool_use_response(tool_name="search_course_content", tool_input=None, tool_id="tu_123"):
    block = Mock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input or {"query": "What is RAG?"}
    block.id = tool_id
    response = Mock()
    response.stop_reason = "tool_use"
    response.content = [block]
    return response


def make_generator(mock_client):
    with patch("ai_generator.anthropic.Anthropic", return_value=mock_client):
        return AIGenerator(api_key="test-key", model="claude-test")


# ---------------------------------------------------------------------------
# Basic response without tools
# ---------------------------------------------------------------------------

class TestDirectResponse:

    def test_returns_text_when_no_tool_use(self):
        client = Mock()
        client.messages.create.return_value = text_response("Direct answer.")
        gen = make_generator(client)

        result = gen.generate_response(query="What is 2+2?")

        assert result == "Direct answer."

    def test_makes_exactly_one_api_call_when_no_tool_use(self):
        client = Mock()
        client.messages.create.return_value = text_response()
        gen = make_generator(client)

        gen.generate_response(query="Hello")

        assert client.messages.create.call_count == 1


# ---------------------------------------------------------------------------
# Tool definition passed to the first API call
# ---------------------------------------------------------------------------

class TestToolRegistration:

    def test_tools_included_in_first_api_call(self):
        client = Mock()
        client.messages.create.return_value = text_response()
        gen = make_generator(client)
        tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]

        gen.generate_response(query="Tell me about RAG", tools=tools)

        params = client.messages.create.call_args[1]
        assert params["tools"] == tools

    def test_tool_choice_auto_set_when_tools_provided(self):
        client = Mock()
        client.messages.create.return_value = text_response()
        gen = make_generator(client)

        gen.generate_response(query="test", tools=[{"name": "search_course_content"}])

        params = client.messages.create.call_args[1]
        assert params["tool_choice"] == {"type": "auto"}

    def test_no_tools_key_when_tools_not_provided(self):
        client = Mock()
        client.messages.create.return_value = text_response()
        gen = make_generator(client)

        gen.generate_response(query="general question")

        params = client.messages.create.call_args[1]
        assert "tools" not in params


# ---------------------------------------------------------------------------
# Tool execution flow (two-call pattern)
# ---------------------------------------------------------------------------

class TestToolExecution:

    def test_tool_manager_execute_called_on_tool_use(self):
        client = Mock()
        client.messages.create.side_effect = [
            tool_use_response(tool_input={"query": "What is RAG?"}),
            text_response("RAG is Retrieval-Augmented Generation."),
        ]
        gen = make_generator(client)
        tool_manager = Mock()
        tool_manager.execute_tool.return_value = "Search results here."

        gen.generate_response(query="What is RAG?", tools=[{}], tool_manager=tool_manager)

        tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="What is RAG?"
        )

    def test_final_answer_comes_from_second_api_call(self):
        client = Mock()
        client.messages.create.side_effect = [
            tool_use_response(),
            text_response("Final synthesized answer."),
        ]
        gen = make_generator(client)
        tool_manager = Mock()
        tool_manager.execute_tool.return_value = "results"

        result = gen.generate_response(query="test", tools=[{}], tool_manager=tool_manager)

        assert result == "Final synthesized answer."

    def test_two_api_calls_made_on_tool_use(self):
        client = Mock()
        client.messages.create.side_effect = [
            tool_use_response(),
            text_response(),
        ]
        gen = make_generator(client)
        tool_manager = Mock()
        tool_manager.execute_tool.return_value = "results"

        gen.generate_response(query="test", tools=[{}], tool_manager=tool_manager)

        assert client.messages.create.call_count == 2

    def test_intermediate_call_includes_tools(self):
        client = Mock()
        client.messages.create.side_effect = [
            tool_use_response(),
            text_response(),
        ]
        gen = make_generator(client)
        tool_manager = Mock()
        tool_manager.execute_tool.return_value = "results"

        gen.generate_response(query="test", tools=[{"name": "search_course_content"}], tool_manager=tool_manager)

        intermediate_call_params = client.messages.create.call_args_list[1][1]
        assert "tools" in intermediate_call_params

    def test_tool_result_included_in_second_call_messages(self):
        client = Mock()
        client.messages.create.side_effect = [
            tool_use_response(tool_id="tu_abc"),
            text_response(),
        ]
        gen = make_generator(client)
        tool_manager = Mock()
        tool_manager.execute_tool.return_value = "Tool output content"

        gen.generate_response(query="test", tools=[{}], tool_manager=tool_manager)

        second_call_messages = client.messages.create.call_args_list[1][1]["messages"]
        tool_result_messages = [
            m for m in second_call_messages
            if isinstance(m.get("content"), list)
            and any(
                isinstance(item, dict) and item.get("type") == "tool_result"
                for item in m["content"]
            )
        ]
        assert len(tool_result_messages) == 1
        payload = tool_result_messages[0]["content"][0]
        assert payload["type"] == "tool_result"
        assert payload["tool_use_id"] == "tu_abc"
        assert payload["content"] == "Tool output content"


# ---------------------------------------------------------------------------
# System prompt and conversation history
# ---------------------------------------------------------------------------

class TestSystemPrompt:

    def test_conversation_history_appended_to_system(self):
        client = Mock()
        client.messages.create.return_value = text_response()
        gen = make_generator(client)

        gen.generate_response(
            query="Follow-up",
            conversation_history="User: Hi\nAssistant: Hello",
        )

        params = client.messages.create.call_args[1]
        assert "Previous conversation:" in params["system"]
        assert "User: Hi" in params["system"]

    def test_no_history_uses_base_system_prompt_only(self):
        client = Mock()
        client.messages.create.return_value = text_response()
        gen = make_generator(client)

        gen.generate_response(query="What is RAG?")

        params = client.messages.create.call_args[1]
        assert "Previous conversation:" not in params["system"]

    def test_system_prompt_contains_search_instructions(self):
        client = Mock()
        client.messages.create.return_value = text_response()
        gen = make_generator(client)

        gen.generate_response(query="test")

        params = client.messages.create.call_args[1]
        assert "search" in params["system"].lower()


# ---------------------------------------------------------------------------
# Sequential tool calling (up to 2 rounds)
# ---------------------------------------------------------------------------

class TestSequentialToolCalling:

    def test_two_tool_rounds_makes_three_api_calls(self):
        client = Mock()
        client.messages.create.side_effect = [
            tool_use_response(tool_id="tu_1"),
            tool_use_response(tool_id="tu_2"),
            text_response("Final answer."),
        ]
        gen = make_generator(client)
        tool_manager = Mock()
        tool_manager.execute_tool.return_value = "results"

        result = gen.generate_response(query="test", tools=[{}], tool_manager=tool_manager)

        assert client.messages.create.call_count == 3
        assert result == "Final answer."

    def test_two_tool_rounds_executes_both_tools(self):
        client = Mock()
        client.messages.create.side_effect = [
            tool_use_response(tool_id="tu_1", tool_input={"query": "first search"}),
            tool_use_response(tool_id="tu_2", tool_input={"query": "second search"}),
            text_response(),
        ]
        gen = make_generator(client)
        tool_manager = Mock()
        tool_manager.execute_tool.return_value = "results"

        gen.generate_response(query="test", tools=[{}], tool_manager=tool_manager)

        assert tool_manager.execute_tool.call_count == 2

    def test_synthesis_call_excludes_tools(self):
        client = Mock()
        client.messages.create.side_effect = [
            tool_use_response(tool_id="tu_1"),
            tool_use_response(tool_id="tu_2"),
            text_response(),
        ]
        gen = make_generator(client)
        tool_manager = Mock()
        tool_manager.execute_tool.return_value = "results"

        gen.generate_response(query="test", tools=[{"name": "search_course_content"}], tool_manager=tool_manager)

        synthesis_call_params = client.messages.create.call_args_list[2][1]
        assert "tools" not in synthesis_call_params

    def test_synthesis_call_sees_both_tool_results(self):
        client = Mock()
        client.messages.create.side_effect = [
            tool_use_response(tool_id="tu_1"),
            tool_use_response(tool_id="tu_2"),
            text_response(),
        ]
        gen = make_generator(client)
        tool_manager = Mock()
        tool_manager.execute_tool.return_value = "search result"

        gen.generate_response(query="test", tools=[{}], tool_manager=tool_manager)

        synthesis_messages = client.messages.create.call_args_list[2][1]["messages"]
        tool_result_ids = [
            item["tool_use_id"]
            for m in synthesis_messages
            if isinstance(m.get("content"), list)
            for item in m["content"]
            if isinstance(item, dict) and item.get("type") == "tool_result"
        ]
        assert "tu_1" in tool_result_ids
        assert "tu_2" in tool_result_ids

    def test_tool_error_does_not_raise(self):
        client = Mock()
        client.messages.create.side_effect = [
            tool_use_response(),
            text_response("Handled gracefully."),
        ]
        gen = make_generator(client)
        tool_manager = Mock()
        tool_manager.execute_tool.side_effect = RuntimeError("db unavailable")

        result = gen.generate_response(query="test", tools=[{}], tool_manager=tool_manager)

        assert result == "Handled gracefully."

    def test_tool_error_sends_error_string_as_tool_result(self):
        client = Mock()
        client.messages.create.side_effect = [
            tool_use_response(tool_id="tu_err"),
            text_response(),
        ]
        gen = make_generator(client)
        tool_manager = Mock()
        tool_manager.execute_tool.side_effect = RuntimeError("db unavailable")

        gen.generate_response(query="test", tools=[{}], tool_manager=tool_manager)

        second_call_messages = client.messages.create.call_args_list[1][1]["messages"]
        tool_results = [
            item
            for m in second_call_messages
            if isinstance(m.get("content"), list)
            for item in m["content"]
            if isinstance(item, dict) and item.get("type") == "tool_result"
        ]
        assert len(tool_results) == 1
        assert tool_results[0]["tool_use_id"] == "tu_err"
        assert "Tool execution error:" in tool_results[0]["content"]

    def test_max_two_rounds_enforced(self):
        client = Mock()
        # Provide more tool_use responses than the limit allows
        client.messages.create.side_effect = [
            tool_use_response(tool_id="tu_1"),
            tool_use_response(tool_id="tu_2"),
            tool_use_response(tool_id="tu_3"),
            tool_use_response(tool_id="tu_4"),
            text_response(),
        ]
        gen = make_generator(client)
        tool_manager = Mock()
        tool_manager.execute_tool.return_value = "results"

        gen.generate_response(query="test", tools=[{}], tool_manager=tool_manager)

        assert client.messages.create.call_count == 3
