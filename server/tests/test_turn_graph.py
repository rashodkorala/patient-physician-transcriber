"""Turn graph tests with a scripted model (task 2.3, ADR-004, CDR-002, EDR-002), and manner in the same call
(IDR-005, trust-across-the-barrier 2.1), and the affect phrase in the frame (IDR-006, affect-in-words group 2)."""

import asyncio
import re

import pytest

import fake_model
from contracts import to_caption
from fake_model import field
from graph.turn_graph import TONE_SYSTEM, TRANSLATE_SYSTEM, Draft, ToneCheck, TurnPipeline
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
        "trust": fake_model.trust,
    }
    return ScriptedModel(handlers)


def run(
    kb, m, text=DOSE, speaker="physician", source="en-CA", target="pa-IN", recognition=0.95, unclear_streak=0, **names
):
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
            unclear_streak=unclear_streak,
            emit=emit,
            **names,
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
        return ToneCheck(
            meaning_preserved=True,
            certainty_preserved=ok,
            warmth_preserved=True,
            issue="" if ok else "Sounds more serious.",
        )

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


def test_low_recognition_confidence_is_unclear_before_the_third_adr_003(kb):
    for streak in (0, 1):
        result, reason, _ = run(kb, model(), text="Hello.", speaker="patient", recognition=0.4, unclear_streak=streak)
        assert result.status == "unclear" and reason is None and result.attempts == 2
        assert result.unclear_streak == streak + 1


def test_third_low_confidence_turn_escalates_as_low_confidence_cdr_002(kb):
    result, reason, _ = run(kb, model(), text="Hello.", speaker="patient", recognition=0.4, unclear_streak=2)
    assert result.status == "escalated" and reason == "low_confidence"
    assert result.unclear_streak == 0  # the third unclear's escalation starts the count again


def test_confidence_and_tone_failure_escalates_as_tone_failure_until_the_third_cdr_002(kb):
    # Both failed: a tone failure escalates at once, and confidence names the reason only at the third (CDR-001).
    result, reason, _ = run(kb, model(tone_check=tone_fails(2)), text="Hello.", recognition=0.4)
    assert result.status == "escalated" and reason == "tone_failure" and result.unclear_streak == 0
    result, reason, _ = run(kb, model(tone_check=tone_fails(2)), text="Hello.", recognition=0.4, unclear_streak=1)
    assert result.status == "escalated" and reason == "tone_failure" and result.unclear_streak == 1
    result, reason, _ = run(kb, model(tone_check=tone_fails(2)), text="Hello.", recognition=0.4, unclear_streak=2)
    assert result.status == "escalated" and reason == "low_confidence" and result.unclear_streak == 0


def test_tone_only_failure_escalates_at_once_whatever_the_streak_adr_003(kb):
    for streak in (0, 1, 2):
        result, reason, _ = run(kb, model(tone_check=tone_fails(2)), text="It is unlikely.", unclear_streak=streak)
        assert result.status == "escalated" and reason == "tone_failure"
        assert result.unclear_streak == streak  # a tone escalation leaves the streak


def test_blocked_and_final_turns_and_the_streak_cdr_002(kb):
    blocked, _, _ = run(kb, model(translate=mistranslate_dose(2)), unclear_streak=1)
    assert blocked.status == "blocked" and blocked.unclear_streak == 1  # blocked leaves it
    final, _, _ = run(kb, model(), text="Hello.", speaker="patient", source="pa-IN", target="en-CA", unclear_streak=2)
    assert final.status == "final" and final.unclear_streak == 0  # final resets it
    readback, _, _ = run(kb, model(), unclear_streak=1)
    assert readback.status == "readback_required" and readback.unclear_streak == 1  # reset only when confirmed


