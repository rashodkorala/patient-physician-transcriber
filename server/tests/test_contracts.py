"""Contract tests for CDR-001, CDR-002, CDR-003, CDR-004, CDR-005 (consent), and CDR-006."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts import (
    CONTROLLER_COMMANDS,
    CONTROLLER_ONLY_EVENTS,
    REVIEW_OR_CONTROLLER_COMMANDS,
    CommandRefused,
    ConsentGive,
    ConsentNotice,
    ConsentSpeak,
    ConsentState,
    ConsentWithdraw,
    DemoInjectionState,
    EmpathyNudge,
    EscalationEntry,
    InjectionStatus,
    InterpreterDismiss,
    InterpreterDismissed,
    InterpreterEscalation,
    InterpreterLine,
    MarkHighRisk,
    NameProposed,
    Names,
    RecordIntegrity,
    TurnCaption,
    TurnRef,
    TurnResult,
    VisitStateController,
    VisitStatePublic,
    VoicePlayback,
    VoiceSpeaking,
    to_caption,
)

FIXTURES = Path(__file__).parent / "fixtures"
PRIVATE_FIELDS = {"emotion", "certainty", "backTranslation", "confidence", "toneTags", "attempts"}


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_turn_result_fixture_validates_cdr_002():
    result = TurnResult.model_validate(load("turn_result.json"))
    assert result.wire() == load("turn_result.json")


@pytest.mark.parametrize("name", ["turn_caption_final.json", "turn_caption_blocked.json"])
def test_turn_caption_fixtures_validate_cdr_002(name):
    caption = TurnCaption.model_validate(load(name))
    assert caption.wire() == load(name)


def test_visit_state_public_fixture_validates_cdr_001():
    state = VisitStatePublic.model_validate(load("visit_state_public.json"))
    assert state.wire() == load("visit_state_public.json")


@pytest.mark.parametrize(
    ("name", "model"),
    [
        ("visit_state_controller.json", VisitStateController),
        ("empathy_nudge.json", EmpathyNudge),
        ("interpreter_escalation.json", InterpreterEscalation),
        ("turn_ref.json", TurnRef),
        ("visit_names.json", Names),
        ("interpreter_line.json", InterpreterLine),
        ("name_proposed.json", NameProposed),
        ("voice_playback.json", VoicePlayback),
        ("voice_speaking.json", VoiceSpeaking),
        ("demo_injection_state.json", DemoInjectionState),
        ("mark_high_risk.json", MarkHighRisk),
    ],
)
def test_controller_payload_fixtures_validate_cdr_001(name, model):
    assert model.model_validate(load(name)).wire() == load(name)


@pytest.mark.parametrize(
    ("name", "model"),
    [
        ("consent_notice.json", ConsentNotice),
        ("consent_state.json", ConsentState),
        ("consent_speak.json", ConsentSpeak),
        ("consent_give.json", ConsentGive),
        ("consent_withdraw.json", ConsentWithdraw),
        ("command_refused.json", CommandRefused),
    ],
)
def test_consent_payload_fixtures_validate_cdr_005(name, model):
    assert model.model_validate(load(name)).wire() == load(name)


@pytest.mark.parametrize(
    ("name", "model"),
    [
        ("interpreter_dismiss.json", InterpreterDismiss),
        ("interpreter_dismissed.json", InterpreterDismissed),
        ("escalation_entry.json", EscalationEntry),
        ("injection_status.json", InjectionStatus),
        ("record_integrity_broken.json", RecordIntegrity),
    ],
)
def test_record_payload_fixtures_validate_cdr_006(name, model):
    assert model.model_validate(load(name)).wire() == load(name)


def test_consent_commands_are_review_or_controller_and_speak_is_private_cdr_005():
    assert {"consent.give", "consent.withdraw", "consent.read_aloud"} == REVIEW_OR_CONTROLLER_COMMANDS
    assert not REVIEW_OR_CONTROLLER_COMMANDS & CONTROLLER_COMMANDS
    assert "consent.speak" in CONTROLLER_ONLY_EVENTS
    assert not {"consent.changed", "command.refused"} & CONTROLLER_ONLY_EVENTS


def test_interpreter_dismiss_is_controller_only_and_dismissed_is_public_cdr_006():
    assert "interpreter.dismiss" in CONTROLLER_COMMANDS
    assert not {"interpreter.dismissed", "record.integrity"} & CONTROLLER_ONLY_EVENTS


def test_public_visit_state_has_no_controller_only_fields_cdr_006():
    # injection and escalations are controller only (CDR-006), so the public model cannot carry them.
    for key in ("injection", "escalations", "nudges"):
        with pytest.raises(ValidationError):
            VisitStatePublic.model_validate({**load("visit_state_public.json"), key: []})


def test_command_refused_has_no_free_text_cdr_005():
    with pytest.raises(ValidationError):
        CommandRefused.model_validate({"command": "consent.give", "reason": "wrong_notice", "message": "x"})
    with pytest.raises(ValidationError):
        CommandRefused.model_validate({"command": "consent.give", "reason": "Consent is already given"})


def test_withdrawal_reason_is_at_most_200_characters_cdr_005():
    ConsentWithdraw.model_validate({"reason": "x" * 200})
    with pytest.raises(ValidationError):
        ConsentWithdraw.model_validate({"reason": "x" * 201})


def test_visit_state_without_consent_or_record_fields_still_validates_cdr_005_cdr_006():
    state = load("visit_state_public.json")
    for key in ("consentNotice", "consentState", "interpreterOpen"):
        state.pop(key)
    parsed = VisitStatePublic.model_validate(state)
    assert parsed.consent_notice is None and parsed.interpreter_open is False


def test_caption_never_carries_private_fields_cdr_002():
    caption = to_caption(TurnResult.model_validate(load("turn_result.json")).model_copy(update={"status": "final"}))
    assert PRIVATE_FIELDS.isdisjoint(caption.wire())
    with pytest.raises(ValidationError):
        TurnCaption.model_validate({**load("turn_caption_final.json"), "emotion": "worried"})


@pytest.mark.parametrize("status", ["blocked", "escalated"])
def test_blocked_and_escalated_captions_hide_translation_cdr_002(status):
    result = TurnResult.model_validate(load("turn_result.json")).model_copy(update={"status": status})
    caption = to_caption(result)
    assert caption.status == status
    assert caption.translation is None
    assert caption.tone_label is None
    assert caption.critical_values == []


def test_caption_tone_label_is_register_only_cdr_002():
    result = TurnResult.model_validate(load("turn_result.json")).model_copy(
        update={"status": "final", "tone_tags": ["urgent", "reassuring"]}
    )
    assert to_caption(result).tone_label == "reassuring"
    result = result.model_copy(update={"tone_tags": ["urgent"]})
    assert to_caption(result).tone_label == "neutral"


def test_names_are_trimmed_and_blank_clears_cdr_003():
    names = Names.model_validate({"physicianName": "  Dr.   Thomas ", "patientName": "  "})
    assert names.wire() == {"physicianName": "Dr. Thomas", "patientName": None}


def test_names_left_out_are_not_set_cdr_003():
    assert Names.model_validate({"patientName": "Harpreet"}).model_fields_set == {"patient_name"}


@pytest.mark.parametrize("name", ["x" * 61, "Room 4", "Dr. 7homas"])
def test_names_reject_long_or_numbered_cdr_003(name):
    # A digit in a name would add a number to every relay that the critical value check never saw.
    with pytest.raises(ValidationError):
        Names.model_validate({"physicianName": name})


def test_visit_state_without_names_still_validates_cdr_003():
    state = load("visit_state_public.json")
    for key in ("physicianName", "patientName", "introduction"):
        state.pop(key)
    assert VisitStatePublic.model_validate(state).introduction == "pending"


@pytest.mark.parametrize(
    "payload",
    [
        {"speaking": True, "speechId": None, "language": None},
        {"speaking": True, "speechId": "t1", "language": None},
        {"speaking": False, "speechId": "t1", "language": "pa-IN"},
        {"speaking": False, "speechId": None, "language": "pa-IN"},
    ],
)
def test_voice_speaking_sets_id_and_language_exactly_when_speaking_cdr_004(payload):
    with pytest.raises(ValidationError):
        VoiceSpeaking.model_validate(payload)


@pytest.mark.parametrize("speech_id", ["", "x" * 65])
def test_voice_playback_rejects_empty_or_long_ids_cdr_004(speech_id):
    with pytest.raises(ValidationError):
        VoicePlayback.model_validate({"speechId": speech_id, "language": "pa-IN"})


def test_voice_speaking_carries_no_content_cdr_004():
    assert set(load("voice_speaking.json")) == {"speaking", "speechId", "language"}


def test_voice_commands_are_controller_only_and_the_event_is_public_cdr_004():
    assert {"voice.started", "voice.ended"} <= CONTROLLER_COMMANDS
    assert "voice.speaking" not in CONTROLLER_ONLY_EVENTS


def test_demo_commands_are_controller_only_and_injection_state_is_private_cdr_001():
    # TDM-002: presenter commands come from the controller; their state never reaches screen or review.
    assert {"demo.inject_mismatch", "demo.cancel_injection", "visit.mark_high_risk"} <= CONTROLLER_COMMANDS
    assert "demo.injection_state" in CONTROLLER_ONLY_EVENTS


def test_pause_and_interpreter_request_are_open_to_any_screen_cdr_001():
    assert not {"visit.pause", "visit.resume", "interpreter.request"} & CONTROLLER_COMMANDS
    assert not {"visit.paused", "visit.resumed", "interpreter.escalation"} & CONTROLLER_ONLY_EVENTS


@pytest.mark.parametrize("state", ["primed", ""])
def test_demo_injection_state_is_armed_fired_or_cancelled_tdm_002(state):
    with pytest.raises(ValidationError):
        DemoInjectionState.model_validate({"state": state})


def test_visit_state_without_speaking_still_validates_cdr_004():
    state = load("visit_state_public.json")
    state.pop("speaking")
    assert VisitStatePublic.model_validate(state).speaking is None
