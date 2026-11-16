"""Fixes for the findings of the live affect-in-words run of 16 November 2026 (affect-in-words group 9).

Each test reproduces a turn from `docs/voice-test.md`, section "Affect in words run, 16 November 2026", with a
scripted model that writes what the live model wrote, then checks the turn graph, the prompts, or the note's code
checks no longer let it through (MDD-006, IDR-006, MDD-004, ADR-004, ADR-011, EDR-002).
"""

import asyncio

import pytest
from test_turn_graph import framed_patient_relay, judge

import fake_model
from fake_model import field
from graph.turn_graph import TONE_SYSTEM, TRANSLATE_SYSTEM, Draft, TurnPipeline, unstated_gender
from kb.embeddings import HashingEmbedder
from kb.store import KnowledgeBase
from llm import ScriptedModel


@pytest.fixture(scope="module")
def kb():
    return KnowledgeBase(HashingEmbedder())


def model(translate, tone_check=None):
    return ScriptedModel(
        {"translate": translate, "tone_check": tone_check or fake_model.tone_check, "trust": fake_model.trust}
    )


def run(kb, m, text, *, speaker="patient", source="ta-LK", target="en-CA", **kwargs):
    return asyncio.run(
        TurnPipeline(m, kb).run(
            turn_id="t1",
            speaker=speaker,
            source=source,
            target=target,
            text=text,
            recognition_confidence=1.0,
            **kwargs,
        )
    )


def attempts_of(*drafts: dict):
    """A translate handler that writes each draft in turn (the last one again if asked for more), keeping the
    fake model's reading of the speaker for every field not given."""
    calls = {"n": 0}

    def handler(user):
        calls["n"] += 1
        base = fake_model.translate(user).model_dump()
        return Draft(**{**base, "affect_phrase": "", **drafts[min(calls["n"], len(drafts)) - 1]})

    return handler


def purposes(m) -> list[str]:
    return [purpose for purpose, _ in m.calls]


def translate_users(m) -> list[str]:
    return [user for purpose, user in m.calls if purpose == "translate"]


def tone_users(m) -> list[str]:
    return [user for purpose, user in m.calls if purpose == "tone_check"]


# ---------- 9.1: a feeling stated in the speaker's own words is not an affect phrase (T15, T1) ----------

T15 = "I am really worried that the new tablets are making me dizzy."


def test_tone_check_is_told_a_stated_feeling_is_content_not_an_affect_phrase_idr_006():
    tone = " ".join(TONE_SYSTEM.split())
    assert 'A feeling the speaker states in their own words ("I am really worried", "I am scared"' in tone
    assert "the relay must keep it, on every turn and for every listener" in tone
    assert "keeping it is never an affect phrase or an addition" in tone
    assert "Only words the interpreter added about how the speaker sounded count as an affect phrase." in tone
    assert "You are told the phrase the interpreter added, if any (interpreter_affect_phrase, or none)." in tone
    # T1: the name in the frame, in any script, is part of the frame.
    assert 'The frame may name the speaker by name or by role ("Meena Rajaratnam says", "the patient says")' in tone


def test_tone_check_is_given_the_interpreters_phrase_or_none_idr_006(kb):
    """T15: an English patient relayed to the patient carries no phrase, so the tone check is told none was added,
    and the worried words stay the patient's own; a turn to the physician names the one phrase that was added."""
    m = model(fake_model.translate)
    result, reason = run(kb, m, T15, source="en-CA", target="ta-LK", listener="patient", patient_name="Meena")
    assert result.status == "final" and reason is None and result.attempts == 1
    (user,) = tone_users(m)
    assert field(user, "interpreter_affect_phrase") == "none" and field(user, "listener") == "patient"
    assert "really worried" in field(user, "original") and "really worried" in field(user, "back_translation")
    to_physician = model(fake_model.translate)
    run(kb, to_physician, "I am scared.", source="pa-IN")
    assert field(tone_users(to_physician)[0], "interpreter_affect_phrase") == "sounding worried"


# ---------- 9.2: "sounding confused" before a plainly stated dose, when the patient said they were confused (T8) ----


T8 = "I take 500 milligrams of metformin every morning. But I am confused about when to see the eye doctor."


def test_tone_check_allows_a_stated_feeling_beside_a_plainly_stated_value_idr_006():
    tone = " ".join(TONE_SYSTEM.split())
    assert (
        "When the speaker did say they are confused, unsure, worried, or the like about anything in the turn, the "
        "matching phrase is faithful, even when the same turn also states a dose or another value plainly" in tone
    )
    assert "the value stays as plain as it was said" in tone
    # The phrase still fails where the speaker expressed no such feeling.
    assert '"sounding confused" in front of a dose from a speaker who expressed no confusion at all' in tone


