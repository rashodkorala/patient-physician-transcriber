"""Private empathy nudges for the physician (demo spec: Empathy nudge).

Runs after a patient turn that sounds worried, embarrassed, in pain, or confused, and
suggests a ready phrase from the reviewed empathy bank. Sent to the controller only.

@implements ADR-002: Knowledge base feeding translation
@implements CDR-001: Visit WebSocket event contract
@contract ws:/ws/visit
"""

from pydantic import BaseModel

from contracts import Emotion, EmpathyNudge
from kb.store import KnowledgeBase
from llm import Model

NUDGE_EMOTIONS: frozenset[str] = frozenset({"worried", "embarrassed", "in_pain", "confused"})

SYSTEM = """You quietly coach a physician during a consultation across a language barrier.
The patient just said something showing an emotion. Suggest, in one short sentence, how the physician can acknowledge it.
Then give the phrase the physician should say. Prefer one of the candidate phrases, adapted to what the patient actually said.
The phrase must be in English, warm, plain, and free of medical jargon."""


class NudgeDraft(BaseModel):
    suggestion: str
    phrase: str


class EmpathyAdvisor:
    def __init__(self, model: Model, kb: KnowledgeBase) -> None:
        self.model = model
        self.kb = kb

    async def nudge(self, turn_id: str, emotion: Emotion, patient_text_en: str) -> EmpathyNudge | None:
        if emotion not in NUDGE_EMOTIONS:
            return None
        candidates = self.kb.empathy_phrases(f"{emotion}: {patient_text_en}", "en-CA", k=3)
        draft = await self.model.parse(
            purpose="empathy",
            system=SYSTEM,
            user="\n".join(
                [
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
