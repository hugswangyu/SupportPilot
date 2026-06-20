from app.agent.rag.backends.base import RetrievedChunk, VectorBackend
from app.agent.rag.backends.chroma_backend import ChromaBackend

__all__ = ["RetrievedChunk", "VectorBackend", "ChromaBackend", "create_backend"]


def create_backend(persist_dir, collection_name: str = "ecom_kb") -> VectorBackend:
    return ChromaBackend(persist_dir=persist_dir, collection_name=collection_name)
