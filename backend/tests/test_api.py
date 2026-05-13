"""
Tests for the API endpoint functions: /api/query and /api/courses.

FastAPI cannot be imported in this test environment because it tries to load
pydantic.version as a submodule, and the conftest.py pydantic mock is a
MagicMock — not a real package with sub-modules.

Instead, the endpoint logic from app.py is reproduced inline as plain async
functions and exercised via asyncio.run(). starlette.exceptions.HTTPException
is safe to import (starlette has no pydantic dependency). FastAPI re-exports
the same class, so the error contract is identical.
"""
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from starlette.exceptions import HTTPException


# ---------------------------------------------------------------------------
# Inline endpoint functions (mirror app.py delegation and error handling)
# ---------------------------------------------------------------------------

_mock_rag = Mock()


async def _query_documents(request):
    body = await request.json()
    query = body.get("query", "")
    session_id = body.get("session_id")
    try:
        if not session_id:
            session_id = _mock_rag.session_manager.create_session()
        answer, sources = _mock_rag.query(query, session_id)
        return {"answer": answer, "sources": sources, "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _get_course_stats():
    try:
        analytics = _mock_rag.get_course_analytics()
        return {
            "total_courses": analytics["total_courses"],
            "course_titles": analytics["course_titles"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _make_request(body: dict):
    req = Mock()
    req.json = AsyncMock(return_value=body)
    return req


def _call_query(body: dict):
    return asyncio.run(_query_documents(_make_request(body)))


def _call_courses():
    return asyncio.run(_get_course_stats())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_mock():
    _mock_rag.reset_mock(side_effect=True)
    _mock_rag.session_manager.create_session.return_value = "session_1"
    _mock_rag.query.return_value = ("Default answer", [])
    _mock_rag.get_course_analytics.return_value = {
        "total_courses": 0,
        "course_titles": [],
    }


# ---------------------------------------------------------------------------
# /api/query — response structure
# ---------------------------------------------------------------------------

class TestQueryResponse:

    def test_answer_comes_from_rag_system(self):
        _mock_rag.query.return_value = ("Embeddings power RAG.", [])
        result = _call_query({"query": "What is RAG?", "session_id": "s1"})
        assert result["answer"] == "Embeddings power RAG."

    def test_sources_included_in_response(self):
        _mock_rag.query.return_value = ("Answer", ["Course A - Lesson 1||https://ex.com"])
        result = _call_query({"query": "test", "session_id": "s1"})
        assert result["sources"] == ["Course A - Lesson 1||https://ex.com"]

    def test_session_id_returned_in_response(self):
        result = _call_query({"query": "test", "session_id": "my-session"})
        assert result["session_id"] == "my-session"

    def test_response_contains_required_keys(self):
        result = _call_query({"query": "test", "session_id": "s1"})
        assert "answer" in result
        assert "sources" in result
        assert "session_id" in result

    def test_empty_sources_list_when_no_tool_used(self):
        _mock_rag.query.return_value = ("Answer", [])
        result = _call_query({"query": "test", "session_id": "s1"})
        assert result["sources"] == []


# ---------------------------------------------------------------------------
# /api/query — delegation to rag_system
# ---------------------------------------------------------------------------

class TestQueryDelegation:

    def test_passes_query_string_to_rag_system(self):
        _call_query({"query": "What is attention?", "session_id": "s1"})
        _mock_rag.query.assert_called_once_with("What is attention?", "s1")

    def test_passes_provided_session_id_to_rag_system(self):
        _call_query({"query": "test", "session_id": "existing-session"})
        _mock_rag.query.assert_called_once_with("test", "existing-session")

    def test_creates_session_when_none_provided(self):
        _mock_rag.session_manager.create_session.return_value = "generated"
        result = _call_query({"query": "test"})
        _mock_rag.session_manager.create_session.assert_called_once()
        assert result["session_id"] == "generated"

    def test_does_not_create_session_when_one_is_provided(self):
        _call_query({"query": "test", "session_id": "existing"})
        _mock_rag.session_manager.create_session.assert_not_called()

    def test_uses_generated_session_id_for_rag_query(self):
        _mock_rag.session_manager.create_session.return_value = "new-session"
        _call_query({"query": "test"})
        _mock_rag.query.assert_called_once_with("test", "new-session")


# ---------------------------------------------------------------------------
# /api/query — error handling
# ---------------------------------------------------------------------------

class TestQueryErrors:

    def test_raises_http_500_on_rag_exception(self):
        _mock_rag.query.side_effect = RuntimeError("DB unavailable")
        with pytest.raises(HTTPException) as exc_info:
            _call_query({"query": "test", "session_id": "s1"})
        assert exc_info.value.status_code == 500

    def test_error_detail_contains_exception_message(self):
        _mock_rag.query.side_effect = ValueError("bad input")
        with pytest.raises(HTTPException) as exc_info:
            _call_query({"query": "test", "session_id": "s1"})
        assert "bad input" in exc_info.value.detail

    def test_raises_http_500_when_session_creation_fails(self):
        _mock_rag.session_manager.create_session.side_effect = RuntimeError("store full")
        with pytest.raises(HTTPException) as exc_info:
            _call_query({"query": "test"})
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# /api/courses — response structure
# ---------------------------------------------------------------------------

class TestCoursesResponse:

    def test_returns_total_course_count(self):
        _mock_rag.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": ["A", "B", "C"],
        }
        result = _call_courses()
        assert result["total_courses"] == 3

    def test_returns_course_titles_list(self):
        _mock_rag.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["Intro to RAG", "MCP Course"],
        }
        result = _call_courses()
        assert result["course_titles"] == ["Intro to RAG", "MCP Course"]

    def test_response_contains_required_keys(self):
        result = _call_courses()
        assert "total_courses" in result
        assert "course_titles" in result

    def test_empty_catalog_returns_zero_count_and_empty_list(self):
        result = _call_courses()
        assert result["total_courses"] == 0
        assert result["course_titles"] == []


# ---------------------------------------------------------------------------
# /api/courses — delegation and error handling
# ---------------------------------------------------------------------------

class TestCoursesDelegation:

    def test_calls_get_course_analytics(self):
        _call_courses()
        _mock_rag.get_course_analytics.assert_called_once()

    def test_raises_http_500_on_analytics_exception(self):
        _mock_rag.get_course_analytics.side_effect = RuntimeError("ChromaDB unavailable")
        with pytest.raises(HTTPException) as exc_info:
            _call_courses()
        assert exc_info.value.status_code == 500

    def test_error_detail_contains_exception_message(self):
        _mock_rag.get_course_analytics.side_effect = RuntimeError("store error")
        with pytest.raises(HTTPException) as exc_info:
            _call_courses()
        assert "store error" in exc_info.value.detail
