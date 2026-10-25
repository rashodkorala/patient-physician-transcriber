"""Download the embedding model once so the demo runs offline (IDR-002).

Usage (from server/): uv run python scripts/download_model.py
"""

import sys
from pathlib import Path

# Scripts run with scripts/ on the import path; the server modules live one level up.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kb.embeddings import E5_MODEL, E5Embedder

if __name__ == "__main__":
    embedder = E5Embedder()
    print(f"{E5_MODEL} ready; sample dims: {len(embedder.query('chest pain'))}")
