"""本地向量化封装：使用 sentence-transformers 加载 BGE 系列模型。

BGE 模型在检索场景下需要对 query 加指令前缀（passages 不需要）：
- encode()     用于文档入库，不加前缀
- encode_one() 用于查询向量化，自动加前缀
"""

from typing import Iterable


class Embedder:
    def __init__(self, model_name: str = "BAAI/bge-small-zh-v1.5", batch_size: int = 64):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "sentence-transformers 未安装。请运行 `pip install sentence-transformers`。"
            ) from e

        self._model = SentenceTransformer(model_name)
        self._model_name = model_name
        self._batch_size = batch_size
        # BGE 系列 query 需要加检索指令，passage 不需要
        self._query_instruction = "为这个句子生成表示以用于检索相关文章：" if "bge" in model_name.lower() else ""

    @property
    def model(self) -> str:
        return self._model_name

    def encode(self, texts: Iterable[str]) -> list[list[float]]:
        """批量编码文档（入库用），不加 query 前缀。"""
        texts = list(texts)
        if not texts:
            return []
        vecs = self._model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vecs.tolist()

    def encode_one(self, text: str) -> list[float]:
        """编码单条 query，自动加 BGE 检索指令前缀。"""
        if self._query_instruction:
            text = self._query_instruction + text
        return self.encode([text])[0]
