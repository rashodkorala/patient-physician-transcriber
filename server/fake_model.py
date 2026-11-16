"""Deterministic stand-in model for keyless runs and tests (EDR-002).

Translations are the source text tagged with the target language, with approved glossary terms
swapped in, so numbers and units survive and the safety checks behave as they would with a faithful translation.
Never used on stage: the server only selects it with TRANSLATOR=fake or without credentials.

A patient or companion turn the fake reads as anything but calm opens with a reporting frame carrying one hedged
affect phrase ("The patient says, sounding worried, ..."), as the live model is asked to (IDR-006); every other
turn has no frame.

@implements EDR-002: Testing: pytest with mocked LLM, speaker-rated tone set, latency check
@implements IDR-006: Affect phrase in the reporting frame, and one constant voice delivery
@implements ADR-011: Explain-back, note, and summary: frozen sources, model proposes, code checks provenance and values
"""

import json
import re
from decimal import Decimal

from chains.checks import DraftSource
from chains.explain_back import CodeItemView, ExplainBackDraft
from chains.note import DraftSection, DraftSentence, NoteDraft
from chains.summary import DraftSummarySentence, SummaryDraft
from graph.turn_graph import LANGUAGE_NAMES, Draft, ToneCheck
from introduction import NameGuess
from llm import ScriptedModel
from trust import CultureCueDraft, NudgeDraft

MEDICATIONS = ("aspirin", "nitroglycerin", "metformin", "amlodipine")
# Markers that let the browser check (web/e2e/week2.mjs) drive blocked, unclear, and escalated turns.
MISMATCH_MARKER = "(test: mismatch)"  # first number times ten on every attempt, so the turn is blocked
TONE_MARKER = "(test: tone)"  # tone check fails on every attempt, so the turn is escalated at once
# ADR-003: confidence 0.3 on every attempt, so the turn is unclear, and the speaker's third in a row escalates.
UNCLEAR_MARKER = "(test: unclear)"
UNCLEAR_CONFIDENCE = 0.3
WORRY = re.compile(r"scared|worried|afraid|ਡਰ|ਫ਼ਿਕਰ|peur|inquiet", re.IGNORECASE)
RELIEF = re.compile(r"relief|relieved|better now|thank you|ਸ਼ੁਕਰ|soulag", re.IGNORECASE)
EMBARRASSED = re.compile(r"embarrass|ashamed|ਸ਼ਰਮ|gêné|honte", re.IGNORECASE)
# IDR-006: the hedged phrase for each emotion but calm, as the translate prompt suggests it in English.
AFFECT_PHRASES = {
    "worried": "sounding worried",
    "embarrassed": "sounding embarrassed",
    "in_pain": "sounding as if in pain",
    "relieved": "sounding relieved",
    "confused": "sounding confused",
}
# IDR-005: the manner the fake reads from a physician's words; plain unless the words clearly carry one.
REASSURING = re.compile(r"reassur|not have|unlikely|\bearly\b|nothing to worry", re.IGNORECASE)
APOLOGETIC = re.compile(r"\bsorry\b|apologi", re.IGNORECASE)
URGENT = re.compile(r"call 911|right away|immediately", re.IGNORECASE)
# MDD-005: topics the tone guides mark as sensitive; the fake cues on the words, the live model on the guidance.
SENSITIVE = re.compile(r"alcohol|drink|smok|sexual|mental health|depress|family conflict", re.IGNORECASE)
CULTURE_CUE = (
    "This question may carry shame in the patient's culture. Say why it matters for their care, "
    "and ask without judgement."
)


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
    physician = field(user, "speaker") == "physician"
    emotion = emotion_of(text)
    frame = "" if physician else affect_frame(field(user, "speaker_name"), emotion)
    return Draft(
        emotion=emotion,
        certainty="high",
        manner=manner_of(text) if physician else "plain",
        medications=[m for m in MEDICATIONS if m in text.lower()],
        translation=f"[{field(user, 'target_code')}] {frame}{translated}",
        back_translation=f"{frame}{text}",
        tone_tags=[tone],
        confidence=UNCLEAR_CONFIDENCE if UNCLEAR_MARKER in text else 0.95,
    )


def emotion_of(text: str) -> str:
    if WORRY.search(text):
        return "worried"
    if EMBARRASSED.search(text):
        return "embarrassed"
    if RELIEF.search(text):
        return "relieved"
    return "calm"


