"""
Tests for RAGSystem.query() — verifies end-to-end content query handling.

All external dependencies (VectorStore, AIGenerator, SessionManager) are mocked.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


def make_config():
    cfg = Mock()
    cfg.ANTHROPIC_API_KEY = "test-key"
    cfg.ANTHROPIC_MODEL = "claude-test"
    cfg.CHUNK_SIZE = 800
    cfg.CHUNK_OVERLAP = 100
    cfg.CHROMA_PATH = "/tmp/test-chroma"
    cfg.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    cfg.MAX_RESULTS = 5
    cfg.MAX_HISTORY = 2
    return cfg


@pytest.fixture
def rag():
    """RAGSystem with all constructor dependencies mocked."""
    with patch("rag_system.VectorStore"), \
         patch("rag_system.AIGenerator"), \
         patch("rag_system.DocumentProcessor"), \
         patch("rag_system.SessionManager"), \
         patch("rag_system.ToolManager"), \
         patch("rag_system.CourseSearchTool"):
        from rag_system import RAGSystem
        system = RAGSystem(make_config())
        # Provide sensible defaults so tests only override what they care about
        system.ai_generator.generate_response.return_value = "AI answer"
        system.tool_manager.get_tool_definitions.return_value = []
        system.tool_manager.get_last_sources.return_value = []
        system.session_manager.get_conversation_history.return_value = None
        yield system


# ---------------------------------------------------------------------------
# Core query flow — AI generator must be used
# ---------------------------------------------------------------------------

class TestQueryUsesAIGenerator:

    def test_query_calls_ai_generator_generate_response(self, rag):
        rag.query("What is RAG?", session_id="s1")
        rag.ai_generator.generate_response.assert_called_once()

    def test_query_returns_answer_from_ai_generator(self, rag):
        rag.ai_generator.generate_response.return_value = "The answer is embeddings."
        answer, _ = rag.query("What is RAG?", session_id="s1")
        assert answer == "The answer is embeddings."

    def test_query_does_not_return_stub_string(self, rag):
        rag.ai_generator.generate_response.return_value = "Real AI answer."
        answer, _ = rag.query("What is RAG?", session_id="s1")
        assert answer != "Otters are the cutest!"


# ---------------------------------------------------------------------------
# Tools must be passed to the AI generator
# ---------------------------------------------------------------------------

class TestQueryPassesTools:

    def test_tools_passed_to_ai_generator(self, rag):
        tool_defs = [{"name": "search_course_content"}]
        rag.tool_manager.get_tool_definitions.return_value = tool_defs

        rag.query("Tell me about RAG", session_id="s1")

        kwargs = rag.ai_generator.generate_response.call_args[1]
        assert kwargs.get("tools") == tool_defs

    def test_tool_manager_passed_to_ai_generator(self, rag):
        rag.query("Tell me about RAG", session_id="s1")
        kwargs = rag.ai_generator.generate_response.call_args[1]
        assert kwargs.get("tool_manager") is rag.tool_manager


# ---------------------------------------------------------------------------
# Conversation history
# ---------------------------------------------------------------------------

class TestQueryConversationHistory:

    def test_fetches_conversation_history_for_session(self, rag):
        rag.query("Follow-up question", session_id="s1")
        rag.session_manager.get_conversation_history.assert_called_once_with("s1")

    def test_passes_history_to_ai_generator(self, rag):
        rag.session_manager.get_conversation_history.return_value = "User: Hi\nAssistant: Hello"

        rag.query("Follow-up", session_id="s1")

        kwargs = rag.ai_generator.generate_response.call_args[1]
        assert kwargs.get("conversation_history") == "User: Hi\nAssistant: Hello"

    def test_stores_exchange_in_session_after_response(self, rag):
        rag.ai_generator.generate_response.return_value = "AI answer"

        rag.query("What is RAG?", session_id="s1")

        rag.session_manager.add_exchange.assert_called_once_with(
            "s1", "What is RAG?", "AI answer"
        )


# ---------------------------------------------------------------------------
# Sources returned from tool manager
# ---------------------------------------------------------------------------

class TestQuerySources:

    def test_returns_sources_from_tool_manager(self, rag):
        rag.tool_manager.get_last_sources.return_value = ["Course A - Lesson 1||http://example.com"]

        _, sources = rag.query("What is RAG?", session_id="s1")

        assert sources == ["Course A - Lesson 1||http://example.com"]

    def test_resets_sources_before_generating_response(self, rag):
        rag.query("What is RAG?", session_id="s1")
        rag.tool_manager.reset_sources.assert_called()

    def test_returns_empty_sources_when_no_tool_used(self, rag):
        rag.tool_manager.get_last_sources.return_value = []

        _, sources = rag.query("What is 2+2?", session_id="s1")

        assert sources == []
