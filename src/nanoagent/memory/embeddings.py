from __future__ import annotations

import numpy as np

_sentence_model = None


def _get_model():
    global _sentence_model
    if _sentence_model is None:
        from sentence_transformers import SentenceTransformer

        _sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _sentence_model


def compute_embedding(text: str) -> list[float]:
    model = _get_model()
    emb = model.encode(text, normalize_embeddings=True)
    return emb.tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    arr_a = np.array(a, dtype=np.float64)
    arr_b = np.array(b, dtype=np.float64)
    dot = float(np.dot(arr_a, arr_b))
    return max(-1.0, min(1.0, dot))
