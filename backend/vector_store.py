import os

from dotenv import load_dotenv
from langchain_classic.embeddings import CacheBackedEmbeddings
from langchain_classic.storage import LocalFileStore
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from backend.llm import embedding_dimension, get_embeddings

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────────

EMBEDDING_DIM = embedding_dimension()

# ── Singletons ────────────────────────────────────────────────────────────────

base_embeddings = get_embeddings()
embedding_file_store = LocalFileStore(os.getenv("EMBEDDING_CACHE_DIR", "./embedding_cache/"))
embeddings = CacheBackedEmbeddings.from_bytes_store(
    base_embeddings,
    embedding_file_store,
    namespace=base_embeddings.model,
    query_embedding_cache=True,
    key_encoder="blake2b",
)

_qdrant_url = os.getenv("QDRANT_URL")
qdrant_client = (
    QdrantClient(
        url=_qdrant_url,
        api_key=os.getenv("QDRANT_API_KEY") or None,
        timeout=120,
    )
    if _qdrant_url
    else QdrantClient(path=os.getenv("QDRANT_LOCAL_PATH", "./data/qdrant"))
)


# ── Collection ───────────────────────────────────────────────────────────────

def get_collection_name(session_id: str) -> str:
    return f"scholarlens_{session_id.replace('-', '_')}"


def get_vectorstore(session_id: str) -> QdrantVectorStore:
    collection_name = get_collection_name(session_id)
    if not qdrant_client.collection_exists(collection_name):
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
    return QdrantVectorStore(
        client=qdrant_client,
        collection_name=collection_name,
        embedding=embeddings,
    )


# ── Public API ───────────────────────────────────────────────────────────────

def add_paper(docs: list[Document], session_id: str) -> None:
    get_vectorstore(session_id).add_documents(docs)


def list_papers(session_id: str) -> list[str]:
    collection_name = get_collection_name(session_id)
    if not qdrant_client.collection_exists(collection_name):
        return []
    seen: set[str] = set()
    titles: list[str] = []
    offset = None
    while True:
        points, offset = qdrant_client.scroll(
            collection_name=collection_name,
            with_payload=True,
            limit=100,
            offset=offset,
        )
        for point in points:
            title = (point.payload or {}).get("metadata", {}).get("title")
            if title and title not in seen:
                seen.add(title)
                titles.append(title)
        if offset is None:
            break
    return titles


def search(query: str, session_id: str, k: int = 4) -> list[Document]:
    return get_vectorstore(session_id).similarity_search(query, k=k)
