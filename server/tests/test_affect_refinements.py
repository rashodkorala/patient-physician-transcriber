"""MDD-006 decision 8, the two affect phrase refinements after the live run (affect-in-words group 10).

(a) When the speaker's own words already state the feeling, the relay carries no affect phrase: a phrase beside
those words doubles it (T1, T16, T18, and P1 in `docs/voice-test.md`, "Affect in words run, 16 November 2026").
(b) "sounding frightened" joins the phrases, for a patient or companion whose emotion is fear (T3 was relayed as
"sounding worried", which the physician hears as weaker).
"""

import asyncio
import re
from typing import get_args

import pytest

import fake_model
from contracts import Emotion, to_caption
from fake_model import field
from graph.turn_graph import TONE_SYSTEM, TRANSLATE_SYSTEM, Draft, ToneCheck, TurnPipeline
from kb.embeddings import HashingEmbedder
from kb.store import KnowledgeBase
from llm import ScriptedModel

# English feeling words that state a feeling in the speaker's own words (enough for these scripted turns).
FEELING_WORDS = re.compile(
    r"\b(worried|worry|anxious|scared|afraid|frightened|terrified|embarrassed|ashamed|relieved|at ease|confused)\b",
    re.IGNORECASE,
)


@pytest.fixture(scope="module")
def kb():
    return KnowledgeBase(HashingEmbedder())


def relay(emotion: str, phrase: str, body: str):
    """A translate handler writing `body` after the patient's frame, with `phrase` in the frame if it is given.

    Its back-translation is the English relay followed by the original, so a scripted tone check can read it and the
    back-translation check (task 9.3) still sees the source script."""

    def handler(user):
        frame = f"The patient says, {phrase}, " if phrase else "The patient says "
        draft = fake_model.translate(user)
        return Draft(
            **{
                **draft.model_dump(),
                "emotion": emotion,
                "translation": f"{frame}{body}",
                # The judge reads English; the original's own words keep it a back-translation in the source script.
                "back_translation": f"{frame}{body} ({field(user, 'utterance')})",
                "affect_phrase": phrase,
            }
        )

    return handler


def doubling_judge(user):
    """A tone check that follows TONE_SYSTEM on decision 8 (a): a phrase beside the speaker's own words for the
    feeling doubles it and fails; the speaker's own feeling words alone are content and pass."""
    added = field(user, "interpreter_affect_phrase")
    back = field(user, "back_translation")
    rest = back.replace(added, "") if added != "none" else back
    doubled = added != "none" and bool(FEELING_WORDS.search(rest))
    return ToneCheck(
        issue="The phrase doubles the feeling the speaker's own words state." if doubled else "",
        meaning_preserved=not doubled,
        certainty_preserved=True,
        warmth_preserved=True,
    )


def run(kb, translate, text, tone_check=doubling_judge, speaker="patient"):
    m = ScriptedModel({"translate": translate, "tone_check": tone_check, "trust": fake_model.trust})
    result, reason = asyncio.run(
        TurnPipeline(m, kb).run(
            turn_id="t1", speaker=speaker, source="ta-LK", target="en-CA", text=text, recognition_confidence=1.0
        )
    )
    return result, reason, m


# ---------- (a) no phrase when the speaker's own words state the feeling ----------

T1_SAID = "டாக்டர், எனக்கு மிகவும் கவலையாக இருக்கிறது. இந்த நெஞ்சு வலி இதயப் பிரச்சினையாக இருக்குமோ என்று யோசித்துக்கொண்டே இருக்கிறேன்."
T1_BODY = "that they are very worried. They keep wondering whether this chest pain could be a heart problem."


def test_translate_prompt_leaves_the_phrase_out_when_the_words_state_the_feeling_mdd_006():
    translate = " ".join(TRANSLATE_SYSTEM.split())
    assert (
        'When the speaker\'s own words already say how they feel ("I am very worried", "I am scared"), relay those '
        "words and add no phrase: the words carry the feeling, and a phrase beside them doubles it" in translate
    )
    assert "The phrase is only for a feeling you read that the words do not state" in translate


