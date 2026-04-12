"""Embedding module — vector representations for Cold Weaver collisions.

Two backends:
1. SentenceTransformer (all-MiniLM-L6-v2) — high quality, needs torch
2. HashEmbedder — lightweight fallback using character n-gram hashing + numpy
"""

import hashlib
import logging
import struct
from functools import lru_cache

import numpy as np

logger = logging.getLogger("delirium.embeddings")

EMBEDDING_DIM = 768  # matches paraphrase-multilingual-mpnet-base-v2


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def embedding_to_bytes(vec: np.ndarray) -> bytes:
    """Serialize a float32 numpy array to bytes for SQLite storage."""
    return vec.astype(np.float32).tobytes()


def bytes_to_embedding(data: bytes) -> np.ndarray:
    """Deserialize bytes back to a float32 numpy array."""
    return np.frombuffer(data, dtype=np.float32).copy()


class HashEmbedder:
    """Lightweight character n-gram hashing embedder. No external model needed.

    Uses the hashing trick: character n-grams are hashed into a fixed-size
    vector. Not as good as a real model, but works for prototype collision
    detection where we need relative distances, not absolute semantics.
    """

    def __init__(self, dim: int = EMBEDDING_DIM, ngram_range: tuple = (3, 5)):
        self.dim = dim
        self.ngram_range = ngram_range

    def embed(self, text: str) -> np.ndarray:
        text = text.lower().strip()
        vec = np.zeros(self.dim, dtype=np.float32)

        for n in range(self.ngram_range[0], self.ngram_range[1] + 1):
            for i in range(len(text) - n + 1):
                ngram = text[i:i + n]
                h = int(hashlib.md5(ngram.encode()).hexdigest(), 16)
                idx = h % self.dim
                sign = 1.0 if (h // self.dim) % 2 == 0 else -1.0
                vec[idx] += sign

        # L2 normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        return np.array([self.embed(t) for t in texts])


class SentenceTransformerEmbedder:
    """High-quality embeddings via sentence-transformers (if installed)."""

    def __init__(self, model_name: str = "paraphrase-multilingual-mpnet-base-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> np.ndarray:
        return self.model.encode(text, normalize_embeddings=True, show_progress_bar=False)

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def get_embedder() -> SentenceTransformerEmbedder:
    """Get the sentence-transformer embedder. No hash fallback."""
    embedder = SentenceTransformerEmbedder()
    logger.info("Using SentenceTransformer embedder (%s)", embedder.model.get_sentence_embedding_dimension())
    return embedder
