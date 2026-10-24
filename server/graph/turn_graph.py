"""Per-turn translation graph.

    START -+-> analyse --+
           +-> retrieve -+-> translate -> verify -+-> done      (final or readback_required)
                              ^                   +-> block     (critical value still mismatched)
                              +---- retry once ---+-> escalate  (confidence or tone still failing)

Outcome order when several apply: blocked, escalated, readback_required, final (CDR-002).

@implements ADR-004: LangGraph for the per-turn translation graph
@implements ADR-002: Knowledge base feeding translation
@implements ADR-003: Human interpreter escalation on low confidence and high-risk moments
@implements CDR-002: Turn result schema
@contract TurnResult
@see openspec/tdr/adr/adr-004-langgraph-turn-graph.md
"""

import operator
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

import critical_values
from contracts import Certainty, CriticalValue, Emotion, GlossaryEntry, ToneTag, TurnResult
from kb.store import KnowledgeBase
from llm import Model

LOW_CONFIDENCE = 0.7
MAX_ATTEMPTS = 2

LANGUAGE_NAMES = {"pa-IN": "Punjabi (Gurmukhi script)", "fr-CA": "Canadian French", "en-CA": "English"}

Emit = Callable[[str], Awaitable[None]]


# ---------- model outputs ----------


class Analysis(BaseModel):
    emotion: Emotion
    certainty: Certainty
    intent: str
    medications: list[str]


class Draft(BaseModel):
    translation: str
    back_translation: str
    tone_tags: list[ToneTag]
    confidence: float


class ToneCheck(BaseModel):
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
    recognition_confidence: float
    analysis: Analysis
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
    stages: Annotated[list[str], operator.add]


# ---------- prompts ----------

ANALYSE_SYSTEM = """You analyse one utterance from a medical consultation before it is interpreted.
Report the speaker's emotion and how certain the speaker sounds, and the intent in a few words.
List every medication name exactly as said (empty list if none)."""

TRANSLATE_SYSTEM = """You interpret a medical consultation between a patient and a physician who do not share a language.
Translate the utterance faithfully into the target language for the listener.
Rules:
- Keep the speaker's level of certainty: never make news sound more or less serious than it was said.
- Keep warmth and reassurance, and use the respectful form of address the guidance describes.
- Use the approved glossary translations for any listed medical term.
- Write every number as digits and never change numbers, doses, units, frequencies, dates, or medication names.
- Translate meaning, not idioms.
Then translate your translation back into the source language as back_translation.
tone_tags describe the register of your translation. confidence (0 to 1) is how sure you are the meaning was kept."""

TONE_SYSTEM = """You check an interpretation in a medical consultation.
Compare the original utterance with the back-translation of the interpretation.
certainty_preserved: the interpretation is neither more nor less certain or serious than the original.
warmth_preserved: reassurance, warmth, and respect in the original survive.
issue: one short sentence describing any problem, or an empty string."""


def tag(name: str, value: str) -> str:
    return f"<{name}>{value}</{name}>"


def _translate_user(state: TurnState) -> str:
    analysis = state["analysis"]
    lines = [
        tag("speaker", state["speaker"]),
        tag("source_language", LANGUAGE_NAMES[state["source"]]),
        tag("target_language", LANGUAGE_NAMES[state["target"]]),
        tag("target_code", state["target"]),
        tag("speaker_emotion", analysis.emotion),
        tag("speaker_certainty", analysis.certainty),
        tag("intent", analysis.intent),
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


# ---------- graph ----------


def build_turn_graph(model: Model, kb: KnowledgeBase):
    async def emit(config: RunnableConfig, stage: str) -> None:
        callback = (config.get("configurable") or {}).get("emit")
        if callback:
            await callback(stage)

    async def analyse(state: TurnState, config: RunnableConfig) -> dict:
        await emit(config, "analysing")
        analysis = await model.parse(
            purpose="analyse",
            system=ANALYSE_SYSTEM,
            user="\n".join([tag("speaker", state["speaker"]), tag("utterance", state["text"])]),
            schema=Analysis,
        )
        return {"analysis": analysis, "stages": ["analysing"]}

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
        return {"draft": draft, "attempts": attempts, "stages": [stage]}

    async def verify(state: TurnState, config: RunnableConfig) -> dict:
        await emit(config, "verifying")
        draft = state["draft"]
        medications = state["analysis"].medications
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
        if not (tone.certainty_preserved and tone.warmth_preserved):
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
        reason = "low_confidence" if "confidence" in state["failures"] else "tone_failure"
        return {"status": "escalated", "escalation_reason": reason}

    def done(state: TurnState) -> dict:
        readback = state["speaker"] == "physician" and bool(state["critical"])
        return {"status": "readback_required" if readback else "final", "escalation_reason": None}

    graph = StateGraph(TurnState)
    for name, node in [
        ("analyse", analyse),
        ("retrieve", retrieve),
        ("translate", translate),
        ("verify", verify),
        ("block", block),
        ("escalate", escalate),
        ("done", done),
    ]:
        graph.add_node(name, node)
    graph.add_edge(START, "analyse")
    graph.add_edge(START, "retrieve")
    graph.add_edge(["analyse", "retrieve"], "translate")
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
        emit: Emit | None = None,
    ) -> tuple[TurnResult, str | None]:
        state: dict[str, Any] = await self.graph.ainvoke(
            {
                "turn_id": turn_id,
                "speaker": speaker,
                "source": source,
                "target": target,
                "text": text,
                "recognition_confidence": recognition_confidence,
                "attempts": 0,
                "stages": [],
            },
            config={"configurable": {"emit": emit}},
        )
        draft: Draft = state["draft"]
        analysis: Analysis = state["analysis"]
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
            emotion=analysis.emotion,
            certainty=analysis.certainty,
            glossary_used=used,
            critical_values=state["critical"],
            confidence=state["confidence"],
            status=state["status"],
            attempts=state["attempts"],
        )
        return result, state.get("escalation_reason")
