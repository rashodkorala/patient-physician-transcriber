"""Per-turn translation graph.

    START -> retrieve -> translate -> verify -+-> done      (final or readback_required)
                            ^                 +-> block     (critical value still mismatched)
                            +-- retry once ---+-> escalate  (confidence or tone still failing: unsettled)

The graph reports a confidence or tone failure that survived the retry; it does not choose between unclear and
escalated. TurnPipeline.run does, from the speaker's unclear streak before the turn (ADR-003, amended
2026-11-12): a tone failure escalates at once, and a confidence failure is unclear until the speaker's third
consecutive one, which escalates with reason low_confidence.

translate also reads the speaker's emotion, certainty, manner, and medications, in the same call: the
latency mitigation ADR-004 names, applied 2026-10-25. Retrieval is local, so it adds no model call.
Manner (IDR-005) is read from the words alone, defaults to plain, and may enter the reporting frame as one
adverb (gentle, serious, urgent, or apologetic only) when the relayed words alone would lose it; the tone check
is told to expect that adverb. For a patient or companion turn, an emotion other than calm enters the frame as one
hedged phrase ("The patient says, sounding worried, ..."), written in the same call from the same emotion read, so
the phrase and the controller's label agree; the tone check is told to expect it too (IDR-006). The voice is
constant, so these words are the only way affect reaches the listener.

Outcome order when several apply: blocked, escalated, unclear, readback_required, final (CDR-002).

The interpreter relays each turn as a person between the two, in reported speech that names the
speaker ("Dr. Thomas is saying ..."), with every clinical detail kept exactly (MDD-004).

Demo night only (TDM-002): a presenter can arm a one-shot mismatch. On the first attempt of a turn whose
translation has a dose number, translate claims it; once claimed, that number is multiplied by 10 on every
attempt of the turn, and the normal verify node blocks it. The graph never sets the status itself.

@implements ADR-004: LangGraph for the per-turn translation graph
@implements ADR-002: Knowledge base feeding translation
@implements ADR-003: Human interpreter escalation on low confidence and high-risk moments
@implements CDR-002: Turn result schema
@implements MDD-004: Mediator voice: the interpreter speaks as a person between the parties, in reported speech
@implements TDM-002: Presenter mismatch control for the blocked-dose beat
@implements IDR-005: Manner vocabulary and voice delivery
@implements MDD-005: Trust across the barrier
@implements MDD-006: Affect in words
@implements IDR-006: Affect phrase in the reporting frame, and one constant voice delivery
@contract TurnResult
@see openspec/tdr/adr/adr-004-langgraph-turn-graph.md
@see openspec/tdr/mdd/mdd-004-mediator-voice.md
@see openspec/tdr/tdm/tdm-002-presenter-mismatch-control.md
@see openspec/tdr/idr/idr-005-manner-vocabulary-and-voice-delivery.md
@see openspec/tdr/idr/idr-006-affect-phrase-in-the-frame-and-constant-voice.md
"""

import operator
import re
import unicodedata
from collections.abc import Awaitable, Callable
from decimal import Decimal
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

import critical_values
from contracts import Certainty, CriticalValue, Emotion, GlossaryEntry, Manner, ToneTag, TurnResult
from kb.store import KnowledgeBase
from llm import Model

LOW_CONFIDENCE = 0.7
MAX_ATTEMPTS = 2
# ADR-003: a speaker's first and second consecutive unclear turns are unclear; the third escalates.
UNCLEAR_LIMIT = 2

LANGUAGE_NAMES = {
    "pa-IN": "Punjabi (Gurmukhi script)",
    "fr-CA": "Canadian French",
    "en-CA": "English",
    "si-LK": "Sinhala (Sinhala script)",
    "ta-LK": "Sri Lankan Tamil (Tamil script)",
}

# How the interpreter refers to someone whose name it does not know (MDD-004).
UNNAMED = {"physician": "your doctor", "patient": "the patient", "companion": "the patient's companion"}

Emit = Callable[[str], Awaitable[None]]
# TDM-002: asks the visit for the armed injection; True means it was armed and is now spent on this turn.
ClaimInjection = Callable[[], Awaitable[bool]]


# ---------- model outputs ----------


class Draft(BaseModel):
    # Read first, so the translation keeps what was read (one call instead of analyse then translate).
    emotion: Emotion
    certainty: Certainty
    # IDR-005: how the speaker said it, read from the words in the same call; plain unless clearly marked.
    manner: Manner
    medications: list[str]
    translation: str
    back_translation: str
    tone_tags: list[ToneTag]
    confidence: float