def affect_frame(speaker_name: str, emotion: str) -> str:
    """The opening frame with its one affect phrase for a patient or companion turn, or nothing when calm (IDR-006)."""
    phrase = AFFECT_PHRASES.get(emotion)
    if not phrase:
        return ""
    return f"{speaker_name[:1].upper()}{speaker_name[1:]} says, {phrase}, "


def manner_of(text: str) -> str:
    """A physician's manner read from marked words only; everything else is plain (IDR-005)."""
    if URGENT.search(text):
        return "urgent"
    if APOLOGETIC.search(text):
        return "apologetic"
    if REASSURING.search(text):
        return "reassuring"
    return "plain"


def tone_check(user: str) -> ToneCheck:
    if TONE_MARKER in field(user, "original"):
        return ToneCheck(
            meaning_preserved=True,
            certainty_preserved=False,
            warmth_preserved=True,
            issue="Sounds more certain than the speaker.",
        )
    return ToneCheck(meaning_preserved=True, certainty_preserved=True, warmth_preserved=True, issue="")


def trust(user: str) -> NudgeDraft | CultureCueDraft:
    """The trust advisor's two questions (MDD-005): a nudge for a patient turn, a culture cue for a physician's."""
    if field(user, "speaker") == "physician":
        return CultureCueDraft(cue=CULTURE_CUE if SENSITIVE.search(field(user, "physician_said")) else None)
    candidates = [c for c in field(user, "candidates").splitlines() if c.strip()]
    return NudgeDraft(
        suggestion="Acknowledge the patient's worry before moving on.",
        phrase=candidates[0] if candidates else "I can see this is worrying you.",
    )


NAME_LEAD = re.compile(r"^(?:my name is|i am|i'm|it's|call me|this is)\s+", re.IGNORECASE)


def name_extract(user: str) -> NameGuess:
    """The reply with a leading "my name is" removed; enough for typed and scripted replies."""
    return NameGuess(name=NAME_LEAD.sub("", field(user, "reply")).strip(" .!"))


# ---------- grounded generation (ADR-011) ----------
# Faithful stand-ins: each restates the sources word for word, so the code checks pass. Tests that need a wrong
# or lenient model give ScriptedModel their own handler.

LANGUAGE_CODES = {name: code for code, name in LANGUAGE_NAMES.items()}


def _sources(user: str, name: str = "sources") -> list[dict]:
    raw = field(user, name)
    return json.loads(raw) if raw else []


def _ref(source: dict) -> DraftSource:
    return DraftSource(kind=source["kind"], id=source["id"], version=source["version"])


def _in_language(source: dict, language: str) -> str | None:
    if source["kind"] == "interpreter_line":
        return next((line["text"] for line in source["lines"] if line["language"] == language), None)
    if source["sourceLanguage"] == language:
        return source["sourceText"]
    if source["targetLanguage"] == language:
        return source["spokenTranslation"]
    return None


def clinical_note(user: str) -> NoteDraft:
    """One sentence per spoken turn, in its English words, tagged with its speaker: patient turns under History,
    physician turns under Plan."""
    sections: dict[str, list[DraftSentence]] = {}
    for source in _sources(user):
        text = _in_language(source, "en-CA")
        if source["kind"] != "turn" or not text:
            continue
        heading = "Plan" if source["speaker"] == "physician" else "History"
        tag = f"{source['speaker']}_stated"
        sections.setdefault(heading, []).append(DraftSentence(text=text, tag=tag, sources=[_ref(source)]))
    return NoteDraft(sections=[DraftSection(heading=h, sentences=s) for h, s in sections.items()])


def patient_summary(user: str) -> SummaryDraft:
    """Each spoken turn as the patient heard or said it, one sentence per turn."""
    language = LANGUAGE_CODES.get(field(user, "patient_language"), field(user, "patient_language"))
    sentences = [
        DraftSummarySentence(text=text, sources=[_ref(source)])
        for source in _sources(user)
        if source["kind"] == "turn" and (text := _in_language(source, language))
    ]
    return SummaryDraft(sentences=sentences)


def explain_back(user: str) -> ExplainBackDraft:
    """A lenient reader: no instructions of its own, and every code item judged matched (code discards that)."""
    views = [CodeItemView(item_id=item["itemId"], outcome="matched") for item in _sources(user, "code_items")]
    return ExplainBackDraft(items=[], code_item_views=views)


def fake_model() -> ScriptedModel:
    return ScriptedModel(
        {
            "translate": translate,
            "tone_check": tone_check,
            "trust": trust,
            "name_extract": name_extract,
            "clinical_note": clinical_note,
            "patient_summary": patient_summary,
            "explain_back": explain_back,
        }
    )