def test_unclear_beats_readback_but_blocked_beats_unclear_cdr_002(kb):
    # A physician dose turn that matches but stays below the confidence threshold is unclear, never read back.
    unclear, _, _ = run(kb, model(), recognition=0.4)
    assert unclear.status == "unclear" and all(v.matched for v in unclear.critical_values)
    blocked, _, _ = run(kb, model(translate=mistranslate_dose(2)), recognition=0.4)
    assert blocked.status == "blocked"


def test_fake_unclear_marker_is_unclear_on_every_attempt_adr_003(kb):
    text = f"Hello. {fake_model.UNCLEAR_MARKER}"
    result, reason, _ = run(kb, model(), text=text, speaker="patient", source="pa-IN", target="en-CA")
    assert result.status == "unclear" and reason is None and result.attempts == 2
    assert result.confidence == fake_model.UNCLEAR_CONFIDENCE


def test_unclear_caption_has_no_translation_cdr_002(kb):
    result, _, _ = run(kb, model(), recognition=0.4)
    caption = to_caption(result).wire()
    assert caption["status"] == "unclear" and caption["translation"] is None and caption["toneLabel"] is None
    assert caption["criticalValues"] == [] and caption["glossaryUsed"] == [] and caption["manner"] is None
    assert "unclearStreak" not in caption and result.wire()["unclearStreak"] == 1


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


# ---------- mediator voice (MDD-004) ----------


def translate_prompt(m) -> str:
    return next(user for purpose, user in m.calls if purpose == "translate")


@pytest.mark.parametrize(
    ("speaker", "source", "target", "names", "speaker_name", "listener_name"),
    [
        (
            "physician",
            "en-CA",
            "pa-IN",
            {"physician_name": "Dr. Thomas", "patient_name": "Harpreet"},
            "Dr. Thomas",
            "Harpreet",
        ),
        ("physician", "en-CA", "pa-IN", {}, "your doctor", "unknown"),
        (
            "patient",
            "pa-IN",
            "en-CA",
            {"physician_name": "Dr. Thomas", "patient_name": "Harpreet"},
            "Harpreet",
            "Dr. Thomas",
        ),
        ("patient", "pa-IN", "en-CA", {}, "the patient", "unknown"),
        ("companion", "pa-IN", "en-CA", {"physician_name": "Dr. Thomas"}, "the patient's companion", "Dr. Thomas"),
    ],
)
def test_translate_names_the_speaker_and_listener_mdd_004(
    kb, speaker, source, target, names, speaker_name, listener_name
):
    m = model()
    run(kb, m, text="Hello.", speaker=speaker, source=source, target=target, **names)
    user = translate_prompt(m)
    assert field(user, "speaker_name") == speaker_name
    assert field(user, "listener_name") == listener_name


def test_translate_instructions_ask_for_reported_speech_and_relay_only_mdd_004():
    from graph.turn_graph import TONE_SYSTEM, TRANSLATE_SYSTEM

    for rule in ("reported speech that names the speaker", "never soften, strengthen, add, or drop", "Relay only"):
        assert rule in TRANSLATE_SYSTEM
    assert "keeping its reporting frame" in TRANSLATE_SYSTEM
    assert "are expected: never count them as a problem" in " ".join(TONE_SYSTEM.split())


def relay(frame):
    """A faithful relay with a reporting frame in front, as the live model writes it."""

    def handler(user):
        draft = fake_model.translate(user)
        back = f"{field(user, 'speaker_name')} is saying: {draft.back_translation}"
        return Draft(**{**draft.model_dump(), "translation": f"{frame} {draft.translation}", "back_translation": back})

    return handler


def test_reporting_frame_keeps_critical_values_matched_mdd_004(kb):
    result, _, _ = run(kb, model(translate=relay("ਡਾ. ਥਾਮਸ ਕਹਿ ਰਹੇ ਹਨ ਕਿ")), physician_name="Dr. Thomas")
    assert result.status == "readback_required" and result.attempts == 1
    assert all(v.matched for v in result.critical_values)