class ToneCheck(BaseModel):
    meaning_preserved: bool
    certainty_preserved: bool
    warmth_preserved: bool
    issue: str


# ---------- state ----------


class TurnState(TypedDict, total=False):
    turn_id: str
    speaker: str
    source: str
    target: str
    text: str
    speaker_name: str
    listener_name: str | None
    recognition_confidence: float
    glossary: list[GlossaryEntry]
    guidance: list[str]
    draft: Draft
    tone: ToneCheck
    critical: list[CriticalValue]
    confidence: float
    attempts: int
    failures: list[str]
    status: str
    escalation_reason: str | None
    # TDM-002: whether this turn carries the presenter's injected mismatch.
    injected: bool
    stages: Annotated[list[str], operator.add]


# ---------- prompts ----------

TRANSLATE_SYSTEM = """You are the interpreter in a medical consultation, sitting between a patient and a physician
who do not share a language. You are a person in the room relaying what each of them says to the other.
First read the speaker: emotion is how they feel, read from the words alone (calm is the default: pick another
value only when the words clearly carry it), certainty is how sure they sound, and medications lists every
medication name exactly as said (empty list if none).
Also read manner: how the speaker said it, from the words alone, as one of plain, warm, reassuring, gentle,
serious, urgent, apologetic, or encouraging. plain is the default: the words inform or ask without marked
feeling. Pick another value only when the words clearly carry it: warm when they are friendly and personal;
reassuring when they lower the listener's concern; gentle when they handle difficult content with care; serious
when they mark the content as grave; urgent when they call for action now; apologetic when they apologise or
acknowledge a fault; encouraging when they praise or encourage.
Then relay the utterance to the listener in the target language, in reported speech that names the speaker,
as a warm human interpreter would. For example, "Take this medicine two times a day after every meal" from the
physician becomes "Dr. Thomas is saying you should take this medicine 2 times a day after every meal".
Rules:
- Open the turn with one short frame naming the speaker as speaker_name gives it ("Dr. Thomas is saying",
  "your doctor is asking"), then speak to the listener as "you". Do not repeat the frame in every sentence.
  Write a name as it sounds, in the target language's script.
- The frame may name the manner, once, as one adverb in the target language's natural form ("Dr. Thomas is
  saying, gently, that ..."), only for gentle, serious, urgent, or apologetic, and only when the relayed words
  alone would lose it. Never for plain, warm, reassuring, or encouraging (the caption label carries those), never
  anywhere but the opening frame, and never in a way that changes an instruction, a certainty word, or a number.
- For a patient or companion turn only, the frame names the speaker's emotion when you read it as anything but
  calm, once, as one hedged phrase in the target language's natural form, so the physician hears how the speaker
  sounded: worried as "sounding worried", embarrassed as "sounding embarrassed", in_pain as "sounding as if in
  pain", relieved as "sounding relieved", and confused as "sounding confused" ("The patient says, sounding
  worried, that ..."; "The patient's companion says, sounding embarrassed, that ..."). A calm turn gets no
  phrase, and a physician turn never gets one. Never more than one phrase, never anywhere but the opening frame,
  and never in a way that changes an instruction, a certainty word, a number, or a medication.
- Use indirect speech in every sentence, not only the first: the speaker is never "I" or "we" anywhere in your
  relay; say "they", "the doctor", or the name instead, and never quote them after a colon. For example, "We
  found it early. I will start you on a new medicine today." from the physician becomes "Dr. Thomas is saying
  they found it early. They will start you on a new medicine today." and never "Dr. Thomas is saying we found
  it early. I will start you on a new medicine today."
- Never guess anyone's gender from their name. In English, use "they" for someone whose gender you were not
  told. In a language that needs a gender, repeat the name or role, or use a respectful form that avoids it.
- Keep everything that was said: every instruction, warning, condition, and question, and every count,
  including "one" or "a" before a medicine or a dose ("one aspirin", "one spray"). Plain everyday words are
  welcome, but never soften, strengthen, add, or drop anything.
- An instruction keeps its force: a plain instruction such as "call 911" becomes "you should call 911", never
  "you can call 911". Use "must" only when the speaker said "must" or "have to".
- Relay only. Never answer a question yourself, and never add advice, explanation, glosses, or reassurance the
  speaker did not give.
- Keep the speaker's emotion and level of certainty: never make news sound more or less serious than it was said.
- Keep warmth and reassurance, and use the respectful form of address the guidance describes.
- Use the approved glossary translations for any listed medical term.
- Write every number as digits and never change numbers, doses, units, frequencies, dates, or medication names.
- Translate meaning, not idioms.
Then translate your relay back into the source language as back_translation, keeping its reporting frame.
tone_tags describe the register of your relay. confidence (0 to 1) is how sure you are the meaning was kept."""

