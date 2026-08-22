"""ScholarLens Streamlit client backed by the FastAPI service."""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st


API_URL = os.getenv("SCHOLARLENS_API_URL", "http://127.0.0.1:8000").rstrip("/")
REQUEST_TIMEOUT = float(os.getenv("SCHOLARLENS_API_TIMEOUT", "300"))

st.set_page_config(page_title="ScholarLens", page_icon="📚", layout="centered")


def api(method: str, path: str, **kwargs: Any) -> Any:
    try:
        response = requests.request(method, f"{API_URL}{path}", timeout=REQUEST_TIMEOUT, **kwargs)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        detail = ""
        if getattr(exc, "response", None) is not None:
            try:
                detail = exc.response.json().get("detail", "")
            except ValueError:
                detail = exc.response.text
        raise RuntimeError(detail or f"Backend request failed: {exc}") from exc


def refresh_sessions() -> list[dict[str, Any]]:
    st.session_state.sessions = api("GET", "/sessions")
    return st.session_state.sessions


def create_session() -> dict[str, Any]:
    session = api("POST", "/sessions")
    refresh_sessions()
    st.session_state.active_session_id = session["id"]
    st.session_state.chats[session["id"]] = []
    return session


def select_session(session_id: str) -> None:
    st.session_state.active_session_id = session_id
    messages = api("GET", f"/sessions/{session_id}/messages")
    chats, turn = [], 0
    for message in messages:
        if message["role"] == "assistant":
            turn += 1
            chats.append({**message, "turn": turn, "graph_state": {}})
        else:
            chats.append(message)
    st.session_state.chats[session_id] = chats


if "sessions" not in st.session_state:
    try:
        refresh_sessions()
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()
if "chats" not in st.session_state:
    st.session_state.chats = {}
if "active_session_id" not in st.session_state:
    if st.session_state.sessions:
        select_session(st.session_state.sessions[0]["id"])
    else:
        create_session()


active_session_id = st.session_state.active_session_id

with st.sidebar:
    if st.button("+ New Chat", use_container_width=True):
        try:
            create_session()
            st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))
    st.divider()
    st.markdown("## 💬 Sessions")
    for session in st.session_state.sessions:
        selected = session["id"] == active_session_id
        if st.button(session["name"], key=f"session_{session['id']}", use_container_width=True, type="primary" if selected else "secondary"):
            if not selected:
                try:
                    select_session(session["id"])
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))

    st.divider()
    st.markdown("## 📄 Documents")
    uploads = st.file_uploader("PDF, TXT, or Markdown", type=["pdf", "txt", "md", "markdown"], accept_multiple_files=True, label_visibility="collapsed")
    if st.button("Add Files", use_container_width=True):
        if not uploads:
            st.warning("No files selected.")
        for upload in uploads or []:
            try:
                with st.spinner(f"Processing {upload.name}…"):
                    result = api("POST", f"/sessions/{active_session_id}/documents/file", files={"file": (upload.name, upload.getvalue(), upload.type)})
                st.success(f"Added: {result['title']} ({result['chunks']} chunks)")
            except RuntimeError as exc:
                st.error(f"Failed: {upload.name} — {exc}")

    st.markdown("**Web Pages**")
    urls = st.text_area("URLs (one per line)", height=80, label_visibility="collapsed", placeholder="https://example.com/paper")
    if st.button("Load URLs", use_container_width=True):
        for url in [item.strip() for item in urls.splitlines() if item.strip()]:
            try:
                with st.spinner(f"Loading {url[:60]}…"):
                    result = api("POST", f"/sessions/{active_session_id}/documents/web", json={"url": url})
                st.success(f"Loaded: {result['title']}")
            except RuntimeError as exc:
                st.error(f"Failed: {exc}")

    st.markdown("**ArXiv Papers**")
    arxiv_query = st.text_input("Paper title or ArXiv ID", label_visibility="collapsed", placeholder="1706.03762 or Attention Is All You Need")
    if st.button("Load ArXiv Paper", use_container_width=True):
        if not arxiv_query.strip():
            st.warning("Enter a paper title or ArXiv ID.")
        else:
            try:
                with st.spinner("Loading from ArXiv…"):
                    result = api("POST", f"/sessions/{active_session_id}/documents/arxiv", json={"query": arxiv_query.strip()})
                st.success(f"Loaded: {result['title']}")
            except RuntimeError as exc:
                st.error(f"Failed: {exc}")

    st.divider()
    st.markdown("### Loaded Documents")
    try:
        documents = api("GET", f"/sessions/{active_session_id}/documents")
        if documents:
            for title in documents:
                st.markdown(f"- {title}")
        else:
            st.caption("No documents loaded yet.")
    except RuntimeError as exc:
        st.caption(f"Could not load document list: {exc}")


st.title("📚 ScholarLens — Research Paper Assistant")
st.markdown("🔍 **Ask questions** from your uploaded papers &nbsp;·&nbsp; ✅ **Verify claims** against recent literature &nbsp;·&nbsp; 🌐 **Search the web** for the latest findings\n\n> Upload documents in the sidebar and start chatting below.")
st.divider()

for message in st.session_state.chats.get(active_session_id, []):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and message.get("graph_state"):
            with st.expander(f"📊 Graph state · turn {message['turn']}"):
                st.json(message["graph_state"])

if prompt := st.chat_input("Ask about your papers, verify a claim, or search the web…"):
    with st.chat_message("user"):
        st.markdown(prompt)
    if prompt.strip().lower().startswith("/btw"):
        query = prompt.strip()[4:].strip()
        with st.chat_message("assistant"):
            if not query:
                st.markdown("Please add a question after `/btw`, e.g. `/btw What is attention?`")
            else:
                try:
                    st.markdown(api("POST", "/btw", json={"query": query})["answer"])
                except RuntimeError as exc:
                    st.error(str(exc))
            st.caption("Side channel — not saved to session history.")
    else:
        chats = st.session_state.chats.setdefault(active_session_id, [])
        chats.append({"role": "user", "content": prompt})
        with st.chat_message("assistant"):
            try:
                with st.spinner("Researching…"):
                    result = api("POST", f"/sessions/{active_session_id}/chat", json={"message": prompt})
                st.markdown(result["answer"])
                turn = sum(1 for item in chats if item["role"] == "assistant") + 1
                with st.expander(f"📊 Graph state · turn {turn}"):
                    st.json(result["graph_state"])
                chats.append({"role": "assistant", "content": result["answer"], "turn": turn, "graph_state": result["graph_state"]})
                refresh_sessions()
            except RuntimeError as exc:
                st.error(str(exc))