def test_frame_only_relay_is_not_escalated_mdd_004(kb):
    result, reason, _ = run(kb, model(translate=relay("ਡਾ. ਥਾਮਸ ਕਹਿ ਰਹੇ ਹਨ ਕਿ")), text="Hello, how are you?")
    assert result.status == "final" and reason is None


def test_dropped_instruction_fails_the_tone_check_and_escalates_mdd_004(kb):
    def dropped(user):
        return ToneCheck(
            meaning_preserved=False,
            certainty_preserved=True,
            warmth_preserved=True,
            issue="The rash warning was dropped.",
        )

    result, reason, _ = run(kb, model(tone_check=dropped), text="Stop the medicine at once if you get a rash.")
    assert result.status == "escalated" and reason == "tone_failure" and result.attempts == 2


# ---------- manner (IDR-005) ----------


def test_manner_is_read_in_the_translate_call_and_labels_a_physician_turn_idr_005(kb):
    m = model()
    result, _, _ = run(kb, m, text="The tests were reassuring. You did not have a heart attack.")
    assert [purpose for purpose, _ in m.calls] == ["translate", "tone_check"]  # no extra call
    assert result.status == "final" and result.manner == "reassuring"
    assert to_caption(result).manner == "reassuring"
    plain, _, _ = run(kb, model(), text="How long have you had the pain?")
    assert plain.manner == "plain" and to_caption(plain).manner == "plain"


def test_patient_turn_has_a_private_manner_and_no_caption_label_idr_005(kb):
    result, _, _ = run(kb, model(), text="ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਡਾਕਟਰ ਜੀ।", speaker="patient", source="pa-IN", target="en-CA")
    assert result.manner == "plain" and to_caption(result).manner is None
    companion, _, _ = run(kb, model(), text="ਉਹ ਸੋਮਵਾਰ ਤੋਂ ਬਿਮਾਰ ਹੈ।", speaker="companion", source="pa-IN", target="en-CA")
    assert to_caption(companion).manner is None


def test_frame_adverb_passes_the_tone_check_and_keeps_the_dose_idr_005(kb):
    def gentle_relay(user):
        draft = fake_model.translate(user)
        back = f"Dr. Thomas is saying, gently, that {draft.back_translation}"
        return Draft(
            **{
                **draft.model_dump(),
                "manner": "gentle",
                "translation": f"ਡਾ. ਥਾਮਸ ਨਰਮੀ ਨਾਲ ਕਹਿ ਰਹੇ ਹਨ ਕਿ {draft.translation}",
                "back_translation": back,
            }
        )

    result, reason, _ = run(kb, model(translate=gentle_relay), physician_name="Dr. Thomas")
    assert result.status == "readback_required" and reason is None and result.attempts == 1
    assert result.manner == "gentle" and all(v.matched for v in result.critical_values)
    assert "0.4" in result.translation
    hello, reason, _ = run(kb, model(translate=gentle_relay), text="Hello, how are you?", physician_name="Dr. Thomas")
    assert hello.status == "final" and reason is None


def test_prompts_define_manner_the_frame_rule_and_the_tone_check_allowance_idr_005():
    translate = " ".join(TRANSLATE_SYSTEM.split())
    for manner in ("plain", "warm", "reassuring", "gentle", "serious", "urgent", "apologetic", "encouraging"):
        assert manner in translate
    assert "plain is the default" in translate
    # 2026-11-11 amendment: no frame adverb for reassuring (the voice and the label carry it).
    assert "only for gentle, serious, urgent, or apologetic" in translate
    assert "Never for plain, warm, reassuring, or encouraging" in translate
    assert "never anywhere but the opening frame" in translate
    # Indirect speech in every sentence, shown with a two-sentence example.
    assert "in every sentence, not only the first" in translate and 'never "I" or "we" anywhere' in translate
    assert "They will start you on a new medicine today." in translate
    tone = " ".join(TONE_SYSTEM.split())
    assert "one manner adverb" in tone and "any such adverb in the frame is expected and never a problem" in tone
    # The tone check stays lenient: it accepts every manner adverb, so a faithful relay is never escalated for
    # one manner word, even one the translate prompt asks the model not to add.
    for adverb in ("gently", "reassuringly", "seriously", "urgently", "apologetically", "warmly", "encouragingly"):
        assert adverb in tone
    assert "reassuringly" not in translate
    assert "seriousness or certainty changed still fails certainty_preserved" in tone


