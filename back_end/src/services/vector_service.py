import json
import numpy as np
import faiss
from src.core.config import get_settings, DATA_DIR
from src.core.llm_client import get_llm_client
from src.services.semantic_service import SemanticService

VECTOR_STORE_FILE = DATA_DIR / "vector_store.json"

_CACHED_ITEMS = None
_CACHED_VECTORS = None


class VectorService:
    """负责向量库读写、向量化和相似度检索。"""

    @staticmethod
    def load_vector_store():
        """读取本地向量库文件。

        Returns:
            dict: 向量库内容，包含标准问题、SQL 模板和 embedding 信息。
        """
        with open(VECTOR_STORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def save_vector_store(data):
        """将向量库数据持久化到本地 JSON 文件。

        Args:
            data: 待写入的向量库结构化数据。
        """
        settings = get_settings()
        embedding_model = data.get("embedding_model", settings.embed_model)
        items = data.get("items", [])
        lines = ["{", f'  "embedding_model": {json.dumps(embedding_model, ensure_ascii=False)},', '  "items": [']
        for idx, item in enumerate(items):
            question = json.dumps(item.get("question", ""), ensure_ascii=False)
            sql = json.dumps(item.get("sql", ""), ensure_ascii=False)
            lines.append("    {")
            lines.append(f'      "question": {question},')
            lines.append(f'      "sql": {sql},')
            embedding = item.get("embedding", [])
            embedding_str = json.dumps(embedding, ensure_ascii=False)
            lines.append(f'      "embedding": {embedding_str}')
            lines.append("    }" + ("," if idx < len(items) - 1 else ""))
        lines.append("  ]")
        lines.append("}")
        with open(VECTOR_STORE_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    @staticmethod
    def embed_text(text):
        """调用向量模型生成文本 embedding。

        Args:
            text: 待向量化的文本内容。

        Returns:
            np.ndarray: ``float32`` 类型的一维向量。

        Raises:
            ValueError: 当模型未返回有效 embedding 时抛出。
        """
        settings = get_settings()
        client = get_llm_client()
        response = client.embeddings.create(
            model=settings.embed_model,
            input=text
        )
        if response.data and response.data[0].embedding:
            return np.array(response.data[0].embedding, dtype="float32")
        raise ValueError("未返回 embedding")

    @staticmethod
    def normalize_vectors(vectors):
        """对向量矩阵做 L2 归一化。

        Args:
            vectors: 形状为 ``(n, d)`` 的向量矩阵。

        Returns:
            np.ndarray: 归一化后的向量矩阵。
        """
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return vectors / norms

    @staticmethod
    def rebuild_vector_store_embeddings():
        """重建向量库条目的 embedding 并刷新缓存。

        Returns:
            int: 完成向量化的条目数量。
        """
        global _CACHED_ITEMS, _CACHED_VECTORS
        data = VectorService.load_vector_store()
        items = data.get("items", [])
        vectors = []
        for item in items:
            vec = VectorService.embed_text(item.get("question", ""))
            item["embedding"] = vec.tolist()
            vectors.append(vec)
        VectorService.save_vector_store(data)
        _CACHED_ITEMS = items
        _CACHED_VECTORS = vectors
        return len(items)

    @staticmethod
    def get_item_embeddings(items):
        """获取模板条目的向量列表，优先复用缓存。

        Args:
            items: 向量库中的模板条目列表。

        Returns:
            list[np.ndarray]: 每个模板条目对应的向量列表。
        """
        if _CACHED_ITEMS is items and isinstance(_CACHED_VECTORS, list) and len(_CACHED_VECTORS) == len(items):
            if all(isinstance(v, np.ndarray) and v.size > 0 for v in _CACHED_VECTORS):
                return _CACHED_VECTORS
        vectors = []
        for item in items:
            embedding = item.get("embedding")
            if isinstance(embedding, list) and len(embedding) > 0:
                vec = np.array(embedding, dtype="float32")
                if vec.size > 0:
                    vectors.append(vec)
                    continue
            vectors.append(VectorService.embed_text(item.get("question", "")))
        return vectors

    @staticmethod
    def build_faiss_index(vectors):
        """基于向量列表构建 FAISS 相似度索引。

        Args:
            vectors: 模板向量列表。

        Returns:
            faiss.IndexFlatIP: 基于内积计算相似度的索引对象。
        """
        matrix = np.vstack(vectors).astype("float32")
        matrix = VectorService.normalize_vectors(matrix)
        dim = matrix.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(matrix)
        return index

    @staticmethod
    def match_user_query(user_input, top_k=1, core_need=None):
        """根据用户需求检索最相似的模板问题和 SQL。

        Args:
            user_input: 用户原始查询文本。
            top_k: 需要返回的最相似结果条数。
            core_need: 已提取好的核心需求；为空时自动提取。

        Returns:
            list[dict] | None: 匹配结果列表；当无法提取核心需求或无模板数据时返回 ``None``。
        """
        if core_need is None:
            core_need = SemanticService.extract_core_need(user_input)
        if not core_need:
            return None
        data = VectorService.load_vector_store()
        items = data.get("items", [])
        if not items:
            return None
        vectors = VectorService.get_item_embeddings(items)
        index = VectorService.build_faiss_index(vectors)
        query_vec = VectorService.embed_text(core_need).reshape(1, -1)
        query_vec = VectorService.normalize_vectors(query_vec)
        scores, indices = index.search(query_vec, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            item = items[idx]
            results.append({
                "core_need": core_need,
                "score": float(score),
                "question": item.get("question"),
                "sql": item.get("sql")
            })
        return results