def test_sounding_confused_before_a_plain_dose_is_final_when_the_patient_said_they_were_confused_idr_006(kb):
    m = model(framed_patient_relay("sounding confused"), tone_check=judge)
    result, reason = run(kb, m, T8, source="pa-IN")
    assert result.status == "final" and reason is None and result.attempts == 1
    assert all(v.matched for v in result.critical_values)
    # Without any confusion in the patient's words, the same phrase in front of the same dose still fails.
    plain = "I take 500 milligrams of metformin every morning."
    failed, reason = run(kb, model(framed_patient_relay("sounding confused"), tone_check=judge), plain, source="pa-IN")
    assert failed.status == "escalated" and reason == "tone_failure"


# ---------- 9.3: a back-translation in the wrong language leaves nothing to compare ----------

T2 = "நான் பள்ளியில் ஆசிரியராக வேலை செய்கிறேன். புகை பிடிப்பதில்லை."
T2_RELAY = "The patient says they work as a teacher at a school. They do not smoke."
T2_BACK = "நோயாளி தான் ஒரு பள்ளியில் ஆசிரியராக வேலை செய்வதாகச் சொல்கிறார். அவர் புகை பிடிப்பதில்லை."


def test_translate_is_told_the_back_translation_language_and_never_to_copy_the_relay_adr_004(kb):
    m = model(attempts_of({"translation": T2_RELAY, "back_translation": T2_BACK}))
    run(kb, m, T2)
    assert field(translate_users(m)[0], "back_translation_language") == "Sri Lankan Tamil (Tamil script)"
    prompt = " ".join(TRANSLATE_SYSTEM.split())
    assert "It is written in the language and script back_translation_language names, never in the target" in prompt
    assert "it is a fresh translation of your relay, never a copy of it" in prompt


def test_back_translation_copied_from_the_relay_is_never_checked_or_final_adr_004(kb):
    m = model(attempts_of({"translation": T2_RELAY, "back_translation": T2_RELAY}))
    result, reason = run(kb, m, T2)
    assert result.status == "escalated" and reason == "tone_failure" and result.attempts == 2
    assert purposes(m) == ["translate", "translate"]  # the tone check is not asked to compare nothing
    hint = field(translate_users(m)[1], "fix_these")
    assert "The back-translation must be a fresh translation of the relay into Sri Lankan Tamil" in hint


def test_back_translation_fixed_on_retry_is_checked_and_final_adr_004(kb):
    m = model(
        attempts_of(
            {"translation": T2_RELAY, "back_translation": T2_RELAY},
            {"translation": T2_RELAY, "back_translation": T2_BACK},
        )
    )
    result, reason = run(kb, m, T2)
    assert result.status == "final" and reason is None and result.attempts == 2
    assert purposes(m) == ["translate", "translate", "tone_check"]
    first, _ = run(kb, model(attempts_of({"translation": T2_RELAY, "back_translation": T2_BACK})), T2)
    assert first.status == "final" and first.attempts == 1


def test_romanised_original_is_left_to_the_tone_check_adr_004(kb):
    """A Punjabi turn typed in Latin letters cannot be told apart from English by script, so code leaves it."""
    typed = "Main har roz savere sair karda haan."
    m = model(attempts_of({"translation": "The patient says they walk every morning.", "back_translation": typed}))
    result, _ = run(kb, m, typed, source="pa-IN")
    assert result.attempts == 1 and purposes(m) == ["translate", "tone_check"]


# ---------- 9.4: a retry hint must not lead the model to paste the original's words (T8, T17, T19, P2) ----------

DOSE_DAILY = "நான் தினமும் காலையில் 500 மில்லிகிராம் மெட்ஃபோர்மின் எடுக்கிறேன்."
LOST = {
    "translation": "The patient says they take 500 mg of metformin in the morning.",
    "back_translation": "நோயாளி காலையில் 500 மி.கி. மெட்ஃபோர்மின் எடுப்பதாகச் சொல்கிறார்.",
}
PASTED = {
    "translation": "The patient says they take 500 mg of metformin தினமும் in the morning.",
    "back_translation": "நோயாளி தினமும் காலையில் 500 மி.கி. மெட்ஃபோர்மின் எடுப்பதாகச் சொல்கிறார்.",
}
KEPT = {
    "translation": "The patient says they take 500 mg of metformin every day, in the morning.",
    "back_translation": PASTED["back_translation"],
}