# ---------- affect in words (IDR-006, MDD-006) ----------

PHRASES = (
    "sounding worried",
    "sounding embarrassed",
    "sounding as if in pain",
    "sounding relieved",
    "sounding confused",
)
WORRIED_DOSE = "I am worried, I take 0.4 milligrams of nitroglycerin."


def phrases_in(text: str) -> list[str]:
    return [p for p in PHRASES for _ in range(text.count(p))]


def opening_frame(translation: str) -> str:
    """Everything up to and including the frame's closing comma after its affect phrase."""
    phrase = phrases_in(translation)[0]
    return translation[: translation.index(phrase) + len(phrase) + 1]


def test_prompts_define_the_affect_phrase_rule_idr_006():
    translate = " ".join(TRANSLATE_SYSTEM.split())
    assert "For a patient or companion turn only, the frame names the speaker's emotion" in translate
    assert "once, as one hedged phrase in the target language's natural form" in translate
    for emotion, phrase in (
        ("worried", "sounding worried"),
        ("embarrassed", "sounding embarrassed"),
        ("in_pain", "sounding as if in pain"),
        ("relieved", "sounding relieved"),
        ("confused", "sounding confused"),
    ):
        assert f'{emotion} as "{phrase}"' in translate
    assert '"The patient says, sounding worried, that ..."' in translate
    assert "A calm turn gets no phrase, and a physician turn never gets one." in translate
    assert "Never more than one phrase, never anywhere but the opening frame" in translate
    assert "a certainty word, a number, or a medication" in translate
    # The emotion the phrase follows is read from the words alone, calm unless they clearly carry a feeling.
    assert "read from the words alone (calm is the default" in translate
    # The voice no longer carries manner, so the prompt no longer says it does.
    assert "the voice carries" not in translate
    tone = " ".join(TONE_SYSTEM.split())
    assert "one hedged phrase naming how the speaker sounded" in tone
    assert "one such phrase in the frame is expected and never a problem" in tone
    assert "seriousness or certainty changed still fails certainty_preserved" in tone


def test_worried_patient_turn_has_exactly_one_phrase_in_the_frame_idr_006(kb):
    m = model()
    result, reason, _ = run(kb, m, text="I am scared of the needle.", speaker="patient", source="pa-IN", target="en-CA")
    assert [purpose for purpose, _ in m.calls] == ["translate", "tone_check"]  # no extra call
    assert result.status == "final" and reason is None and result.emotion == "worried"
    assert result.translation == "[en-CA] The patient says, sounding worried, I am scared of the needle."
    assert phrases_in(result.translation) == ["sounding worried"]
    assert to_caption(result).manner is None
    named, _, _ = run(
        kb, model(), text="I am scared.", speaker="patient", source="pa-IN", target="en-CA", patient_name="Harpreet"
    )
    assert named.translation == "[en-CA] Harpreet says, sounding worried, I am scared."


def test_calm_patient_turn_has_no_phrase_idr_006(kb):
    result, _, _ = run(kb, model(), text="ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਡਾਕਟਰ ਜੀ।", speaker="patient", source="pa-IN", target="en-CA")
    assert result.emotion == "calm" and result.translation == "[en-CA] ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਡਾਕਟਰ ਜੀ।"
    assert phrases_in(result.translation) == []


