"""FastAPI service for ScholarLens.

The Streamlit UI calls this module over HTTP.  The API owns session metadata,
LangGraph checkpoints, ingestion, and retrieval so the browser-facing layer
does not import or mutate RAG state directly.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage

from backend.btw_handler import handle_btw
from backend.llm import get_chat_model
from backend.paper_loader import load_arxiv, load_document, load_webpage
from backend.rag_graph import build_graph
from backend.vector_store import add_paper, list_papers


DATA_DIR = Path(os.getenv("SCHOLARLENS_DATA_DIR", "data"))
SESSIONS_FILE = DATA_DIR / "sessions.json"


class UrlIngestRequest(BaseModel):
    url: str


class ArxivIngestRequest(BaseModel):
    query: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=12_000)


class BtwRequest(BaseModel):
    query: str = Field(min_length=1, max_length=12_000)


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_sessions() -> dict[str, dict[str, Any]]:
    _ensure_data_dir()
    try:
        return json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_sessions(sessions: dict[str, dict[str, Any]]) -> None:
    _ensure_data_dir()
    SESSIONS_FILE.write_text(json.dumps(sessions, indent=2), encoding="utf-8")


@lru_cache(maxsize=1)
def _graph():
    _ensure_data_dir()
    return build_graph(db_path=str(DATA_DIR / "checkpoints.db"))


@lru_cache(maxsize=1)
def _rename_llm():
    return get_chat_model(temperature=0)


def _session_or_404(session_id: str) -> dict[str, Any]:
    session = _load_sessions().get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def _new_session() -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    session = {
        "id": session_id,
        "name": "New Session",
        "created_at": datetime.now().isoformat(),
        "is_named": False,
    }
    sessions = _load_sessions()
    sessions[session_id] = session
    _save_sessions(sessions)
    return session


def _rename_session(session_id: str, first_message: str) -> dict[str, Any]:
    sessions = _load_sessions()
    session = sessions[session_id]
    if session.get("is_named"):
        return session
    try:
        response = _rename_llm().invoke([
            {"role": "system", "content": "Create a concise 3-5 word title for this research chat. Return only the title."},
            {"role": "user", "content": first_message[:500]},
        ])
        session["name"] = response.content.strip() or "New Session"
    except Exception:
        session["name"] = "New Session"
    session["is_named"] = True
    sessions[session_id] = session
    _save_sessions(sessions)
    return session


def _serialize_state(values: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in values.items():
        if key == "messages":
            out[key] = [
                {"type": type(message).__name__, "content": message.content[:300] if isinstance(message.content, str) else repr(message.content)[:300]}
                for message in (value or [])
            ]
        elif key == "retrieved_docs":
            out[key] = [{"content": doc.page_content[:300], "metadata": doc.metadata} for doc in (value or [])]
        else:
            out[key] = value
    return out


def _messages(session_id: str) -> list[dict[str, str]]:
    state = _graph().get_state({"configurable": {"thread_id": session_id}})
    if not state or not state.values:
        return []
    result = []
    for message in state.values.get("messages", []):
        content = message.content if isinstance(message.content, str) else str(message.content)
        name = type(message).__name__
        if name == "HumanMessage":
            result.append({"role": "user", "content": content})
        elif name in {"AIMessage", "AIMessageChunk"}:
            result.append({"role": "assistant", "content": content})
    return result


app = FastAPI(title="ScholarLens API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("SCHOLARLENS_FRONTEND_ORIGIN", "http://localhost:8501")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sessions")
def sessions() -> list[dict[str, Any]]:
    return sorted(_load_sessions().values(), key=lambda item: item["created_at"], reverse=True)


@app.post("/sessions", status_code=201)
def create_session() -> dict[str, Any]:
    return _new_session()


@app.get("/sessions/{session_id}/messages")
def session_messages(session_id: str) -> list[dict[str, str]]:
    _session_or_404(session_id)
    return _messages(session_id)


@app.get("/sessions/{session_id}/documents")
def session_documents(session_id: str) -> list[str]:
    _session_or_404(session_id)
    return list_papers(session_id)


def _ingest(session_id: str, loader) -> dict[str, Any]:
    _session_or_404(session_id)
    try:
        docs = loader()
        add_paper(docs, session_id)
        title = docs[0].metadata.get("title") if docs else "source"
        return {"title": title, "chunks": len(docs)}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/sessions/{session_id}/documents/file")
async def ingest_file(session_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    suffix = Path(file.filename or "upload.txt").suffix
    if suffix.lower() not in {".pdf", ".txt", ".md", ".markdown"}:
        raise HTTPException(status_code=415, detail="Supported file types are PDF, TXT, and Markdown")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        handle.write(await file.read())
        path = handle.name
    try:
        result = _ingest(session_id, lambda: load_document(path))
        result["title"] = Path(file.filename or result["title"]).stem
        return result
    finally:
        Path(path).unlink(missing_ok=True)


@app.post("/sessions/{session_id}/documents/web")
def ingest_web(session_id: str, request: UrlIngestRequest) -> dict[str, Any]:
    return _ingest(session_id, lambda: load_webpage(request.url))


@app.post("/sessions/{session_id}/documents/arxiv")
def ingest_arxiv(session_id: str, request: ArxivIngestRequest) -> dict[str, Any]:
    return _ingest(session_id, lambda: load_arxiv(request.query))


@app.post("/sessions/{session_id}/chat")
def chat(session_id: str, request: ChatRequest) -> dict[str, Any]:
    session = _session_or_404(session_id)
    first_message = not _messages(session_id)
    input_state = {
        "messages": [HumanMessage(content=request.message)], "session_id": session_id,
        "query": request.message, "route": None, "retrieved_docs": [],
        "retrieval_attempts": 0, "claim_verdict": None, "claim_source": None,
        "superseding_papers": [], "answer": None, "is_relevant": None, "rewrite_count": 0,
    }
    try:
        values = _graph().invoke(input_state, {"configurable": {"thread_id": session_id}})
        answer = values.get("answer") or "No response generated."
        if first_message:
            session = _rename_session(session_id, request.message)
        return {"answer": answer, "graph_state": _serialize_state(values), "session": session}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/btw")
def btw(request: BtwRequest) -> dict[str, str]:
    try:
        return {"answer": "".join(handle_btw(request.query))}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
