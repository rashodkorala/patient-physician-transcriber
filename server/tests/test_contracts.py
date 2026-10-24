"""Contract tests for CDR-001 and CDR-002 (task 1.2)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts import TurnCaption, TurnResult, VisitStatePublic, to_caption

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


def test_caption_never_carries_private_fields_cdr_002():
    caption = to_caption(TurnResult.model_validate(load("turn_result.json")) .model_copy(update={"status": "final"}))
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