def test_retry_hint_names_a_lost_value_by_meaning_never_by_the_originals_words_adr_004(kb):
    m = model(attempts_of(LOST, KEPT))
    result, reason = run(kb, m, DOSE_DAILY)
    assert result.status == "final" and reason is None and result.attempts == 2
    hint = field(translate_users(m)[1], "fix_these")
    assert "Keep the frequency the original states, 1 time per day, in English" in hint
    assert "never copy a word of the original into the relay" in hint
    assert "தினமும்" not in hint and "Keep exactly" not in hint
    assert "Never copy a word of the original into it" in " ".join(TRANSLATE_SYSTEM.split())


def test_relay_that_pastes_the_originals_word_for_a_lost_value_is_never_final_adr_004(kb):
    """Before group 9 this was final: the pasted Tamil word satisfied the critical value check (T17, P2)."""
    m = model(attempts_of(LOST, PASTED))
    result, reason = run(kb, m, DOSE_DAILY)
    assert all(v.matched for v in result.critical_values)  # the paste satisfies the value check ...
    assert result.status == "escalated" and reason == "tone_failure" and result.attempts == 2  # ... but not code


def test_latin_value_into_a_latin_target_is_still_kept_exactly_adr_004(kb):
    lost = {"translation": "[fr-CA] Le médecin dit de prendre de la nitroglycérine.", "back_translation": "x"}
    m = model(attempts_of(lost, {"translation": "[fr-CA] 0.4 milligrams", "back_translation": "0.4 milligrams"}))
    run(kb, m, "Take 0.4 milligrams of nitroglycerin.", speaker="physician", source="en-CA", target="fr-CA")
    assert "Keep exactly: 0.4 milligrams" in field(translate_users(m)[1], "fix_these")


# ---------- 9.5: gender is never guessed from a name (T19, the note) ----------

TEACHER = "நான் பள்ளியில் ஆசிரியராக வேலை செய்கிறேன்."


@pytest.mark.parametrize(
    ("text", "unstated"),
    [
        ("Meena Rajaratnam says she works as a teacher at a school.", ["she"]),
        ("The patient says they work as a teacher. Her husband drives her here.", ["her"]),
        ("The patient says their mother can't breathe at night, and she is frightened.", []),
        ("The patient says her mother died of this illness.", ["her"]),
        ("Mr Singh says he walks every morning.", []),
        ("The patient says they had chest pain. The heart test was normal.", []),
    ],
)
def test_unstated_gender_mdd_004(text, unstated):
    assert unstated_gender(text) == unstated


def test_relay_that_guesses_the_speakers_gender_is_retried_mdd_004(kb):
    she = {"translation": "Meena Rajaratnam says she works as a teacher at a school.", "back_translation": TEACHER}
    they = {"translation": "Meena Rajaratnam says they work as a teacher at a school.", "back_translation": TEACHER}
    m = model(attempts_of(she, they))
    result, reason = run(kb, m, TEACHER, patient_name="Meena Rajaratnam")
    assert result.status == "final" and reason is None and result.attempts == 2
    assert '"she"' in field(translate_users(m)[1], "fix_these")
    always, reason = run(kb, model(attempts_of(she)), TEACHER, patient_name="Meena Rajaratnam")
    assert always.status == "escalated" and reason == "tone_failure"


def test_a_pronoun_only_the_back_translation_needs_is_not_a_guessed_gender_mdd_004(kb):
    """Live re-run of T15: the Tamil relay was gender-neutral, and only its English back-translation said "she".
    What the listener hears is the relay, so code reads the relay, and the tone check is not asked about gender."""
    relay = {
        "translation": "மீனா ராஜரத்னம் சொல்கிறார், புதிய மாத்திரைகள் தனக்குத் தலைச்சுற்றலை ஏற்படுத்துகின்றன என்று மிகவும் கவலைப்படுகிறார்.",
        "back_translation": "Meena Rajaratnam is saying that she is really worried that the new tablets are making her dizzy.",
    }  # fmt: skip
    result, reason = run(kb, model(attempts_of(relay)), T15, source="en-CA", target="ta-LK", listener="patient")
    assert result.status == "final" and reason is None and result.attempts == 1
    assert "gender" not in TONE_SYSTEM


def test_relay_that_names_a_gendered_relation_keeps_its_pronoun_mdd_004(kb):
    companion = "அம்மாவுக்கு இரவில் மூச்சு விட முடியாமல் போகிறது."
    relay = {
        "translation": "The patient's companion says the patient, their mother, can't breathe at night; she wakes up.",
        "back_translation": companion,
    }
    result, reason = run(kb, model(attempts_of(relay)), companion, speaker="companion")
    assert result.status == "final" and reason is None and result.attempts == 1