TONE_SYSTEM = """You check an interpretation in a medical consultation.
The interpreter relays each utterance in reported speech that names the speaker, for example "Dr. Thomas is
saying you should rest". That reporting frame, the change from first to third person, and a plain instruction
("rest") reported as "you should rest" are expected: never count them as a problem.
The frame may also carry one manner adverb (gently, reassuringly, seriously, urgently, apologetically, warmly, or
encouragingly) naming how the speaker spoke, as in "Dr. Thomas is saying, gently, that ...": any such adverb in
the frame is expected and never a problem, whichever manner it names.
For a patient or companion, the frame may instead carry one hedged phrase naming how the speaker sounded
(sounding worried, sounding embarrassed, sounding as if in pain, sounding relieved, or sounding confused), as in
"The patient says, sounding worried, that ...": one such phrase in the frame is expected and never a problem.
An adverb or phrase in the frame describes the speaker, not the news: a relay whose seriousness or certainty
changed still fails certainty_preserved, whatever the frame says.
Compare the original utterance with the back-translation of the interpretation.
meaning_preserved: every instruction, warning, condition, and question in the original is there, and nothing
was added, such as advice or an answer the speaker did not give.
certainty_preserved: the interpretation is neither more nor less certain or serious than the original. A small
word a fluent speaker adds for natural grammar, such as "still" in "still not better after 5 minutes", does not
change it.
warmth_preserved: reassurance, warmth, and respect in the original survive.
issue: one short sentence describing any problem, or an empty string."""


def tag(name: str, value: str) -> str:
    return f"<{name}>{value}</{name}>"


def _translate_user(state: TurnState) -> str:
    lines = [
        tag("speaker", state["speaker"]),
        tag("speaker_name", state["speaker_name"]),
        tag("listener_name", state.get("listener_name") or "unknown"),
        tag("source_language", LANGUAGE_NAMES[state["source"]]),
        tag("target_language", LANGUAGE_NAMES[state["target"]]),
        tag("target_code", state["target"]),
        tag("glossary", "; ".join(f"{g.term} = {g.translation}" for g in state.get("glossary", [])) or "none"),
        tag("guidance", "\n".join(state.get("guidance", [])) or "none"),
    ]
    if state.get("failures"):
        problems = []
        for v in state.get("critical", []):
            if not v.matched:
                problems.append(
                    f"Keep exactly: {v.source}"
                    if v.source
                    else f"Remove the number not in the original: {v.translated}"
                )
        if "tone" in state["failures"]:
            problems.append(f"Tone problem in the previous attempt: {state['tone'].issue}")
        if "confidence" in state["failures"]:
            problems.append("The previous attempt was uncertain; translate more literally.")
        lines.append(tag("fix_these", "\n".join(problems)))
    lines.append(tag("utterance", state["text"]))
    return "\n".join(lines)


def medication_forms(medications: list[str], glossary: list[GlossaryEntry]) -> dict[str, list[str]]:
    """Approved target-language forms of each medication, from glossary entries naming it.

    "nitroglycerin" is found under the entry "nitroglycerin spray", with and without its bracketed gloss.
    """
    forms: dict[str, list[str]] = {}
    for name in medications:
        key = name.casefold()
        for g in glossary:
            term = g.term.casefold()
            if key in term or term in key:
                forms.setdefault(name, []).extend(dict.fromkeys([g.translation, g.translation.split(" (")[0]]))
    return forms


# ---------- TDM-002: presenter mismatch control ----------

# A number written as digits and the unit after it, read as critical_values reads them in any language.
_NUMBER_WITH_UNIT = re.compile(rf"(?<![\w.,])(\d+(?:[.,]\d+)?)\s*({critical_values._UNIT})", re.IGNORECASE)