def test_tone_check_fails_a_phrase_that_doubles_the_speakers_own_words_mdd_006():
    tone = " ".join(TONE_SYSTEM.split())
    assert (
        "When the original already states the feeling in the speaker's own words, the frame carries no phrase: a "
        "phrase beside those words doubles the feeling and fails meaning_preserved" in tone
    )


def test_doubled_relay_is_not_final_and_the_relay_without_the_phrase_is_mdd_006(kb):
    """T1, T16, T18: "sounding worried, that they are very worried" doubles the feeling; the words alone carry it."""
    doubled, reason, _ = run(kb, relay("worried", "sounding worried", T1_BODY), T1_SAID)
    assert doubled.status == "escalated" and reason == "tone_failure" and doubled.attempts == 2
    words_only, reason, m = run(kb, relay("worried", "", T1_BODY), T1_SAID)
    assert words_only.status == "final" and reason is None and words_only.attempts == 1
    assert words_only.emotion == "worried" and words_only.affect_phrase == ""  # the label still reads worried
    assert field(next(u for p, u in m.calls if p == "tone_check"), "interpreter_affect_phrase") == "none"


def test_phrase_stays_when_the_words_do_not_state_the_feeling_mdd_006(kb):
    """Decision 2 stands otherwise: a feeling read but not stated in words gets its one phrase."""
    body = "that their mother died of this same illness, and they are asking whether they will die like that too."
    result, reason, _ = run(kb, relay("worried", "sounding worried", body), "என் அம்மா இதே நோயால் இறந்துபோனார்.")
    assert result.status == "final" and reason is None and result.affect_phrase == "sounding worried"


# ---------- (b) "sounding frightened" for fear ----------

T3_SAID = "என் அம்மா இதே நோயால் இறந்துபோனார். நானும் அப்படி இறந்துவிடுவேனா?"
T3_BODY = "that their mother died of this same illness. They are asking whether they will die like that too."


def test_frightened_is_an_emotion_with_its_own_phrase_mdd_006():
    assert "frightened" in get_args(Emotion)
    translate = " ".join(TRANSLATE_SYSTEM.split())
    assert 'frightened as "sounding frightened"' in translate
    assert "frightened when they are afraid or scared" in translate
    tone = " ".join(TONE_SYSTEM.split())
    assert "sounding frightened" in tone


def test_frightened_patient_turn_carries_sounding_frightened_and_the_label_stays_private_mdd_006(kb):
    """T3: fear is relayed as fear, not weakened to worry; the label reaches the controller only (CDR-008)."""
    result, reason, _ = run(kb, relay("frightened", "sounding frightened", T3_BODY), T3_SAID)
    assert result.status == "final" and reason is None and result.attempts == 1
    assert result.emotion == "frightened" and result.affect_phrase == "sounding frightened"
    assert result.translation.startswith("The patient says, sounding frightened, ")
    assert result.wire()["emotion"] == "frightened"  # turn.analysis, controller only
    caption = to_caption(result).wire()
    assert "emotion" not in caption and caption.get("manner") is None


def test_frightened_phrase_is_never_for_a_physician_mdd_006(kb):
    result, reason, _ = run(
        kb,
        relay("frightened", "sounding frightened", "that the results are back."),
        "The results are back.",
        tone_check=fake_model.tone_check,
        speaker="physician",
    )
    assert result.status == "escalated" and reason == "tone_failure"


# ---------- a pronoun in a reported back-translation means the speaker (live check of group 10, T1 and T3) ----------


def test_tone_check_reads_a_reported_pronoun_as_the_speaker_mdd_004():
    """Live, a faithful T1 and T3 escalated because the tone check read Tamil "தாங்கள்" (they themselves, or the
    honorific you) in the back-translation as "you", and so as the patient's worry given to the physician."""
    tone = " ".join(TONE_SYSTEM.split())
    assert "The back-translation is reported speech too: a pronoun that refers back to the speaker in it" in tone
    assert '(such as Tamil "தாங்கள்" after "the patient says"), means the speaker, never the listener' in tone
    translate = " ".join(TRANSLATE_SYSTEM.split())
    assert 'never by a word that can also mean "you"' in translate
