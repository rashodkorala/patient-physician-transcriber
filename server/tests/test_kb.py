"""Knowledge base retrieval tests (task 2.2, IDR-002). Run offline with the hashing embedder."""

import pytest

from kb.embeddings import HashingEmbedder
from kb.store import KnowledgeBase


@pytest.fixture(scope="module")
def kb():
    return KnowledgeBase(HashingEmbedder())


def terms(hits):
    return [h.term for h in hits]


def test_glossary_exact_match_english_to_punjabi_idr_002(kb):
    hits = kb.glossary_hits("Use the nitroglycerin spray under your tongue.", "en-CA", "pa-IN")
    assert "nitroglycerin spray" in terms(hits)
    assert "under the tongue" not in terms(hits)  # "under your tongue" is not the glossary form
    spray = next(h for h in hits if h.term == "nitroglycerin spray")
    assert spray.translation == "ਨਾਈਟ੍ਰੋਗਲਿਸਰੀਨ ਸਪਰੇਅ"
    assert "ਜੀਭ" in spray.explanation  # explanation is in the listener's language


def test_glossary_alias_and_case_insensitive_idr_002(kb):
    assert terms(kb.glossary_hits("Your EKG was normal.", "en-CA", "fr-CA")) == ["ECG"]
    assert terms(kb.glossary_hits("You did not have a HEART ATTACK.", "en-CA", "fr-CA")) == ["heart attack"]


def test_glossary_whole_words_only_idr_002(kb):
    # "ASA" must not match inside another word.
    assert terms(kb.glossary_hits("Take it at Kasabian street.", "en-CA", "pa-IN")) == []


def test_glossary_fuzzy_match_tolerates_recognition_slips_idr_002(kb):
    assert "nitroglycerin spray" in terms(kb.glossary_hits("the nitroglycerine spray", "en-CA", "pa-IN"))


def test_glossary_from_patient_language_idr_002(kb):
    hits = kb.glossary_hits("ਕੀ ਮੈਨੂੰ ਵੀ ਦਿਲ ਦਾ ਦੌਰਾ ਪਵੇਗਾ?", "pa-IN", "en-CA")
    assert terms(hits) == ["ਦਿਲ ਦਾ ਦੌਰਾ"]
    assert hits[0].translation == "heart attack"
    assert hits[0].explanation.startswith("Damage to the heart")


def test_vector_search_is_filtered_by_language_and_kind_idr_002(kb):
    from kb.store import CONTENT_DIR, _sections

    punjabi_chunks = {f"{t}. {b}" for t, b in _sections((CONTENT_DIR / "tone" / "pa.md").read_text(encoding="utf-8"))}
    guidance = kb.tone_guidance("how to address an older patient respectfully", "pa-IN", k=10)
    assert guidance and set(guidance) <= punjabi_chunks  # never French or English guidance
    assert any("ਤੁਸੀਂ" in g for g in guidance)
    phrases = kb.empathy_phrases("worried about cost", "en-CA")
    assert phrases and all(p.isascii() for p in phrases)
    explainer = kb.condition_explainers("chest pain on effort", "fr-CA")
    assert explainer and "angine" in explainer[0]


def test_every_content_file_has_a_reviewer_field(kb):
    from pathlib import Path

    content = Path(__file__).parent.parent / "kb" / "content"
    for path in [*content.rglob("*.yaml"), *content.rglob("*.md")]:
        if path.name == "README.md":
            continue
        assert "reviewer:" in path.read_text(encoding="utf-8"), path.name
