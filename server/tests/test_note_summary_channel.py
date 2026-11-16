"""The clinical note and patient summary on the visit channel (CDR-007, ADR-011, ADR-006, demo-night-mvp tasks 3.6
and 3.7): generation off the receive loop, who receives what, the summary's value check and refusal, the chain
entry, the speak gate, read-aloud, and stale artefacts."""

import re

import pytest
from test_visit_channel import (
    drain_until,
    kb,  # noqa: F401  (fixture)
    make_client,
    submit,
    types,
)
from test_voice import FakeVoice
from visit_helpers import (
    CHEST,
    CHEST_CORRECTED,
    PLAN_PA,
    assert_public,
    close,
    command,
    connect,
    entries,
    kinds,
    marker,
    patient_says,
    speak_plan,
    translate,
    visit,
)

import fake_model
from chains.note import SYSTEM as NOTE_SYSTEM
from chains.note import DraftSection, DraftSentence, NoteDraft
from chains.summary import SYSTEM as SUMMARY_SYSTEM
from chains.summary import SummaryDraft
from contracts import ClinicalNote, PatientSummary
from fake_model import MISMATCH_MARKER


@pytest.fixture
def client(kb):  # noqa: F811
    with make_client(kb, translate=translate, voice=FakeVoice()) as c:
        yield c


def until_stage(ws, event_type, *stages):
    """Events up to the first `event_type` whose stage is one of `stages`."""
    seen = []
    while True:
        event = ws.receive_json()
        seen.append(event)
        if event["type"] == event_type and event["payload"]["stage"] in stages:
            return seen


def visit_with_plan(ctl) -> tuple[str, str]:
    return speak_plan(ctl), patient_says(ctl, CHEST)["turnId"]


def generate_note(ctl):
    command(ctl, "note.generate")
    return until_stage(ctl, "note.status", "ready", "failed")


def generate_summary(ctl):
    command(ctl, "summary.generate")
    return until_stage(ctl, "summary.status", "ready", "refused")


# ---------- the note ----------


WORRIED = ("ਮੈਨੂੰ ਸੂਈ ਤੋਂ ਬਹੁਤ ਡਰ ਲੱਗਦਾ ਹੈ।", None)


def test_the_affect_phrase_never_reaches_the_note_or_the_summary_idr_006(kb):  # noqa: F811
    """IDR-006 review fix 2: a worried patient turn is relayed with "sounding worried", and the chain keeps it as
    spoken, but the note and summary sources leave it out, so neither can restate it as the patient's words."""
    prompts: dict[str, list[str]] = {}

    def recording(purpose, handler):
        def record(user):
            prompts.setdefault(purpose, []).append(user)
            return handler(user)

        return record

    handlers = {
        "clinical_note": recording("clinical_note", fake_model.clinical_note),
        "patient_summary": recording("patient_summary", fake_model.patient_summary),
    }
    with make_client(kb, translate=translate, voice=FakeVoice(), handlers=handlers) as client:
        sockets, (ctl,) = connect(client, "controller")
        try:
            speak_plan(ctl)
            worried = patient_says(ctl, WORRIED)
            assert worried["translation"] == f"[en-CA] The patient says, sounding worried, {WORRIED[0]}"
            assert any("sounding worried" in (e["body"].get("translation") or "") for e in entries(client))
            generate_note(ctl)
            note = drain_until(ctl, "note.ready")[-1]["payload"]
            generate_summary(ctl)
            summary = drain_until(ctl, "summary.ready")[-1]["payload"]
        finally:
            close(sockets)
    for purpose in ("clinical_note", "patient_summary"):
        assert prompts[purpose] and all("sounding" not in user for user in prompts[purpose]), purpose
    note_text = [sentence["text"] for section in note["sections"] for sentence in section["sentences"]]
    assert f"[en-CA] The patient says {WORRIED[0]}" in note_text
    assert not any("sounding" in text for text in note_text)
    assert not any("sounding" in sentence["text"] for sentence in summary["sentences"])
    # The prompts say the same, for whatever the deterministic step cannot see.
    note_rule = " ".join(NOTE_SYSTEM.split())
    assert "never restate it, or any reading of how a speaker sounded" in note_rule
    assert "Leave how a speaker sounded out of the note." in note_rule
    summary_rule = " ".join(SUMMARY_SYSTEM.split())
    assert "Never say how the patient sounded or felt as the interpreter described it" in summary_rule


