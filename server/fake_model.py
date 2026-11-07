"""Deterministic stand-in model for keyless runs and tests (EDR-002).

Translations are the source text tagged with the target language, with approved glossary terms
swapped in, so numbers and units survive and the safety checks behave as they would with a faithful translation.
Never used on stage: the server only selects it with TRANSLATOR=fake or without credentials.

@implements EDR-002: Testing: pytest with mocked LLM, speaker-rated tone set, latency check
"""

import re
from decimal import Decimal

from empathy import NudgeDraft
from graph.turn_graph import Draft, ToneCheck
from introduction import NameGuess
from llm import ScriptedModel

MEDICATIONS = ("aspirin", "nitroglycerin", "metformin", "amlodipine")
# Markers that let the browser check (web/e2e/week2.mjs) drive blocked and escalated turns.
MISMATCH_MARKER = "(test: mismatch)"  # first number times ten on every attempt, so the turn is blocked
TONE_MARKER = "(test: tone)"  # tone check fails on every attempt, so the turn is escalated
WORRY = re.compile(r"scared|worried|afraid|ਡਰ|ਫ਼ਿਕਰ|peur|inquiet", re.IGNORECASE)


def field(user: str, name: str) -> str:
    match = re.search(rf"<{name}>(.*?)</{name}>", user, flags=re.S)
    return match.group(1).strip() if match else ""


def glossary_terms(user: str) -> list[tuple[str, str]]:
    """Pairs from the prompt's "term = translation; ..." glossary field, longest term first."""
    raw = field(user, "glossary")
    if raw in ("", "none"):
        return []
    pairs = [(term, approved) for term, _, approved in (p.partition(" = ") for p in raw.split("; ")) if approved]
    return sorted(pairs, key=lambda pair: -len(pair[0]))


def translate(user: str) -> Draft:
    """Keeps the utterance, swapping in approved glossary terms as a faithful interpreter would."""
    text = field(user, "utterance")
    translated = text
    for term, approved in glossary_terms(user):
        translated = re.sub(rf"\b{re.escape(term)}\b", approved, translated, flags=re.IGNORECASE)
    if MISMATCH_MARKER in text:
        translated = re.sub(
            r"\d+(?:\.\d+)?", lambda m: f"{(Decimal(m.group()) * 10).normalize():f}", translated, count=1
        )
    tone = "reassuring" if re.search(r"reassur|not have|unlikely", text, re.IGNORECASE) else "respectful"
    return Draft(
        emotion="worried" if WORRY.search(text) else "calm",
        certainty="high",
        medications=[m for m in MEDICATIONS if m in text.lower()],
        translation=f"[{field(user, 'target_code')}] {translated}",
        back_translation=text,
        tone_tags=[tone],
        confidence=0.95,
    )


def tone_check(user: str) -> ToneCheck:
    if TONE_MARKER in field(user, "original"):
        return ToneCheck(
            meaning_preserved=True,
            certainty_preserved=False,
            warmth_preserved=True,
            issue="Sounds more certain than the speaker.",
        )
    return ToneCheck(meaning_preserved=True, certainty_preserved=True, warmth_preserved=True, issue="")


def empathy(user: str) -> NudgeDraft:
    candidates = [c for c in field(user, "candidates").splitlines() if c.strip()]
    return NudgeDraft(
        suggestion="Acknowledge the patient's worry before moving on.",
        phrase=candidates[0] if candidates else "I can see this is worrying you.",
    )


NAME_LEAD = re.compile(r"^(?:my name is|i am|i'm|it's|call me|this is)\s+", re.IGNORECASE)


def name_extract(user: str) -> NameGuess:
    """The reply with a leading "my name is" removed; enough for typed and scripted replies."""
    return NameGuess(name=NAME_LEAD.sub("", field(user, "reply")).strip(" .!"))


def fake_model() -> ScriptedModel:
    return ScriptedModel(
        {"translate": translate, "tone_check": tone_check, "empathy": empathy, "name_extract": name_extract}
    )
