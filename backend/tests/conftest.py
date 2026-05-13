import sys
import os
from unittest.mock import MagicMock

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