def multiply_first_dose(translation: str, language: str) -> str | None:
    """The translation with its first dose number multiplied by 10 (0.4 mg becomes 4 mg), or None without one.

    Only digits before a dose unit count, so the change is always one the critical value check reads as a
    different dose.
    """
    text = unicodedata.normalize("NFC", translation)
    # One character for one, so a position in the digit-mapped text is the same position in the text.
    prepared = text.translate(critical_values.DIGIT_MAP)
    for m in _NUMBER_WITH_UNIT.finditer(prepared):
        if critical_values._unit_key(m.group(2)) not in critical_values.DOSE_UNITS:
            continue
        raw = m.group(1)
        decimal_comma = "," in raw and (critical_values.lang_key(language) == "fr" or len(raw.split(",")[1]) != 3)
        value = Decimal(raw.replace(",", "." if decimal_comma else ""))
        tenfold = f"{(value * 10).normalize():f}"
        if decimal_comma:
            tenfold = tenfold.replace(".", ",")
        return text[: m.start(1)] + tenfold + text[m.end(1) :]
    return None


# ---------- ADR-003: unclear turns and the per-speaker streak ----------


def settle_failure(failures: list[str], unclear_streak: int) -> tuple[str, str | None]:
    """The outcome of a confidence or tone failure that survived the retry: (status, escalation reason).

    `unclear_streak` is the speaker's consecutive unclear turns before this one. A confidence failure is unclear
    while the streak is below UNCLEAR_LIMIT and escalates with low_confidence once it reaches it. A tone failure
    escalates at once with tone_failure, because repeating does not repair a meaning drift; when both fail, the
    confidence rule names the reason only once the streak has reached the limit (CDR-001, CDR-002).

    @implements ADR-003: Human interpreter escalation on low confidence and high-risk moments
    @implements CDR-002: Turn result schema
    """
    if "confidence" in failures and unclear_streak >= UNCLEAR_LIMIT:
        return "escalated", "low_confidence"
    if "tone" in failures:
        return "escalated", "tone_failure"
    return "unclear", None


def streak_after(status: str, reason: str | None, unclear_streak: int) -> int:
    """The speaker's unclear streak after a turn with this outcome (CDR-002 `unclearStreak`).

    unclear adds one; final resets to 0; the third unclear's low_confidence escalation resets to 0; blocked, a tone
    escalation, and a read-back still waiting leave it (a read-back resets it when the physician confirms).
    """
    if status == "unclear":
        return unclear_streak + 1
    if status == "final" or (status == "escalated" and reason == "low_confidence"):
        return 0
    return unclear_streak


# ---------- graph ----------


def build_turn_graph(model: Model, kb: KnowledgeBase):
    async def emit(config: RunnableConfig, stage: str) -> None:
        callback = (config.get("configurable") or {}).get("emit")
        if callback:
            await callback(stage)

    async def inject(state: TurnState, config: RunnableConfig, draft: Draft, attempts: int) -> tuple[Draft, bool]:
        """TDM-002: claim the armed injection on a first attempt that can carry it, then apply it on every attempt."""
        injected = state.get("injected", False)
        altered = multiply_first_dose(draft.translation, state["target"])
        claim: ClaimInjection | None = (config.get("configurable") or {}).get("claim_injection")
        if not injected and attempts == 1 and altered is not None and claim is not None:
            injected = await claim()
        if injected and altered is not None:
            draft = draft.model_copy(update={"translation": altered})
        return draft, injected

    async def retrieve(state: TurnState, config: RunnableConfig) -> dict:
        await emit(config, "checking_glossary")
        glossary = kb.glossary_hits(state["text"], state["source"], state["target"])
        guidance = kb.tone_guidance(state["text"], state["target"], k=3)
        guidance += kb.empathy_phrases(state["text"], state["target"], k=2)
        return {"glossary": glossary, "guidance": guidance, "stages": ["checking_glossary"]}

    async def translate(state: TurnState, config: RunnableConfig) -> dict:
        attempts = state.get("attempts", 0) + 1
        stage = "translating" if attempts == 1 else "retrying"
        await emit(config, stage)
        draft = await model.parse(
            purpose="translate", system=TRANSLATE_SYSTEM, user=_translate_user(state), schema=Draft
        )
        draft, injected = await inject(state, config, draft, attempts)
        return {"draft": draft, "attempts": attempts, "injected": injected, "stages": [stage]}

    async def verify(state: TurnState, config: RunnableConfig) -> dict:
        await emit(config, "verifying")
        draft = state["draft"]
        medications = draft.medications
        critical = critical_values.check(
            state["text"],
            state["source"],
            draft.translation,
            state["target"],
            draft.back_translation,
            medications,
            medication_forms(medications, state.get("glossary", [])),
        )
        tone = await model.parse(
            purpose="tone_check",
            system=TONE_SYSTEM,
            user="\n".join([tag("original", state["text"]), tag("back_translation", draft.back_translation)]),
            schema=ToneCheck,
        )
        recognition = state.get("recognition_confidence") or 1.0
        confidence = min(draft.confidence, recognition)
        failures = []
        if not all(v.matched for v in critical):
            failures.append("critical")
        if not (tone.meaning_preserved and tone.certainty_preserved and tone.warmth_preserved):
            failures.append("tone")
        if confidence < LOW_CONFIDENCE:
            failures.append("confidence")
        return {
            "critical": critical,
            "tone": tone,
            "confidence": confidence,
            "failures": failures,
            "stages": ["verifying"],
        }

    def route(state: TurnState) -> Literal["translate", "block", "escalate", "done"]:
        failures = state["failures"]
        if failures and state["attempts"] < MAX_ATTEMPTS:
            return "translate"
        if "critical" in failures:
            return "block"
        if "confidence" in failures or "tone" in failures:
            return "escalate"
        return "done"

    def block(state: TurnState) -> dict:
        return {"status": "blocked", "escalation_reason": None}

    def escalate(state: TurnState) -> dict:
        # Unsettled: TurnPipeline.run turns the surviving failures into unclear or escalated (settle_failure).
        return {"status": "unsettled", "escalation_reason": None}

    def done(state: TurnState) -> dict:
        readback = state["speaker"] == "physician" and bool(state["critical"])
        return {"status": "readback_required" if readback else "final", "escalation_reason": None}

    graph = StateGraph(TurnState)
    for name, node in [
        ("retrieve", retrieve),
        ("translate", translate),
        ("verify", verify),
        ("block", block),
        ("escalate", escalate),
        ("done", done),
    ]:
        graph.add_node(name, node)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "translate")
    graph.add_edge("translate", "verify")
    graph.add_conditional_edges("verify", route, ["translate", "block", "escalate", "done"])
    for terminal in ("block", "escalate", "done"):
        graph.add_edge(terminal, END)
    return graph.compile()


