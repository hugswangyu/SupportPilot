"""知识库检索工具：通过向量检索回答 FAQ、政策类问题。

与查订单/查物流这类「结构化数据查询」工具不同，
search_knowledge 面向非结构化文本（退换货政策、配送说明、FAQ 等），
返回 Top-K 命中片段及其来源，由 LLM 引用回答。

使用 ChromaDB 嵌入式向量数据库（HNSW 索引）。
为避免每次进程启动都重建索引，单例缓存 Retriever。
"""

from pathlib import Path
from typing import Optional

from app.config.settings import settings
from app.agent.rag.backends import create_backend
from app.agent.rag.embedder import Embedder
from app.agent.rag.retriever import KnowledgeRetriever

_retriever: Optional[KnowledgeRetriever] = None


def _create_backend_from_settings():
    return create_backend(
        persist_dir=Path(settings.chroma_persist_dir),
        collection_name=settings.chroma_collection,
    )


def _get_retriever() -> KnowledgeRetriever:
    global _retriever
    if _retriever is None:
        embedder = Embedder(model_name=settings.embedding_model)
        backend = _create_backend_from_settings()
        _retriever = KnowledgeRetriever(embedder=embedder, backend=backend)
        _retriever.load()
    return _retriever


def reset_retriever() -> None:
    """清空单例缓存（测试或切换后端时使用）。"""
    global _retriever
    _retriever = None


def search_knowledge(query: str, top_k: int = 3) -> dict:
    """检索退换货政策、配送说明、会员权益、FAQ 等知识库内容。

    Returns:
        {
          "success": bool,
          "backend": "chroma",
          "query": str,
          "results": [
            {"doc": "...", "section": "...", "score": 0.83, "text": "..."},
            ...
          ],
          "error": "..."  # 仅失败时存在
        }
    """
    if not query or not query.strip():
        return {"success": False, "error": "query 不能为空", "query": query, "results": []}

    try:
        retriever = _get_retriever()
    except FileNotFoundError as e:
        return {
            "success": False,
            "error": str(e),
            "backend": "chroma",
            "query": query,
            "results": [],
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"知识库初始化失败: {e}",
            "backend": "chroma",
            "query": query,
            "results": [],
        }

    top_k = max(1, min(int(top_k or 3), 5))
    hits = retriever.search(query, top_k=top_k)

    return {
        "success": True,
        "backend": "chroma",
        "query": query,
        "results": [
            {
                "doc": h.chunk.doc,
                "section": h.chunk.section,
                "score": round(h.score, 4),
                "text": h.chunk.text,
            }
            for h in hits
        ],
    }
