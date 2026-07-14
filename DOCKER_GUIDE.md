# ScholarLens Docker Guide

The supported deployment is the Compose stack in [`compose.yaml`](compose.yaml). It starts the complete application locally:

- `app` — Streamlit UI and LangGraph workflow
- `ollama` — local chat and embedding inference
- `ollama-init` — pulls the configured models before the app starts
- `qdrant` — persistent vector database

## 1. Configure the environment

```bash
cp .env.example .env
```

Set `TAVILY_API_KEY` in `.env`. The default provider is local Ollama and the default chat model is `qwen3:8b`; use another model if your machine has less memory:

```dotenv
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3:8b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIM=768
TAVILY_API_KEY=tvly-...
```

The default Compose network connects the app to `http://ollama:11434` and `http://qdrant:6333` internally. To use OpenAI instead, set `LLM_PROVIDER=openai` plus `OPENAI_API_KEY`, `OPENAI_MODEL`, and OpenAI embedding settings in `.env`; the model-pull job will then skip the Ollama downloads.

## 2. Start everything

```bash
docker compose up --build
```

The first run downloads the Ollama images and model weights. Open `http://localhost:8501`.

The app starts only after Qdrant is healthy and both configured Ollama models have been pulled successfully.

## 3. Run in the background

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f app
```

## 4. Stop or reset

```bash
docker compose down

# Destructive: remove Qdrant, Ollama, app state, and embedding volumes.
docker compose down -v
```

## 5. Hardware guidance

Ollama can run on CPU, but larger models need substantial RAM and are slower without GPU acceleration. For a smaller machine, set a compact model in `.env`, for example:

```dotenv
OLLAMA_MODEL=qwen3:4b
```

The embedding model must remain compatible with `OLLAMA_EMBEDDING_DIM`. If you change embedding models or dimensions, rebuild the relevant Qdrant collections.

## 6. GPU acceleration

The base Compose file is CPU-compatible. On an NVIDIA host, install the NVIDIA Container Toolkit and add a GPU reservation to the `ollama` service according to the Docker Compose version installed on the host. Keep the Ollama volume so pulled models survive restarts.

## 7. Useful commands

```bash
docker compose ps
docker compose logs -f
docker compose exec ollama ollama list
docker compose exec ollama ollama pull qwen3:4b
docker compose restart app
```

## 8. EC2 or another VM

1. Install Docker Engine and the Compose plugin.
2. Copy the repository and `.env` to the host.
3. Open only the required inbound port, preferably behind a reverse proxy and TLS.
4. Run `docker compose up --build -d`.
5. Put authentication in front of Streamlit before exposing it publicly.
6. Back up the named volumes and rotate the Tavily key through the host secret manager.

Do not expose Qdrant or Ollama directly to the public internet. Only the Streamlit application should be reachable by end users.
