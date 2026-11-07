"""Contract tests for CDR-001 and CDR-002 (task 1.2)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts import (
    EmpathyNudge,
    InterpreterEscalation,
    InterpreterLine,
    NameProposed,
    Names,
    TurnCaption,
    TurnRef,
    TurnResult,
    VisitStateController,
    VisitStatePublic,
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
    ],
)
def test_controller_payload_fixtures_validate_cdr_001(name, model):
    assert model.model_validate(load(name)).wire() == load(name)


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
