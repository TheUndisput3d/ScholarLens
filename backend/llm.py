"""Centralized model-provider configuration for ScholarLens.

All chat generation and embedding calls go through this module, so each
feature uses the same selected provider: a local Ollama model or OpenAI.
"""

from __future__ import annotations

import os
from typing import Any

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


def provider() -> str:
    """Return the configured provider and reject unsupported values early."""

    selected = os.getenv("LLM_PROVIDER", "ollama").strip().lower()
    if selected not in {"ollama", "openai"}:
        raise ValueError("LLM_PROVIDER must be either 'ollama' or 'openai'.")
    return selected


def _ollama_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")


def _chat_model_name() -> str:
    return os.getenv("OLLAMA_MODEL", "qwen3:8b")


def get_chat_model(*, temperature: float | None = None) -> Any:
    """Return the configured chat model for every application feature."""

    if provider() == "openai":
        kwargs: dict[str, object] = {
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        return ChatOpenAI(**kwargs)

    kwargs: dict[str, object] = {
        "model": _chat_model_name(),
        "base_url": _ollama_url(),
        "reasoning": False,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature
    return ChatOllama(**kwargs)


def get_embeddings() -> Any:
    """Return embeddings from the selected provider."""

    if provider() == "openai":
        return OpenAIEmbeddings(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        )

    return OllamaEmbeddings(
        model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
        base_url=_ollama_url(),
    )


def embedding_dimension() -> int:
    """Dimension for the configured Ollama embedding model.

    The defaults match ``nomic-embed-text`` (768 dimensions) and
    ``text-embedding-3-small`` (1,536 dimensions). Values stay configurable
    so custom models cannot create Qdrant collections with an accidental
    dimension.
    """

    if provider() == "openai":
        return int(os.getenv("OPENAI_EMBEDDING_DIM", "1536"))
    return int(os.getenv("OLLAMA_EMBEDDING_DIM", "768"))
