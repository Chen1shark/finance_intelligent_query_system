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

    @staticmethod
    def load_vector_store():
        """
        读取向量库文件并返回结构化数据。
        返回:
            dict: 向量库内容，包含标准问题与SQL字段。
        """
        with open(VECTOR_STORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def save_vector_store(data):
        """
        将向量库数据持久化到本地JSON文件。
        参数:
            data (dict): 向量库结构化数据。
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
        """
        调用阿里云OpenAI兼容接口生成文本向量。
        参数:
            text (str): 待向量化的文本。
        返回:
            np.ndarray: 向量化后的浮点向量。
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
        """
        对向量矩阵进行L2归一化以便计算余弦相似度。
        参数:
            vectors (np.ndarray): 形状为(n, d)的向量矩阵。
        返回:
            np.ndarray: 归一化后的向量矩阵。
        """
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return vectors / norms

    @staticmethod
    def rebuild_vector_store_embeddings():
        """
        启动时对向量库中的question重新向量化并写回文件，同时写入内存缓存。
        返回:
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
        """
        获取模板条目的向量，优先使用内存缓存。
        参数:
            items (list): 模板条目列表。
        返回:
            list[np.ndarray]: 向量列表。
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
        """
        基于向量构建FAISS索引。
        参数:
            vectors (list): 向量列表。
        返回:
            faiss.IndexFlatIP: 内积索引，用于相似度检索。
        """
        matrix = np.vstack(vectors).astype("float32")
        matrix = VectorService.normalize_vectors(matrix)
        dim = matrix.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(matrix)
        return index

    @staticmethod
    def match_user_query(user_input, top_k=1, core_need=None):
        """
        使用核心需求向量检索最相似的标准问题与SQL。
        参数:
            user_input (str): 用户原始输入。
            top_k (int): 返回最相似的条目数量。
            core_need (str): 预提取的核心需求，为None时自动提取。
        返回:
            list[dict] | None: 匹配结果列表，包含相似度、标准问题与SQL。
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
