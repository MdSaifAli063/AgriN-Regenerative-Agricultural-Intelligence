"""
KrishiNet-BRICS - RAG Embedding Service.

Provides vector embedding generation, caching, and cosine similarity calculations:
  - Generates 768-dimensional normalized embeddings via Gemini API or offline engine
  - Maintains precomputed embeddings in data/seed/knowledge_embeddings.json
  - Pure Python cosine similarity computation
"""

import json
import logging
import math
import os
from typing import Dict, List, Optional

from app.ai.gemini_client import gemini_client
from app.core.config import settings

logger = logging.getLogger("krishinet.rag.embedding")

CACHE_FILE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "..",
        "data",
        "seed",
        "knowledge_embeddings.json",
    )
)


class EmbeddingService:
    def __init__(self):
        self._cache: Dict[str, List[float]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Loads precomputed embeddings from json file if available."""
        if os.path.exists(CACHE_FILE_PATH):
            try:
                with open(CACHE_FILE_PATH, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded {len(self._cache)} precomputed embeddings from {CACHE_FILE_PATH}")
            except Exception as e:
                logger.warning(f"Failed to read precomputed embeddings file: {e}")

    def save_cache(self) -> None:
        """Saves current embedding cache back to json file."""
        try:
            os.makedirs(os.path.dirname(CACHE_FILE_PATH), exist_ok=True)
            with open(CACHE_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._cache, f)
            logger.info(f"Saved {len(self._cache)} embeddings to {CACHE_FILE_PATH}")
        except Exception as e:
            logger.warning(f"Could not persist embeddings cache: {e}")

    async def get_embedding(self, text: str, is_query: bool = False) -> List[float]:
        """Returns embedding vector for text, leveraging cache or generating new."""
        # Clean and hash text key
        clean = text.strip()
        if not is_query and clean in self._cache:
            return self._cache[clean]

        if is_query:
            vec = await gemini_client.embed_query(clean)
        else:
            vec_list = await gemini_client.embed_texts([clean], task_type="RETRIEVAL_DOCUMENT")
            vec = vec_list[0] if vec_list else [0.0] * settings.GEMINI_EMBEDDING_DIM
            self._cache[clean] = vec

        return vec

    async def get_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Batch resolves embeddings for multiple text passages."""
        results: List[List[float]] = []
        to_fetch_indices: List[int] = []
        to_fetch_texts: List[str] = []

        for idx, t in enumerate(texts):
            clean = t.strip()
            if clean in self._cache:
                results.append(self._cache[clean])
            else:
                results.append([])
                to_fetch_indices.append(idx)
                to_fetch_texts.append(clean)

        if to_fetch_texts:
            fetched_vecs = await gemini_client.embed_texts(to_fetch_texts, task_type="RETRIEVAL_DOCUMENT")
            for i, vec in enumerate(fetched_vecs):
                orig_idx = to_fetch_indices[i]
                orig_text = to_fetch_texts[i]
                results[orig_idx] = vec
                self._cache[orig_text] = vec

        return results

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Computes cosine similarity between two float vectors."""
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0

        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))

        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0

        return max(0.0, min(1.0, dot / (norm1 * norm2)))


embedding_service = EmbeddingService()
