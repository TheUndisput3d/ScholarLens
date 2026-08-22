from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

import backend.api as scholar_api


class FakeGraph:
    def __init__(self) -> None:
        self.states: dict[str, dict] = {}

    def invoke(self, state: dict, config: dict) -> dict:
        session_id = config["configurable"]["thread_id"]
        values = {
            **state,
            "answer": "Grounded test answer.",
            "messages": [
                state["messages"][0],
                AIMessage(content="Grounded test answer."),
            ],
        }
        self.states[session_id] = values
        return values

    def get_state(self, config: dict):
        return SimpleNamespace(values=self.states.get(config["configurable"]["thread_id"], {}))


def test_session_ingestion_and_chat_flow(tmp_path, monkeypatch) -> None:
    graph = FakeGraph()
    monkeypatch.setattr(scholar_api, "DATA_DIR", tmp_path)
    monkeypatch.setattr(scholar_api, "_graph", lambda: graph)
    monkeypatch.setattr(scholar_api, "_rename_session", lambda session_id, message: scholar_api._load_sessions()[session_id])
    monkeypatch.setattr(scholar_api, "load_document", lambda path: [SimpleNamespace(metadata={"title": "Upload"})])
    monkeypatch.setattr(scholar_api, "add_paper", lambda docs, session_id: None)
    monkeypatch.setattr(scholar_api, "list_papers", lambda session_id: ["Upload"])

    client = TestClient(scholar_api.app)
    session = client.post("/sessions").json()
    session_id = session["id"]

    assert client.get("/sessions").json()[0]["id"] == session_id
    upload = client.post(
        f"/sessions/{session_id}/documents/file",
        files={"file": ("notes.txt", b"test source", "text/plain")},
    )
    assert upload.status_code == 200
    assert client.get(f"/sessions/{session_id}/documents").json() == ["Upload"]

    chat = client.post(f"/sessions/{session_id}/chat", json={"message": "What does the source say?"})
    assert chat.status_code == 200
    assert chat.json()["answer"] == "Grounded test answer."
    assert client.get(f"/sessions/{session_id}/messages").json() == [
        {"role": "user", "content": "What does the source say?"},
        {"role": "assistant", "content": "Grounded test answer."},
    ]
