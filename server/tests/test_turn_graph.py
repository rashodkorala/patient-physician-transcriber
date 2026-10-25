"""Turn graph tests with a scripted model (task 2.3, ADR-004, CDR-002, EDR-002)."""

import asyncio

import pytest

import fake_model
from fake_model import field
from graph.turn_graph import Draft, ToneCheck, TurnPipeline
from kb.embeddings import HashingEmbedder
from kb.store import KnowledgeBase
from llm import ScriptedModel

DOSE = "Use the nitroglycerin spray: 0.4 milligrams, one spray under your tongue."


@pytest.fixture(scope="module")
def kb():
    return KnowledgeBase(HashingEmbedder())


def model(translate=None, tone_check=None):
    handlers = {
        "translate": translate or fake_model.translate,
        "tone_check": tone_check or fake_model.tone_check,
        "empathy": fake_model.empathy,
    }
    return ScriptedModel(handlers)


def run(kb, m, text=DOSE, speaker="physician", source="en-CA", target="pa-IN", recognition=0.95):
    stages = []

    async def emit(stage):
        stages.append(stage)

    result, reason = asyncio.run(
        TurnPipeline(m, kb).run(
            turn_id="t1",
            speaker=speaker,
            source=source,
            target=target,
            text=text,
            recognition_confidence=recognition,
            emit=emit,
        )
    )
    return result, reason, stages


def mistranslate_dose(times):
    """Translate with 0.4 turned into 4 for the first `times` attempts."""
    calls = {"n": 0}

    def handler(user):
        calls["n"] += 1
        draft = fake_model.translate(user)
        if calls["n"] <= times:
            draft = Draft(**{**draft.model_dump(), "translation": draft.translation.replace("0.4", "4")})
        return draft

    return handler


def tone_fails(times):
    calls = {"n": 0}

    def handler(user):
        calls["n"] += 1
        ok = calls["n"] > times
        return ToneCheck(certainty_preserved=ok, warmth_preserved=True, issue="" if ok else "Sounds more serious.")

    return handler


def test_faithful_dose_needs_readback_cdr_002(kb):
    result, reason, stages = run(kb, model())
    assert result.status == "readback_required" and result.attempts == 1 and reason is None
    assert all(v.matched for v in result.critical_values)
    assert {"checking_glossary", "translating", "verifying"} <= set(stages)
    assert {g.term for g in result.glossary_used} == {"nitroglycerin spray", "milligrams"}
    medication = next(v for v in result.critical_values if v.kind == "medication")
    assert medication.translated == "ਨਾਈਟ੍ਰੋਗਲਿਸਰੀਨ ਸਪਰੇਅ"  # matched in the translation, not the back-translation


def test_mismatch_then_fixed_on_retry_cdr_002(kb):
    m = model(translate=mistranslate_dose(1))
    result, _, stages = run(kb, m)
    assert result.status == "readback_required" and result.attempts == 2
    assert "retrying" in stages
    retry_prompt = [u for p, u in m.calls if p == "translate"][1]
    assert "Keep exactly: 0.4 milligrams" in field(retry_prompt, "fix_these")


def test_mismatch_twice_is_blocked_cdr_002(kb):
    result, reason, _ = run(kb, model(translate=mistranslate_dose(2)))
    assert result.status == "blocked" and result.attempts == 2 and reason is None
    assert any(not v.matched for v in result.critical_values)


def test_tone_failure_twice_escalates_cdr_002(kb):
    result, reason, _ = run(kb, model(tone_check=tone_fails(2)), text="This is very unlikely to be serious.")
    assert result.status == "escalated" and reason == "tone_failure"


def test_matched_dose_with_failed_tone_is_escalated_not_read_back_cdr_002(kb):
    result, reason, _ = run(kb, model(tone_check=tone_fails(2)))
    assert all(v.matched for v in result.critical_values)
    assert result.status == "escalated" and reason == "tone_failure"


def test_mismatch_beats_tone_failure_cdr_002(kb):
    result, _, _ = run(kb, model(translate=mistranslate_dose(2), tone_check=tone_fails(2)))
    assert result.status == "blocked"


def test_low_recognition_confidence_escalates_as_low_confidence_cdr_001(kb):
    result, reason, _ = run(kb, model(tone_check=tone_fails(2)), text="Hello.", recognition=0.4)
    assert result.status == "escalated" and reason == "low_confidence"  # both failed: low_confidence wins


def test_patient_numbers_are_checked_but_not_read_back_cdr_002(kb):
    result, _, _ = run(kb, model(), text="ਮੈਂ 58 ਸਾਲ ਦਾ ਹਾਂ।", speaker="patient", source="pa-IN", target="en-CA")
    assert result.status == "final"
    assert result.critical_values and all(v.matched for v in result.critical_values)


def test_plain_turn_is_final_and_uses_glossary_guidance(kb):
    m = model()
    result, _, _ = run(kb, m, text="You did not have a heart attack.")
    assert result.status == "final" and result.critical_values == []
    prompt = next(u for p, u in m.calls if p == "translate")
    assert "heart attack = ਦਿਲ ਦਾ ਦੌਰਾ" in field(prompt, "glossary")
    assert field(prompt, "guidance") != "none"


def test_fake_model_markers_drive_blocked_and_escalated_turns(kb):
    blocked, _, _ = run(kb, fake_model.fake_model(), text=f"{DOSE} {fake_model.MISMATCH_MARKER}")
    assert blocked.status == "blocked" and "4 ਮਿਲੀਗ੍ਰਾਮ" in blocked.translation and "0.4" not in blocked.translation
    escalated, reason, _ = run(kb, fake_model.fake_model(), text=f"Hello. {fake_model.TONE_MARKER}")
    assert escalated.status == "escalated" and reason == "tone_failure"


def test_one_model_call_per_attempt_before_the_tone_check_adr_004(kb):
    # ADR-004's latency mitigation: translate also reads emotion, certainty, and medications.
    m = model()
    result, _, stages = run(kb, m)
    assert [purpose for purpose, _ in m.calls] == ["translate", "tone_check"]
    assert "analysing" not in stages
    assert result.emotion == "calm" and result.certainty == "high"


def test_retry_repeats_only_translate_and_tone_check_adr_004(kb):
    m = model(translate=mistranslate_dose(1))
    run(kb, m)
    assert [purpose for purpose, _ in m.calls] == ["translate", "tone_check", "translate", "tone_check"]