def test_note_every_sentence_tagged_and_sourced_and_controller_only_cdr_007(client):
    sockets, (ctl, record, tv, phone) = connect(client, "controller", "controller", "screen", "review")
    try:
        plan, chest = visit_with_plan(ctl)
        events = generate_note(ctl)
        stages = [e["payload"]["stage"] for e in events if e["type"] == "note.status"]
        assert stages == ["generating", "checking", "ready"]
        note = drain_until(ctl, "note.ready")[-1]["payload"]
        ClinicalNote.model_validate(note)
        sentences = [s for section in note["sections"] for s in section["sentences"]]
        assert sentences and all(s["tag"] and s["sources"] for s in sentences)
        cited = {(r["id"], r["version"]) for s in sentences for r in s["sources"]}
        assert cited == {(plan, "original"), (chest, "original")}
        assert note["basedOnHead"] == visit(client).chain.head_hash
        # A /record view connects with the controller role and gets the note too.
        assert drain_until(record, "note.ready")[-1]["payload"] == note
        _, (tv_events, phone_events) = marker(ctl, tv, phone)
        assert_public(tv_events + phone_events)
        assert "note" not in kinds(client)  # notes are not chained
    finally:
        close(sockets)
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        state = ctl.receive_json()["payload"]
        assert state["note"] == note and state["noteStale"] is False
    for role in ("screen", "review"):
        with client.websocket_connect(f"/ws/visit?role={role}") as ws:
            assert_public([ws.receive_json()])


def test_a_corrected_turn_is_cited_at_its_amendment_and_gaps_are_listed_cdr_007(client):
    sockets, (ctl, phone) = connect(client, "controller", "review")
    try:
        _, chest = visit_with_plan(ctl)
        submit(ctl, "patient", "pa-IN", f"ਮੈਟਫਾਰਮਿਨ 500 ਮਿਲੀਗ੍ਰਾਮ {MISMATCH_MARKER}")
        blocked = drain_until(ctl, "turn.result")[-1]["payload"]
        drain_until(phone, "record.integrity")
        command(
            phone, "segment.amend", segmentId=chest, text=CHEST_CORRECTED[0], language="pa-IN", recognitionConfidence=1
        )
        until_stage(ctl, "segment.status", "applied")
        amendment_id = visit(client).segments[chest].current
        generate_note(ctl)
        note = drain_until(ctl, "note.ready")[-1]["payload"]
        refs = [r for section in note["sections"] for s in section["sentences"] for r in s["sources"]]
        assert {"kind": "turn", "id": chest, "version": amendment_id} in refs
        assert all(r["id"] != blocked["turnId"] for r in refs)
        assert note["untranslatedTurnIds"] == [blocked["turnId"]]
        texts = [s["text"] for section in note["sections"] for s in section["sentences"]]
        assert CHEST_CORRECTED[1] in texts and CHEST[1] not in texts
    finally:
        close(sockets)


def test_a_wrong_tag_is_downgraded_and_listed_with_from_cdr_007(kb):  # noqa: F811
    def all_patient_stated(user):
        draft = fake_model.clinical_note(user)
        return NoteDraft(
            sections=[
                DraftSection(
                    heading=section.heading,
                    sentences=[s.model_copy(update={"tag": "patient_stated"}) for s in section.sentences],
                )
                for section in draft.sections
            ]
        )

    with make_client(kb, translate=translate, handlers={"clinical_note": all_patient_stated}) as client:
        sockets, (ctl,) = connect(client, "controller")
        try:
            visit_with_plan(ctl)
            generate_note(ctl)
            note = drain_until(ctl, "note.ready")[-1]["payload"]
            plan_sentence = next(s for s in note["sections"][0]["sentences"] if s["tag"] == "ai_inference")
            assert {"sentenceId": plan_sentence["sentenceId"], "from": "patient_stated", "to": "ai_inference"} in note[
                "tagDowngrades"
            ]
        finally:
            close(sockets)


