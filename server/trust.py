"""The trust advisor: private help for the physician on how the visit is landing (MDD-005).

After every spoken turn, one background call on the tone model, never on the turn's critical path:

- a patient turn that sounds worried, embarrassed, in pain, or confused gets the empathy nudge as before (demo
  spec: Empathy nudge), a ready phrase from the reviewed empathy bank;
- a physician turn gets a culture cue when the retrieved tone and culture guidance for the patient's language
  marks the topic sensitive, and nothing otherwise;
- a companion turn gets neither.

Whether a reassurance landed is decided by code from the visit's spoken history (CDR-008), never by the model.
Everything here reaches the controller only, and nothing is ever written into the note, the summary, or the record.

@implements MDD-005: Trust across the barrier
@implements CDR-008: Patient signals, manner, trust updates, companion turns, and the closing check on the visit channel
@implements ADR-002: Knowledge base feeding translation
@implements CDR-001: Visit WebSocket event contract
@contract ws:/ws/visit
@see openspec/tdr/mdd/mdd-005-trust-across-the-barrier.md
@see openspec/tdr/cdr/cdr-008-patient-voice-manner-and-trust-events.md
"""

from collections.abc import Iterable
from dataclasses import dataclass

from pydantic import BaseModel

from contracts import TRUST_CUE_MAX, Emotion, EmpathyNudge, PatientSignal, TrustCue
from graph.turn_graph import LANGUAGE_NAMES
from kb.store import KnowledgeBase
from llm import Model

# The purpose every advisor call carries; llm.py runs it on the tone model (ADR-006).
PURPOSE = "trust"

# The emotions that get an empathy nudge, and the CDR-008 reassurance rule's worry: an earlier patient turn with
# one of these emotions ...
NUDGE_EMOTIONS: frozenset[str] = frozenset({"worried", "embarrassed", "in_pain", "confused"})
# ... a physician turn between them with one of these manners ...
REASSURING_MANNERS: frozenset[str] = frozenset({"reassuring", "warm", "gentle", "encouraging"})
# ... and this turn sounds like one of these: landed.
LANDED_EMOTIONS: frozenset[str] = frozenset({"calm", "relieved"})

# Fixed English suggestions for each patient signal, sent with the signal's trust update (CDR-008).
UNDERSTANDING_CUES: dict[str, str] = {
    "not_understood": "Say it another way, in shorter sentences, one instruction at a time.",
    "slower": "Slow down and pause between sentences.",
    "repeat": "The last translation is being replayed for the patient.",
}

NUDGE_SYSTEM = """You quietly coach a physician during a consultation across a language barrier.
The patient just said something showing an emotion. Suggest, in one short sentence, how the physician can acknowledge it.
Then give the phrase the physician should say. Prefer one of the candidate phrases, adapted to what the patient actually said.
The phrase must be in English, warm, plain, and free of medical jargon."""

# The culture cue's length asked of the model; _cue still cuts anything longer than TRUST_CUE_MAX cleanly.
CULTURE_CUE_ASK = 160

CULTURE_SYSTEM = f"""You quietly coach a physician during a consultation across a language barrier.
You are given what the physician just said and the tone and culture guidance for the patient's language.
If the physician's words touch a topic that guidance marks as sensitive or shaming in the patient's culture, write one
cue for the physician only: in English, one or two short sentences, at most {CULTURE_CUE_ASK} characters in all,
naming the sensitivity and suggesting how to ask, for example by saying why the question matters for the patient's care.
The cue is about cultural sensitivity and how to ask, never clinical advice, never what the tests or results show, and
never a change to a clinical fact, a dose, or an instruction. Never write anything for the patient to see.
Never guess anyone's gender from a name; refer to the patient as "they" or as "the patient".
If nothing in the guidance applies to these words, return null for cue. Everyday clinical questions get no cue."""


class NudgeDraft(BaseModel):
    suggestion: str
    phrase: str


class CultureCueDraft(BaseModel):
    cue: str | None


@dataclass(frozen=True)
class SpokenTurn:
    """What the reassurance rule needs of an earlier spoken turn."""

    speaker: str
    emotion: str
    manner: str