def test_companion_turn_names_the_companion_and_carries_one_phrase_idr_006(kb):
    result, _, _ = run(
        kb, model(), text="I am embarrassed to say this.", speaker="companion", source="pa-IN", target="en-CA"
    )
    assert result.speaker == "companion" and result.emotion == "embarrassed"
    assert result.translation.startswith("[en-CA] The patient's companion says, sounding embarrassed, ")
    assert phrases_in(result.translation) == ["sounding embarrassed"]


def test_physician_turn_never_gets_an_affect_phrase_idr_006(kb):
    result, _, _ = run(kb, model(), text="I am worried about your blood pressure.", physician_name="Dr. Thomas")
    assert result.emotion == "worried" and result.status == "final"
    assert phrases_in(result.translation) == [] and " says, " not in result.translation


def framed_patient_relay(phrase):
    """A faithful patient relay whose frame carries `phrase`, back-translated with the same frame."""

    def handler(user):
        draft = fake_model.translate(user)
        text = fake_model.field(user, "utterance")
        frame = f"The patient says, {phrase}, "
        return Draft(
            **{
                **draft.model_dump(),
                "translation": f"[en-CA] {frame}{text}",
                "back_translation": f"{frame}{text}",
            }
        )

    return handler


def judge(user):
    """A tone check that follows TONE_SYSTEM: the frame and one hedged affect phrase are expected; anything else
    added to the relay changes how certain or serious it sounds."""
    original, back = field(user, "original"), field(user, "back_translation")
    relayed = re.sub(rf"^The patient says, (?:{'|'.join(PHRASES)}), ", "", back)
    same = relayed == original
    return ToneCheck(
        meaning_preserved=True,
        certainty_preserved=same,
        warmth_preserved=True,
        issue="" if same else "The frame makes the patient sound more certain than they were.",
    )


def test_frame_phrase_passes_the_tone_check_idr_006(kb):
    m = model(translate=framed_patient_relay("sounding worried"), tone_check=judge)
    result, reason, _ = run(kb, m, text="I am scared.", speaker="patient", source="pa-IN", target="en-CA")
    assert result.status == "final" and reason is None and result.attempts == 1
    tone_user = next(user for purpose, user in m.calls if purpose == "tone_check")
    assert field(tone_user, "back_translation") == "The patient says, sounding worried, I am scared."


def test_phrase_that_makes_the_statement_more_certain_fails_the_tone_check_idr_006(kb):
    m = model(translate=framed_patient_relay("sounding sure it is nothing serious"), tone_check=judge)
    result, reason, _ = run(
        kb, m, text="I think it might be nothing.", speaker="patient", source="pa-IN", target="en-CA"
    )
    assert result.status == "escalated" and reason == "tone_failure" and result.attempts == 2
    # The same turn with only the hedged phrase is not escalated: the phrase alone is never the failure.
    hedged, reason, _ = run(
        kb,
        model(translate=framed_patient_relay("sounding worried"), tone_check=judge),
        text="I think it might be nothing.",
        speaker="patient",
        source="pa-IN",
        target="en-CA",
    )
    assert hedged.status == "final" and reason is None


def test_worried_patient_dose_keeps_its_value_and_the_check_still_blocks_a_change_idr_006(kb):
    result, reason, _ = run(kb, model(), text=WORRIED_DOSE, speaker="patient", source="pa-IN", target="en-CA")
    assert result.status == "final" and reason is None and result.attempts == 1
    assert "0.4" in result.translation and result.critical_values
    assert all(v.matched for v in result.critical_values)
    assert phrases_in(result.translation) == ["sounding worried"]
    assert "0.4" not in opening_frame(result.translation)  # the phrase sits in the frame, before the value
    changed, _, _ = run(
        kb, model(translate=mistranslate_dose(2)), text=WORRIED_DOSE, speaker="patient", source="pa-IN", target="en-CA"
    )
    assert changed.status == "blocked" and "sounding worried" in changed.translation
    assert not all(v.matched for v in changed.critical_values)