def test_a_note_with_an_unsourced_sentence_fails_after_one_retry_and_is_never_published_cdr_007(kb):  # noqa: F811
    def unsourced(user):
        return NoteDraft(
            sections=[
                DraftSection(heading="Plan", sentences=[DraftSentence(text="Rest.", tag="ai_inference", sources=[])])
            ]
        )

    with make_client(kb, translate=translate, handlers={"clinical_note": unsourced}) as client:
        sockets, (ctl,) = connect(client, "controller")
        try:
            visit_with_plan(ctl)
            events = generate_note(ctl)
            stages = [e["payload"]["stage"] for e in events if e["type"] == "note.status"]
            assert stages == ["generating", "checking", "retrying", "checking", "failed"]
            assert "cites no source" in events[-1]["payload"]["detail"]
            assert "note.ready" not in types(events) and visit(client).note is None
            assert visit(client).note_generating is False
        finally:
            close(sockets)


def test_note_and_summary_generate_refusals_cdr_007(client):
    sockets, (ctl, tv, phone) = connect(client, "controller", "screen", "review")
    try:
        for name in ("note.generate", "summary.generate"):
            command(ctl, name)
            assert "Nothing has been spoken" in drain_until(ctl, "error")[-1]["payload"]["message"]
        patient_says(ctl, CHEST)
        submit(ctl, "physician", "en-CA", "Take metformin 500 milligrams twice a day.")
        turn_id = drain_until(ctl, "turn.readback_required")[-1]["payload"]["turnId"]
        for name in ("note.generate", "summary.generate"):
            command(ctl, name)
            assert "dose" in drain_until(ctl, "error")[-1]["payload"]["message"]
        command(ctl, "turn.readback_confirm", turnId=turn_id)
        drain_until(ctl, "turn.result")
        v = visit(client)
        for attribute, value, words in [
            ("amend_in_flight", "x", "correction"),
            ("note_generating", True, "already"),
            ("summary_generating", True, "already"),
        ]:
            setattr(v, attribute, value)
            name = "summary.generate" if attribute == "summary_generating" else "note.generate"
            command(ctl, name)
            assert words in drain_until(ctl, "error")[-1]["payload"]["message"]
            setattr(v, attribute, None if attribute == "amend_in_flight" else False)
        command(ctl, "explainback.start")
        drain_until(ctl, "explainback.state")
        v.explain_back = v.explain_back.model_copy(update={"state": "checking"})
        command(ctl, "note.generate")
        assert "explain-back" in drain_until(ctl, "error")[-1]["payload"]["message"]
        v.explain_back = v.explain_back.model_copy(update={"state": "cancelled"})

        # Screen and review copies are dropped.
        for ws in (tv, phone):
            command(ws, "note.generate")
            command(ws, "summary.generate")
        _, (tv_events, phone_events) = marker(ctl, tv, phone)
        assert not {"summary.status", "command.refused"} & set(types(tv_events + phone_events))
        assert v.note is None and v.summary is None
    finally:
        close(sockets)


# ---------- the summary ----------