class TurnPipeline:
    """Runs the graph for one turn and assembles the CDR-002 TurnResult."""

    def __init__(self, model: Model, kb: KnowledgeBase) -> None:
        self.graph = build_turn_graph(model, kb)

    async def run(
        self,
        *,
        turn_id: str,
        speaker: str,
        source: str,
        target: str,
        text: str,
        recognition_confidence: float,
        unclear_streak: int = 0,
        physician_name: str | None = None,
        patient_name: str | None = None,
        emit: Emit | None = None,
        claim_injection: ClaimInjection | None = None,
    ) -> tuple[TurnResult, str | None]:
        # The listener is the patient when the physician speaks, and the physician otherwise.
        names = {"physician": physician_name, "patient": patient_name}
        listener = "patient" if speaker == "physician" else "physician"
        state: dict[str, Any] = await self.graph.ainvoke(
            {
                "turn_id": turn_id,
                "speaker": speaker,
                "source": source,
                "target": target,
                "text": text,
                "speaker_name": names.get(speaker) or UNNAMED[speaker],
                "listener_name": names[listener],
                "recognition_confidence": recognition_confidence,
                "attempts": 0,
                "injected": False,
                "stages": [],
            },
            config={"configurable": {"emit": emit, "claim_injection": claim_injection}},
        )
        status: str = state["status"]
        reason: str | None = state.get("escalation_reason")
        if status == "unsettled":
            # ADR-003: the speaker's streak before this turn decides between unclear and escalated.
            status, reason = settle_failure(state["failures"], unclear_streak)
        draft: Draft = state["draft"]
        # A glossary translation may carry a gloss in brackets the model can leave out.
        said = draft.translation.casefold()
        used = [g for g in state.get("glossary", []) if g.translation.split(" (")[0].casefold() in said]
        result = TurnResult(
            turn_id=turn_id,
            speaker=speaker,  # type: ignore[arg-type]
            source_language=source,  # type: ignore[arg-type]
            target_language=target,  # type: ignore[arg-type]
            source_text=text,
            translation=draft.translation,
            back_translation=draft.back_translation,
            tone_tags=draft.tone_tags,
            emotion=draft.emotion,
            certainty=draft.certainty,
            manner=draft.manner,
            glossary_used=used,
            critical_values=state["critical"],
            confidence=state["confidence"],
            status=status,  # type: ignore[arg-type]
            attempts=state["attempts"],
            unclear_streak=streak_after(status, reason, unclear_streak),
        )
        return result, reason
