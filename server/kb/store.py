"""Knowledge base: loads curated content, indexes it in Chroma, and answers lookups.

Glossary terms are matched exactly (after normalisation) and fuzzily, never by vector
search alone, so a medical term never depends on embedding quality. Tone guidance,
empathy phrases, and condition explainers use vector search filtered by language.

@implements ADR-002: Knowledge base feeding translation
@implements IDR-002: Chroma with local multilingual embeddings plus exact-match glossary lookup
@see openspec/tdr/idr/idr-002-kb-retrieval-chroma.md
"""

import re
import unicodedata
import uuid
from dataclasses import dataclass
from pathlib import Path

import chromadb
import yaml
from rapidfuzz import fuzz

from contracts import GlossaryEntry
from kb.embeddings import Embedder

CONTENT_DIR = Path(__file__).parent / "content"
FUZZY_THRESHOLD = 90
FUZZY_MIN_LENGTH = 6


@dataclass(frozen=True)
class GlossaryTerm:
    pair: str  # target language code, e.g. "pa-IN"
    en: str
    aliases_en: tuple[str, ...]
    target: str
    aliases_target: tuple[str, ...]
    explanation_en: str
    explanation_target: str


PAIR_FILES = {"pa-IN": "en-pa.yaml", "fr-CA": "en-fr.yaml", "si-LK": "en-si.yaml", "ta-LK": "en-ta.yaml"}
LANG_FILES = {"pa-IN": "pa", "fr-CA": "fr", "en-CA": "en", "si-LK": "si", "ta-LK": "ta"}


def normalise(text: str) -> str:
    """Case-fold, unify Unicode forms, and collapse punctuation and spacing."""
    text = unicodedata.normalize("NFC", text).casefold()
    return " ".join(re.sub(r"[^\w\s]", " ", text).split())


def _contains(haystack: str, needle: str) -> bool:
    if not needle:
        return False
    return re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack) is not None


def _sections(markdown: str) -> list[tuple[str, str]]:
    """Split on '## ' headings; each section is one retrievable chunk."""
    parts = re.split(r"^## +(.+)$", markdown, flags=re.M)
    return [(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]


class KnowledgeBase:
    def __init__(self, embedder: Embedder, content_dir: Path = CONTENT_DIR) -> None:
        self.embedder = embedder
        self.glossary: list[GlossaryTerm] = []
        self.client = chromadb.EphemeralClient()
        # Ephemeral clients share one in-process store, so each instance gets its own collection.
        self.collection = self.client.create_collection(
            name=f"kb-{uuid.uuid4().hex}", metadata={"hnsw:space": "cosine"}
        )
        self._load(content_dir)

    def _load(self, content_dir: Path) -> None:
        for pair, file in PAIR_FILES.items():
            data = yaml.safe_load((content_dir / "glossary" / file).read_text(encoding="utf-8"))
            for e in data["entries"]:
                self.glossary.append(
                    GlossaryTerm(
                        pair=pair,
                        en=e["en"],
                        aliases_en=tuple(e.get("aliases_en") or ()),
                        target=e["target"],
                        aliases_target=tuple(e.get("aliases_target") or ()),
                        explanation_en=e["explanation_en"],
                        explanation_target=e["explanation_target"],
                    )
                )

        ids, docs, metas = [], [], []
        for lang, stem in LANG_FILES.items():
            tone = (content_dir / "tone" / f"{stem}.md").read_text(encoding="utf-8")
            for title, body in _sections(tone):
                ids.append(f"tone:{lang}:{title}")
                docs.append(f"{title}. {body}")
                metas.append({"kind": "tone", "lang": lang})
            empathy = yaml.safe_load((content_dir / "empathy" / f"{stem}.yaml").read_text(encoding="utf-8"))
            for i, e in enumerate(empathy["entries"]):
                ids.append(f"empathy:{lang}:{i}")
                docs.append(e["phrase"])
                metas.append(
                    {"kind": "empathy", "lang": lang, "intent": e["intent"], "emotions": ",".join(e["emotions"])}
                )
        for path in sorted((content_dir / "conditions").glob("*.md")):
            for lang, body in _sections(path.read_text(encoding="utf-8")):
                ids.append(f"condition:{path.stem}:{lang}")
                docs.append(body)
                metas.append({"kind": "condition", "lang": lang, "condition": path.stem})
        self.collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=self.embedder.passages(docs))

    # ---------- glossary (deterministic) ----------

    def glossary_hits(self, text: str, source: str, target: str) -> list[GlossaryEntry]:
        """Terms said in `text`, as GlossaryEntry(term in source, translation and explanation in target)."""
        pair = target if source == "en-CA" else source
        from_english = source == "en-CA"
        said = normalise(text)
        hits: list[GlossaryEntry] = []
        for term in (t for t in self.glossary if t.pair == pair):
            forms = (term.en, *term.aliases_en) if from_english else (term.target, *term.aliases_target)
            if not any(self._matches(said, normalise(f)) for f in forms):
                continue
            hits.append(
                GlossaryEntry(
                    term=term.en if from_english else term.target,
                    translation=term.target if from_english else term.en,
                    explanation=term.explanation_target if from_english else term.explanation_en,
                )
            )
        return hits

    @staticmethod
    def _matches(said: str, form: str) -> bool:
        if _contains(said, form):
            return True
        return len(form) >= FUZZY_MIN_LENGTH and fuzz.partial_ratio(form, said) >= FUZZY_THRESHOLD

    # ---------- vector search (filtered by language) ----------

    def _search(self, query: str, where: dict, k: int) -> list[str]:
        result = self.collection.query(query_embeddings=[self.embedder.query(query)], n_results=k, where=where)
        return result["documents"][0] if result["documents"] else []

    def tone_guidance(self, query: str, language: str, k: int = 3) -> list[str]:
        return self._search(query, {"$and": [{"kind": "tone"}, {"lang": language}]}, k)

    def empathy_phrases(self, query: str, language: str, k: int = 3) -> list[str]:
        return self._search(query, {"$and": [{"kind": "empathy"}, {"lang": language}]}, k)

    def condition_explainers(self, query: str, language: str, k: int = 1) -> list[str]:
        return self._search(query, {"$and": [{"kind": "condition"}, {"lang": language}]}, k)
