"""Embeddings for knowledge base retrieval.

@implements IDR-002: Chroma with local multilingual embeddings plus exact-match glossary lookup
@see openspec/tdr/idr/idr-002-kb-retrieval-chroma.md
"""

import hashlib
import math
import os
from typing import Protocol

E5_MODEL = "intfloat/multilingual-e5-small"


class Embedder(Protocol):
    def passages(self, texts: list[str]) -> list[list[float]]: ...
    def query(self, text: str) -> list[float]: ...


class E5Embedder:
    """Local multilingual model; works offline once downloaded (scripts/download_model.py)."""

    def __init__(self, model_name: str = E5_MODEL) -> None:
        from sentence_transformers import SentenceTransformer  # embeddings group

        self.model = SentenceTransformer(model_name)

    def passages(self, texts: list[str]) -> list[list[float]]:
        # E5 expects these prefixes for retrieval.
        vectors = self.model.encode([f"passage: {t}" for t in texts], normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    def query(self, text: str) -> list[float]:
        return self.model.encode([f"query: {text}"], normalize_embeddings=True)[0].tolist()


class HashingEmbedder:
    """Deterministic character-trigram embedder for tests and keyless runs (EDR-002).

    Lexical only: good enough to test indexing and filtering, never used for the demo.
    """

    def __init__(self, dims: int = 512) -> None:
        self.dims = dims

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dims
        padded = f"  {text.lower()}  "
        for i in range(len(padded) - 2):
            digest = hashlib.blake2b(padded[i : i + 3].encode("utf-8"), digest_size=4).digest()
            vec[int.from_bytes(digest, "big") % self.dims] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def passages(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def query(self, text: str) -> list[float]:
        return self._embed(text)


def make_embedder() -> Embedder:
    """EMBEDDINGS=hashing selects the test embedder; the demo always uses E5."""
    if os.environ.get("EMBEDDINGS", "e5") == "hashing":
        return HashingEmbedder()
    return E5Embedder()
