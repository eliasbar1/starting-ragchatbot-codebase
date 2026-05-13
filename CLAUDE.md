# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
# Start the server (from project root)
./run.sh

# Or manually
cd backend && uv run uvicorn app:app --reload --port 8000
```

The app is served at `http://localhost:8000`. The frontend is served as static files from FastAPI — there is no separate frontend build step.

**Required:** A `.env` file in the project root with:
```
ANTHROPIC_API_KEY=your_key_here
```

On first startup, the server loads all `.txt` files from the `docs/` folder into ChromaDB, and the `sentence-transformers` embedding model (`all-MiniLM-L6-v2`) is downloaded automatically if not cached.

## Architecture

This is a RAG (Retrieval-Augmented Generation) chatbot. The backend is a FastAPI app (`backend/app.py`) that serves both the API and the frontend static files. There is no separate frontend server.

### Query flow

1. **Frontend** (`frontend/script.js`) — POSTs `{ query, session_id }` to `POST /api/query`
2. **`app.py`** — receives the request, manages session creation, delegates to `RAGSystem.query()`
3. **`rag_system.py`** — orchestrates: fetches conversation history → calls `AIGenerator`
4. **`ai_generator.py`** — makes a first Claude API call with the `search_course_content` tool available; if Claude decides to search, handles tool execution and makes a second Claude API call to synthesize the answer
5. **`search_tools.py`** — `CourseSearchTool.execute()` calls `VectorStore.search()`; also tracks source labels for the UI
6. **`vector_store.py`** — ChromaDB with two collections: `course_catalog` (course titles/metadata) and `course_content` (chunked lesson text). Course name resolution uses semantic search against `course_catalog` to handle fuzzy matching before filtering `course_content`
7. **`session_manager.py`** — in-memory session store; keeps the last `MAX_HISTORY` (default: 2) exchanges per session, prepended to the Claude system prompt as conversation context

### Course document format

Course documents are plain `.txt` files in `docs/`. `DocumentProcessor` parses them expecting:
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 0: <lesson title>
Lesson Link: <url>
<lesson content...>

Lesson 1: <lesson title>
...
```
The course title doubles as the unique ID in ChromaDB — duplicate titles are skipped on startup. Text is chunked by sentence boundaries at ~800 chars with 100-char overlap.

### Key design decisions

- **Two-call Claude pattern**: the first call lets Claude decide whether to search; the second call (without tools) synthesizes the final answer from tool results. This is intentional — do not collapse into one call.
- **Tool-based retrieval**: search is implemented as a Claude tool (`search_course_content`), not a pre-retrieval step. Claude controls whether and what to search.
- **`course_title` is the primary key**: in ChromaDB, the course title is used as the document ID in `course_catalog` and as the filter field in `course_content`. Renaming a course title means re-ingesting documents.
- **No persistent sessions**: `SessionManager` is in-memory only; sessions reset on server restart.

## Dependencies

Managed with `uv`. To add packages: `uv add <package>`. The `.venv` is local to the project.