def test_a_passed_summary_is_public_chained_and_spoken_by_sentence_cdr_007(client):
    sockets, (ctl, tv, phone) = connect(client, "controller", "screen", "review")
    try:
        visit_with_plan(ctl)
        events = generate_summary(ctl)
        stages = [e["payload"]["stage"] for e in events if e["type"] == "summary.status"]
        assert stages == ["generating", "checking", "ready"]
        checks = [e["payload"] for e in events if e["type"] == "summary.check"]
        assert [(c["attempt"], c["outcome"]) for c in checks] == [(1, "passed")]
        summary = drain_until(ctl, "summary.ready")[-1]["payload"]
        PatientSummary.model_validate(summary)
        assert summary["language"] == "pa-IN" and summary["check"] == "passed"
        assert PLAN_PA in [s["text"] for s in summary["sentences"]]
        integrity = drain_until(ctl, "record.integrity")[-1]["payload"]

        # Chained once, and its own entry does not make it stale.
        assert kinds(client).count("summary") == 1
        entry = entries(client)[-1]
        assert entry["kind"] == "summary" and entry["entryId"] == summary["summaryId"] and entry["body"] == summary
        assert integrity["status"] == "verified"
        assert visit(client).summary_stale is False

        for ws in (tv, phone):
            seen = drain_until(ws, "summary.ready")
            assert seen[-1]["payload"] == summary
            assert_public(seen)
            public_stages = [e["payload"] for e in seen if e["type"] == "summary.status"]
            assert [s["stage"] for s in public_stages] == ["generating", "checking", "ready"]

        # The speak gate serves each sentence in the patient's language only, in the constant delivery (IDR-006).
        first = summary["sentences"][0]
        assert first["sentenceId"] == f"{summary['summaryId']}.0"
        assert client.get(f"/api/speech/{first['sentenceId']}", params={"language": "pa-IN"}).status_code == 200
        assert client.get(f"/api/speech/{first['sentenceId']}", params={"language": "en-CA"}).status_code == 404
        assert client.get(f"/api/speech/{summary['summaryId']}.99", params={"language": "pa-IN"}).status_code == 404
        command(ctl, "voice.started", speechId=first["sentenceId"], language="pa-IN")
        speaking = drain_until(tv, "voice.speaking")[-1]["payload"]
        assert speaking == {"speaking": True, "speechId": first["sentenceId"], "language": "pa-IN"}
    finally:
        close(sockets)
    for role in ("screen", "review"):
        with client.websocket_connect(f"/ws/visit?role={role}") as ws:
            snapshot = ws.receive_json()
            assert snapshot["payload"]["summary"] == summary and snapshot["payload"]["summaryStale"] is False
            assert_public([snapshot])
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        state = ctl.receive_json()["payload"]
        assert [c["outcome"] for c in state["summaryChecks"]] == ["passed"]


def wrong_dose(user):
    draft = fake_model.patient_summary(user)
    return SummaryDraft(sentences=[s.model_copy(update={"text": re.sub("500", "50", s.text)}) for s in draft.sentences])


def no_dose(user):
    draft = fake_model.patient_summary(user)
    return SummaryDraft(sentences=[s for s in draft.sentences if "500" not in s.text])


@pytest.mark.parametrize(("handler", "problem"), [(wrong_dose, "changed"), (no_dose, "missing")])
def test_a_mismatched_or_missing_dose_is_refused_after_one_retry_cdr_007(kb, handler, problem):  # noqa: F811
    with make_client(kb, translate=translate, voice=FakeVoice(), handlers={"patient_summary": handler}) as client:
        sockets, (ctl, tv, phone) = connect(client, "controller", "screen", "review")
        try:
            visit_with_plan(ctl)
            events = generate_summary(ctl)
            checks = [e["payload"] for e in events if e["type"] == "summary.check"]
            assert [(c["attempt"], c["outcome"]) for c in checks] == [(1, "failed"), (2, "failed")]
            assert problem in {m["problem"] for m in checks[-1]["mismatches"]}
            assert events[-1]["payload"]["stage"] == "refused" and events[-1]["payload"]["detail"]
            assert "summary.ready" not in types(events)
            for ws in (tv, phone):
                seen = until_stage(ws, "summary.status", "refused")
                assert seen[-1]["payload"]["detail"] is None
                assert "summary.ready" not in types(seen)
                assert_public(seen)
            assert "summary" not in kinds(client) and visit(client).summary is None
            summary_id = checks[0]["summaryId"]
            assert client.get(f"/api/speech/{summary_id}.0", params={"language": "pa-IN"}).status_code == 404
            command(phone, "summary.read_aloud", summaryId=summary_id)
            assert drain_until(phone, "command.refused")[-1]["payload"]["reason"] == "not_current"
        finally:
            close(sockets)


