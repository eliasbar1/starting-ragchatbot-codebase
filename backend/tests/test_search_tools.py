"""
Tests for CourseSearchTool.execute() in search_tools.py.

All tests use a mocked VectorStore — no real ChromaDB is created.
"""
import pytest
from unittest.mock import Mock
from search_tools import CourseSearchTool
from vector_store import SearchResults


def make_tool(store=None):
    store = store or Mock()
    return CourseSearchTool(store), store


def make_results(docs, metas, distances=None):
    distances = distances or [0.1] * len(docs)
    return SearchResults(documents=docs, metadata=metas, distances=distances)


# ---------------------------------------------------------------------------
# Successful search — formatting and source tracking
# ---------------------------------------------------------------------------

class TestExecuteFormattedOutput:

    def test_returns_course_and_lesson_header(self):
        tool, store = make_tool()
        store.search.return_value = make_results(
            ["RAG stands for Retrieval-Augmented Generation."],
            [{"course_title": "Intro to RAG", "lesson_number": 1}],
        )
        store.get_lesson_link.return_value = None

        result = tool.execute(query="What is RAG?")

        assert "[Intro to RAG - Lesson 1]" in result
        assert "RAG stands for Retrieval-Augmented Generation." in result

    def test_returns_course_header_when_no_lesson_number(self):
        tool, store = make_tool()
        store.search.return_value = make_results(
            ["Some content."],
            [{"course_title": "MCP Course"}],
        )

        result = tool.execute(query="test")

        assert "[MCP Course]" in result
        assert "- Lesson" not in result

    def test_multiple_results_are_separated(self):
        tool, store = make_tool()
        store.search.return_value = make_results(
            ["Doc A.", "Doc B."],
            [
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
            ],
        )
        store.get_lesson_link.return_value = None

        result = tool.execute(query="test")

        assert "Doc A." in result
        assert "Doc B." in result


# ---------------------------------------------------------------------------
# Source tracking
# ---------------------------------------------------------------------------

class TestSourceTracking:

    def test_last_sources_contains_lesson_link_when_available(self):
        tool, store = make_tool()
        store.search.return_value = make_results(
            ["content"],
            [{"course_title": "MCP Course", "lesson_number": 3}],
        )
        store.get_lesson_link.return_value = "https://example.com/lesson3"

        tool.execute(query="test")

        assert len(tool.last_sources) == 1
        assert "MCP Course - Lesson 3" in tool.last_sources[0]
        assert "https://example.com/lesson3" in tool.last_sources[0]

    def test_last_sources_no_link_suffix_when_no_lesson_link(self):
        tool, store = make_tool()
        store.search.return_value = make_results(
            ["content"],
            [{"course_title": "MCP Course", "lesson_number": 3}],
        )
        store.get_lesson_link.return_value = None

        tool.execute(query="test")

        assert tool.last_sources[0] == "MCP Course - Lesson 3"

    def test_last_sources_course_only_when_no_lesson(self):
        tool, store = make_tool()
        store.search.return_value = make_results(
            ["content"],
            [{"course_title": "MCP Course"}],
        )

        tool.execute(query="test")

        assert tool.last_sources[0] == "MCP Course"

    def test_multiple_results_produce_multiple_sources(self):
        tool, store = make_tool()
        store.search.return_value = make_results(
            ["doc1", "doc2"],
            [
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
            ],
        )
        store.get_lesson_link.return_value = None

        tool.execute(query="test")

        assert len(tool.last_sources) == 2


# ---------------------------------------------------------------------------
# Empty and error results
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_results_returns_no_content_message(self):
        tool, store = make_tool()
        store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])

        result = tool.execute(query="unknown topic")

        assert "No relevant content found" in result

    def test_empty_results_with_course_filter_mentions_course(self):
        tool, store = make_tool()
        store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])

        result = tool.execute(query="something", course_name="RAG Course")

        assert "RAG Course" in result

    def test_empty_results_with_lesson_filter_mentions_lesson(self):
        tool, store = make_tool()
        store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])

        result = tool.execute(query="something", lesson_number=5)

        assert "5" in result

    def test_error_in_results_returns_error_message(self):
        tool, store = make_tool()
        store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[], error="ChromaDB connection failed"
        )

        result = tool.execute(query="test")

        assert "ChromaDB connection failed" in result


# ---------------------------------------------------------------------------
# Parameters forwarded to the vector store
# ---------------------------------------------------------------------------

class TestStoreCallParameters:

    def test_passes_query_to_store(self):
        tool, store = make_tool()
        store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])

        tool.execute(query="What is embeddings?")

        store.search.assert_called_once_with(
            query="What is embeddings?", course_name=None, lesson_number=None
        )

    def test_passes_course_name_to_store(self):
        tool, store = make_tool()
        store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])

        tool.execute(query="test", course_name="Intro to RAG")

        store.search.assert_called_once_with(
            query="test", course_name="Intro to RAG", lesson_number=None
        )

    def test_passes_lesson_number_to_store(self):
        tool, store = make_tool()
        store.search.return_value = SearchResults(documents=[], metadata=[], distances=[])

        tool.execute(query="test", lesson_number=2)

        store.search.assert_called_once_with(
            query="test", course_name=None, lesson_number=2
        )
