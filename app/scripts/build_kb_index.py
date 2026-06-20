"""离线构建知识库向量索引（ChromaDB）。

用法：
  python app/scripts/build_kb_index.py

流程：
  1. 扫描 knowledge/ 下的所有 .md 文件，按二级标题切分。
  2. 调用 OpenAI Embeddings 将每个 chunk 向量化。
  3. 写入 ChromaDB PersistentClient（HNSW 索引）。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from app.config.settings import settings  # noqa: E402
from app.agent.rag.backends import create_backend  # noqa: E402
from app.agent.rag.chunker import chunk_markdown_dir  # noqa: E402
from app.agent.rag.embedder import Embedder  # noqa: E402


def main():
    kb_dir = ROOT / settings.kb_dir

    if not kb_dir.exists():
        print(f"❌ 知识库目录不存在: {kb_dir}")
        sys.exit(1)

    backend = create_backend(
        persist_dir=ROOT / settings.chroma_persist_dir,
        collection_name=settings.chroma_collection,
    )

    print("=" * 60)
    print("  电商平台 · 知识库索引构建（ChromaDB）")
    print(f"  源目录    : {kb_dir}")
    print(f"  索引目录  : {ROOT / settings.chroma_persist_dir}")
    print(f"  Embedding : {settings.embedding_model}")
    print("=" * 60)

    print("\n[1/3] 扫描并切分 markdown 文档...")
    chunks = chunk_markdown_dir(kb_dir)
    if not chunks:
        print("❌ 未发现任何文档，请检查 knowledge/ 目录")
        sys.exit(1)

    by_doc: dict[str, int] = {}
    for c in chunks:
        by_doc[c.doc] = by_doc.get(c.doc, 0) + 1
    for doc, n in by_doc.items():
        print(f"   - {doc}: {n} chunk")
    print(f"   合计 {len(chunks)} 个 chunk")

    print(f"\n[2/3] 调用 {settings.embedding_model} 批量向量化...")
    embedder = Embedder(model_name=settings.embedding_model)
    vectors = embedder.encode([c.text for c in chunks])
    dim = len(vectors[0]) if vectors else 0
    print(f"   完成，向量维度 = {dim}")

    print("\n[3/3] 写入 ChromaDB 索引...")
    backend.upsert(
        chunks=chunks,
        vectors=vectors,
        embedding_model=settings.embedding_model,
    )
    print(f"   已写入 {backend.size()} 条向量")

    print("\n🎉 索引构建完成。")


if __name__ == "__main__":
    main()