# ---------- presenter mismatch control (TDM-002, task 5.1) ----------


class Arming:
    """The visit's one-shot injection as the graph sees it: claimed once, then spent."""

    def __init__(self, armed=True):
        self.armed = armed
        self.claims = 0

    async def claim(self):
        self.claims += 1
        fired, self.armed = self.armed, False
        return fired


def run_armed(kb, m, arming, text=DOSE):
    return asyncio.run(
        TurnPipeline(m, kb).run(
            turn_id="t1",
            speaker="physician",
            source="en-CA",
            target="pa-IN",
            text=text,
            recognition_confidence=0.95,
            claim_injection=arming.claim,
        )
    )


def test_injection_multiplies_the_first_dose_by_ten_on_both_attempts_and_blocks_tdm_002(kb):
    m = model()
    arming = Arming()
    result, reason = run_armed(kb, m, arming)
    assert result.status == "blocked" and result.attempts == 2 and reason is None
    assert "4 ਮਿਲੀਗ੍ਰਾਮ" in result.translation and "0.4" not in result.translation
    dose = next(v for v in result.critical_values if v.source == "0.4 milligrams")
    assert dose.matched is False
    # The model translated faithfully both times; the control changed the number after it, on both attempts.
    assert [p for p, _ in m.calls] == ["translate", "tone_check", "translate", "tone_check"]
    assert "Keep exactly: 0.4 milligrams" in field([u for p, u in m.calls if p == "translate"][1], "fix_these")
    assert arming.claims == 1 and arming.armed is False


def test_injection_waits_through_a_turn_without_a_critical_value_tdm_002(kb):
    arming = Arming()
    result, _ = run_armed(kb, model(), arming, text="You did not have a heart attack.")
    assert result.status == "final" and arming.armed is True and arming.claims == 0


def test_injection_waits_through_a_number_that_is_not_a_dose_tdm_002(kb):
    arming = Arming()
    result, _ = run_armed(kb, model(), arming, text="If the pain is not better after 5 minutes, call 911.")
    assert result.status == "readback_required" and arming.armed is True and arming.claims == 0
    assert all(v.matched for v in result.critical_values)


def test_following_turn_after_firing_is_unaffected_tdm_002(kb):
    arming = Arming()
    run_armed(kb, model(), arming)
    repeated, _ = run_armed(kb, model(), arming)
    assert repeated.status == "readback_required" and "0.4" in repeated.translation
    assert all(v.matched for v in repeated.critical_values)


def test_unarmed_injection_leaves_the_dose_alone_tdm_002(kb):
    result, _ = run_armed(kb, model(), Arming(armed=False))
    assert result.status == "readback_required" and "0.4" in result.translation


@pytest.mark.parametrize(
    ("translation", "language", "expected"),
    [
        ("[pa-IN] 0.4 ਮਿਲੀਗ੍ਰਾਮ, 1 ਸਪਰੇਅ", "pa-IN", "[pa-IN] 4 ਮਿਲੀਗ੍ਰਾਮ, 1 ਸਪਰੇਅ"),
        ("Après 5 minutes, 0,4 milligramme", "fr-CA", "Après 5 minutes, 4 milligramme"),
        ("take 81 mg once a day", "en-CA", "take 810 mg once a day"),
        ("੦.੪ ਮਿਲੀਗ੍ਰਾਮ", "pa-IN", "4 ਮਿਲੀਗ੍ਰਾਮ"),  # noqa: RUF001  (Gurmukhi digits)
        ("0.4 மில்லிகிராம் மருந்து", "ta-LK", "4 மில்லிகிராம் மருந்து"),
        ("call 911 after 5 minutes", "en-CA", None),
    ],
)
def test_multiply_first_dose_tdm_002(translation, language, expected):
    from graph.turn_graph import multiply_first_dose

    assert multiply_first_dose(translation, language) == expected
