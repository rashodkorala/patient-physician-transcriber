"""Download the embedding model once so the demo runs offline (IDR-002).

Usage (from server/): uv run python scripts/download_model.py
"""

from kb.embeddings import E5_MODEL, E5Embedder

if __name__ == "__main__":
    embedder = E5Embedder()
    print(f"{E5_MODEL} ready; sample dims: {len(embedder.query('chest pain'))}")
