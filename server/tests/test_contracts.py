"""Contract tests for CDR-001, CDR-002, CDR-003, CDR-004, CDR-005, CDR-006, CDR-007, and TDM-005."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts import (
    CONTROLLER_COMMANDS,
    CONTROLLER_ONLY_EVENTS,
    REVIEW_COMMANDS,
    REVIEW_OR_CONTROLLER_COMMANDS,
    ROLE_SHAPED_EVENTS,
    ArtefactsStale,
    ArtefactStatus,
    ClinicalNote,
    CommandRefused,
    ConsentGive,
    ConsentNotice,
    ConsentSpeak,
    ConsentState,
    ConsentWithdraw,
    DemoInjectionState,
    EmpathyNudge,
    EscalationEntry,
    ExplainBackRef,
    ExplainBackResult,
    ExplainBackState,
    InjectionStatus,
    InterpreterDismiss,
    InterpreterDismissed,
    InterpreterEscalation,
    InterpreterLine,
    MarkHighRisk,
    NameProposed,
    Names,
    NoteSentence,
    PatientSummary,
    RecordIntegrity,
    SegmentAmend,
    SegmentAmended,
    SegmentAnalysis,
    SegmentConfirm,
    SegmentHistory,
    SegmentHistoryController,
    SegmentStatus,
    SummaryCheck,
    SummaryRef,
    SummarySpeak,
    TagDowngrade,
    TamperRecord,
    TamperState,
    TurnCaption,
    TurnRef,
    TurnResult,
    VisitStateController,
    VisitStatePublic,
    VoicePlayback,
    VoiceSpeaking,
    to_caption,
    wire_explain_back,
    wire_note,
    wire_summary,
    wire_summary_check,
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
    assert {"consent.give", "consent.withdraw", "consent.read_aloud"} <= REVIEW_OR_CONTROLLER_COMMANDS
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


# ---------- CDR-005 explain-back, CDR-006 corrections and tamper, CDR-007 note and summary ----------


def contains_key(obj, key) -> bool:
    if isinstance(obj, dict):
        return key in obj or any(contains_key(v, key) for v in obj.values())
    if isinstance(obj, list):
        return any(contains_key(v, key) for v in obj)
    return False


@pytest.mark.parametrize(
    ("name", "model"),
    [
        ("explain_back_ref.json", ExplainBackRef),
        ("explain_back_state.json", ExplainBackState),
        ("explain_back_result.json", ExplainBackResult),
    ],
)
def test_explain_back_payload_fixtures_validate_cdr_005(name, model):
    assert model.model_validate(load(name)).wire() == load(name)


@pytest.mark.parametrize(
    ("name", "model"),
    [
        ("segment_confirm.json", SegmentConfirm),
        ("segment_amend.json", SegmentAmend),
        ("segment_status.json", SegmentStatus),
        ("segment_status_refused.json", SegmentStatus),
        ("segment_analysis.json", SegmentAnalysis),
        ("segment_amended_amend.json", SegmentAmended),
        ("segment_amended_confirm.json", SegmentAmended),
        ("segment_history.json", SegmentHistory),
        ("segment_history_controller.json", SegmentHistoryController),
        ("tamper_record.json", TamperRecord),
        ("tamper_state.json", TamperState),
    ],
)
def test_correction_and_tamper_payload_fixtures_validate_cdr_006(name, model):
    assert model.model_validate(load(name)).wire() == load(name)


@pytest.mark.parametrize(
    ("name", "model"),
    [
        ("artefact_status.json", ArtefactStatus),
        ("clinical_note.json", ClinicalNote),
        ("patient_summary.json", PatientSummary),
        ("summary_check.json", SummaryCheck),
        ("summary_ref.json", SummaryRef),
        ("summary_speak.json", SummarySpeak),
        ("artefacts_stale.json", ArtefactsStale),
    ],
)
def test_note_and_summary_payload_fixtures_validate_cdr_007(name, model):
    assert model.model_validate(load(name)).wire() == load(name)


def test_new_command_and_event_role_rules_cdr_005_cdr_006_cdr_007():
    assert {"explainback.start", "explainback.check", "explainback.cancel"} <= CONTROLLER_COMMANDS
    assert {"note.generate", "summary.generate", "demo.tamper_record"} <= CONTROLLER_COMMANDS
    assert {"segment.confirm", "segment.amend"} == REVIEW_COMMANDS
    assert {"summary.read_aloud", "summary.stop"} <= REVIEW_OR_CONTROLLER_COMMANDS
    assert not REVIEW_COMMANDS & (CONTROLLER_COMMANDS | REVIEW_OR_CONTROLLER_COMMANDS)
    private = {
        "explainback.result",
        "segment.analysis",
        "demo.tamper_state",
        "note.status",
        "note.ready",
        "summary.check",
        "summary.speak",
    }
    assert private <= CONTROLLER_ONLY_EVENTS
    public = {"explainback.state", "segment.status", "segment.amended", "summary.status", "summary.ready"}
    assert not (public | {"artefacts.stale"}) & CONTROLLER_ONLY_EVENTS
    assert {"summary.status", "artefacts.stale"} == ROLE_SHAPED_EVENTS


def test_public_visit_state_cannot_carry_private_artefacts_cdr_005_cdr_006_cdr_007():
    for key in ("tamper", "explainBackResults", "note", "noteStale", "summaryChecks"):
        with pytest.raises(ValidationError):
            VisitStatePublic.model_validate({**load("visit_state_public.json"), key: None})


def test_public_segment_history_cannot_carry_analysis_cdr_006():
    with pytest.raises(ValidationError):
        SegmentHistory.model_validate(load("segment_history_controller.json"))
    assert not contains_key(load("visit_state_public.json"), "analysis")


def test_explain_back_state_carries_no_text_or_outcomes_cdr_005():
    assert set(load("explain_back_state.json")) == {"explainBackId", "state", "explanationTurnIds"}


def test_tag_downgrade_from_is_from_on_the_wire_cdr_007():
    downgrade = TagDowngrade(sentence_id="n-s0", from_="patient_stated")
    assert downgrade.wire() == {"sentenceId": "n-s0", "from": "patient_stated", "to": "ai_inference"}
    assert TagDowngrade.model_validate(downgrade.wire()) == downgrade


def test_segment_amend_bounds_cdr_006():
    base = load("segment_amend.json")
    for bad in ({"text": ""}, {"text": "x" * 1001}, {"recognitionConfidence": 1.5}, {"language": "en-CA"}):
        with pytest.raises(ValidationError):
            SegmentAmend.model_validate({**base, **bad})


def test_note_sentence_needs_a_source_and_summary_check_attempt_is_one_or_two_cdr_007():
    sentence = load("clinical_note.json")["sections"][0]["sentences"][0]
    with pytest.raises(ValidationError):
        NoteSentence.model_validate({**sentence, "sources": []})
    with pytest.raises(ValidationError):
        SummaryCheck.model_validate({**load("summary_check.json"), "attempt": 3})


def test_a_summary_is_only_ever_passed_cdr_007():
    with pytest.raises(ValidationError):
        PatientSummary.model_validate({**load("patient_summary.json"), "check": "failed"})


def test_visit_state_without_the_new_fields_still_validates_cdr_005_cdr_006_cdr_007():
    state = load("visit_state_public.json")
    for key in ("segments", "explainBack", "summary", "summaryStale"):
        state.pop(key)
    parsed = VisitStatePublic.model_validate(state)
    assert parsed.segments == [] and parsed.summary is None


def test_chain_results_map_to_wire_one_to_one_adr_011_cdr_005_cdr_007():
    from chains import explain_back as eb
    from chains import note as nt
    from chains import summary as sm
    from chains.checks import SourceRef as ChainRef

    turn = ChainRef(kind="turn", id="t1", version="original")
    note = nt.ClinicalNote(
        note_id="n",
        language="en-CA",
        based_on_head="h",
        generated_at="2026-11-19T19:00:00+00:00",
        sections=(
            nt.NoteSection(heading="Plan", sentences=(nt.NoteSentence("n-s0", "Rest.", "ai_inference", (turn,)),)),
        ),
        untranslated_turn_ids=("t3",),
        tag_downgrades=(nt.TagDowngrade(sentence_id="n-s0", from_="patient_stated"),),
        attempts=2,
    )
    wired = wire_note(note).wire()
    assert wired["tagDowngrades"] == [{"sentenceId": "n-s0", "from": "patient_stated", "to": "ai_inference"}]
    assert wired["sections"][0]["sentences"][0]["sources"] == [{"kind": "turn", "id": "t1", "version": "original"}]
    assert "attempts" not in wired and wired["untranslatedTurnIds"] == ["t3"]

    summary = sm.PatientSummary(
        summary_id="s",
        language="pa-IN",
        based_on_head="h",
        generated_at="2026-11-19T19:00:00+00:00",
        sentences=(sm.SummarySentence("s.0", 0, "ਲਓ।", (turn,)),),
        values=(sm.SummaryValue("dose", "81 ਮਿਲੀਗ੍ਰਾਮ", "t1"),),
    )
    assert wire_summary(summary).wire()["sentences"][0]["sentenceId"] == "s.0"
    check = sm.SummaryCheck("s", 2, "failed", (sm.Mismatch("dose", "81", None, "t1", "missing"),), ("internal",))
    assert wire_summary_check(check).wire() == {
        "summaryId": "s",
        "attempt": 2,
        "outcome": "failed",
        "mismatches": [{"kind": "dose", "expected": "81", "found": None, "sourceTurnId": "t1", "problem": "missing"}],
    }

    item = eb.ExplainBackItem("e-c0", "frequency", "Twice a day", ("t1",), "missed", "code", "2 times per day")
    result = eb.ExplainBackResult("e", "h", ("t5",), (item,), "e", attempts=2)
    wired = wire_explain_back(result).wire()
    assert wired["items"][0]["decidedBy"] == "code" and wired["items"][0]["evidenceTurnIds"] == []
    assert "attempts" not in wired and wired["entryId"] == "e"