def test_read_aloud_and_stop_reach_controllers_only_cdr_007(client):
    sockets, (ctl, tv, phone) = connect(client, "controller", "screen", "review")
    try:
        visit_with_plan(ctl)
        generate_summary(ctl)
        summary = drain_until(ctl, "summary.ready")[-1]["payload"]
        drain_until(phone, "summary.ready")
        command(phone, "summary.read_aloud", summaryId=summary["summaryId"])
        speak = drain_until(ctl, "summary.speak")[-1]["payload"]
        assert speak == {
            "summaryId": summary["summaryId"],
            "action": "play",
            "speechIds": [s["sentenceId"] for s in summary["sentences"]],
        }
        command(tv, "summary.read_aloud", summaryId=summary["summaryId"])  # dropped
        command(ctl, "summary.stop", summaryId=summary["summaryId"])
        stop = drain_until(ctl, "summary.speak")[-1]["payload"]
        assert stop["action"] == "stop"
        command(ctl, "summary.read_aloud", summaryId="old")
        assert drain_until(ctl, "error")[-1]["payload"]["command"] == "summary.read_aloud"
        ctl_events, (tv_events, phone_events) = marker(ctl, tv, phone)
        assert "summary.speak" not in types(ctl_events)  # the screen's copy did nothing
        assert_public(tv_events + phone_events)
    finally:
        close(sockets)


def test_appending_after_generation_marks_artefacts_stale_cdr_007(client):
    sockets, (ctl, tv) = connect(client, "controller", "screen")
    try:
        visit_with_plan(ctl)
        generate_note(ctl)
        drain_until(ctl, "note.ready")
        generate_summary(ctl)
        drain_until(ctl, "summary.ready")
        # The summary's own entry was appended after the note, so the note is already stale; the summary is not.
        stale = drain_until(ctl, "artefacts.stale")[-1]["payload"]
        assert stale["note"] is True and stale["summary"] is False
        drain_until(tv, "summary.ready")

        patient_says(ctl, CHEST_CORRECTED)
        stale = drain_until(ctl, "artefacts.stale")[-1]["payload"]
        assert stale == {"note": True, "summary": True, "headHash": visit(client).chain.head_hash}
        tv_stale = drain_until(tv, "artefacts.stale")
        assert [e["payload"] for e in tv_stale if e["type"] == "artefacts.stale"] == [
            {"note": False, "summary": True, "headHash": visit(client).chain.head_hash}
        ]
        # A stale summary can still be played, and the gate still serves it.
        summary = visit(client).summary
        assert client.get(f"/api/speech/{summary.summary_id}.0", params={"language": "pa-IN"}).status_code == 200
    finally:
        close(sockets)
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        state = ctl.receive_json()["payload"]
        assert state["noteStale"] is True and state["summaryStale"] is True

    # Regenerating refreshes it.
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        generate_summary(ctl)
        drain_until(ctl, "summary.ready")
        assert visit(client).summary_stale is False


def test_summary_entries_cannot_be_tampered_tdm_005(client):
    sockets, (ctl,) = connect(client, "controller")
    try:
        visit_with_plan(ctl)
        generate_summary(ctl)
        summary = drain_until(ctl, "summary.ready")[-1]["payload"]
        command(ctl, "demo.tamper_record", entryId=summary["summaryId"])
        assert "Only a turn" in drain_until(ctl, "error")[-1]["payload"]["message"]
        assert visit(client).tamper is None
    finally:
        close(sockets)