def reassurance_landed(history: Iterable[SpokenTurn], speaker: str, emotion: str) -> bool | None:
    """CDR-008: set only on a patient turn that follows (a) an earlier patient turn whose emotion was worried,
    embarrassed, in_pain, or confused and (b) a physician turn between them whose manner was reassuring, warm,
    gentle, or encouraging: true when this turn sounds calm or relieved, otherwise false; null in every other case.

    `history` is the visit's spoken turns before this one, in the order they were spoken. A companion turn never
    carries the mark and never counts as the patient's worry.

    Once the reassurance has landed (a patient turn after it sounded calm or relieved), the worry and the
    reassurance are spent: later turns carry null until a new worry and a new reassuring turn after it. A patient
    turn that is still worried after the reassurance keeps the pair armed until it lands.
    """
    if speaker != "patient":
        return None
    worried, reassured = False, False
    for turn in history:
        if turn.speaker == "patient":
            if reassured and turn.emotion in LANDED_EMOTIONS:
                worried, reassured = False, False
            elif turn.emotion in NUDGE_EMOTIONS:
                worried = True
        elif turn.speaker == "physician" and worried and turn.manner in REASSURING_MANNERS:
            reassured = True
    if not reassured:
        return None
    return emotion in LANDED_EMOTIONS


def understanding_cue(signal: PatientSignal) -> TrustCue:
    return TrustCue(kind="understanding", text=UNDERSTANDING_CUES[signal])


def clip(text: str, limit: int = TRUST_CUE_MAX) -> str:
    """`text` within `limit` characters, never cut mid-word: at the last sentence end that fits, or failing that at
    the last word boundary, with no trailing space. Only a single word longer than the limit is cut inside it."""
    if len(text) <= limit:
        return text
    head = text[: limit + 1]  # one more, so a sentence or word that ends exactly at the limit still counts
    sentence_end = max(head.rfind(mark) for mark in (". ", "! ", "? "))
    if sentence_end > 0:
        return head[: sentence_end + 1]
    word_end = head.rfind(" ")
    if word_end > 0:
        return head[:word_end].rstrip(" ,;:-")
    return text[:limit]


def _cue(kind: str, text: str | None) -> TrustCue | None:
    """A cue within the contract's bounds, or None when the model gave nothing usable."""
    text = " ".join((text or "").split())
    if not text:
        return None
    return TrustCue(kind=kind, text=clip(text))  # type: ignore[arg-type]


class TrustAdvisor:
    def __init__(self, model: Model, kb: KnowledgeBase) -> None:
        self.model = model
        self.kb = kb

    async def nudge(self, turn_id: str, emotion: Emotion, patient_text_en: str) -> EmpathyNudge | None:
        """The empathy nudge for a patient turn, or None when the emotion asks for none."""
        if emotion not in NUDGE_EMOTIONS:
            return None
        candidates = self.kb.empathy_phrases(f"{emotion}: {patient_text_en}", "en-CA", k=3)
        draft = await self.model.parse(
            purpose=PURPOSE,
            system=NUDGE_SYSTEM,
            user="\n".join(
                [
                    "<speaker>patient</speaker>",
                    f"<emotion>{emotion}</emotion>",
                    f"<patient_said>{patient_text_en}</patient_said>",
                    "<candidates>" + "\n".join(candidates) + "</candidates>",
                ]
            ),
            schema=NudgeDraft,
        )
        return EmpathyNudge(
            turn_id=turn_id, emotion=emotion, suggestion=draft.suggestion, phrase=draft.phrase, phrase_language="en-CA"
        )

    async def culture_cue(self, physician_text: str, patient_language: str) -> TrustCue | None:
        """A culture cue for a physician turn, from the patient language's tone and culture guidance, or None."""
        guidance = self.kb.tone_guidance(physician_text, patient_language, k=3)
        draft = await self.model.parse(
            purpose=PURPOSE,
            system=CULTURE_SYSTEM,
            user="\n".join(
                [
                    "<speaker>physician</speaker>",
                    f"<patient_language>{LANGUAGE_NAMES.get(patient_language, patient_language)}</patient_language>",
                    f"<physician_said>{physician_text}</physician_said>",
                    "<guidance>" + "\n".join(guidance) + "</guidance>",
                ]
            ),
            schema=CultureCueDraft,
        )
        return _cue("culture", draft.cue)


def nudge_cue(nudge: EmpathyNudge) -> TrustCue | None:
    """The nudge's suggestion as the patient turn's trust cue, so the trust view carries it inline."""
    return _cue("reassurance", nudge.suggestion)
