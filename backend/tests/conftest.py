import sys
import os
import pytest
from unittest.mock import MagicMock, Mock

# Add the backend directory to sys.path so tests can import backend modules directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Pre-mock heavy modules so they don't trigger network/OS calls or slow initialization
# during test collection. These must be in sys.modules before any test file is imported.
_SIMPLE_MOCKS = [
    "chromadb",
    "chromadb.config",
    "chromadb.utils",
    "chromadb.utils.embedding_functions",
    "sentence_transformers",
    "anthropic",
    "pydantic_core",
]
for _mod in _SIMPLE_MOCKS:
    sys.modules[_mod] = MagicMock()

# Pydantic needs special handling: BaseModel must be a real class so that
# subclasses in models.py can be defined without metaclass errors.
_mock_pydantic = MagicMock()
_mock_pydantic.BaseModel = object  # plain Python class, no validation
sys.modules["pydantic"] = _mock_pydantic


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_config():
    """Config mock with realistic defaults used across test modules."""
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
def sample_courses():
    """Representative course catalog for test data setup."""
    return [
        {
            "title": "Intro to RAG",
            "course_link": "https://example.com/rag",
            "instructor": "Jane Smith",
            "lessons": [
                {"lesson_number": 1, "title": "What is RAG?", "lesson_link": "https://example.com/rag/1"},
                {"lesson_number": 2, "title": "Embeddings", "lesson_link": "https://example.com/rag/2"},
            ],
        },
        {
            "title": "MCP Course",
            "course_link": "https://example.com/mcp",
            "instructor": "John Doe",
            "lessons": [
                {"lesson_number": 1, "title": "MCP Basics", "lesson_link": "https://example.com/mcp/1"},
            ],
        },
    ]
