"""Server voice tests: what /api/speech/{id} will and will not speak, the delivery table, and the
ElevenLabs adapter's fallback signal (ADR-010, CDR-003, mediator-voice tasks 3.1, 3.2, and 3.4)."""

import asyncio
from typing import get_args

import pytest
from fastapi.testclient import TestClient
from test_visit_channel import DOSE, SETTINGS, drain_until, drain_until_stage, submit

import fake_model
from contracts import Certainty, Emotion
from graph.turn_graph import Draft, ToneCheck
from kb.embeddings import HashingEmbedder
from kb.store import KnowledgeBase
from llm import ScriptedModel
from main import create_app
from voice import (
    EMOTION_DELIVERY,
    LINE_DELIVERY,
    ElevenLabsVoice,
    VoiceUnavailable,
    delivery_for,
    describe_error,
    spoken_text,
)


class FakeVoice:
    """Records what it was asked to say; speaks every language but Sinhala, like ElevenLabs."""

    name = "fake"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.said: list[tuple[str, str, object]] = []

    def supports(self, language):
        return language != "si-LK"

    async def stream(self, text, language, delivery):
        if self.fail:
            raise VoiceUnavailable("vendor down")
        self.said.append((text, language, delivery))

        async def chunks():
            yield b"ID3"
            yield b"audio"

        return chunks()


@pytest.fixture(scope="module")
def kb():
    return KnowledgeBase(HashingEmbedder())


def make_client(kb, voice=None, translate=None, tone_check=None, settings=SETTINGS):
    model = ScriptedModel(
        {
            "translate": translate or fake_model.translate,
            "tone_check": tone_check or fake_model.tone_check,
            "empathy": fake_model.empathy,
            "name_extract": fake_model.name_extract,
        }
    )
    return TestClient(create_app(model=model, settings=settings, kb=kb, voice=voice))


def final_turn(client, text="Hello, how are you feeling today?"):
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        submit(ctl, "physician", "en-CA", text)
        return drain_until(ctl, "turn.result")[-1]["payload"]


# ---------- what may be spoken (task 3.1) ----------


def test_final_turn_streams_its_translation_with_its_delivery(kb):
    voice = FakeVoice()
    with make_client(kb, voice) as client:
        caption = final_turn(client)
        response = client.get(f"/api/speech/{caption['turnId']}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg" and response.content == b"ID3audio"
        text, language, delivery = voice.said[0]
        assert text == caption["translation"] and language == "pa-IN"
        assert delivery in {delivery_for(e, c) for e in get_args(Emotion) for c in get_args(Certainty)}


def test_confirmed_readback_is_spoken_and_unsettled_or_rejected_is_not(kb):
    voice = FakeVoice()
    with make_client(kb, voice) as client, client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        submit(ctl, "physician", "en-CA", DOSE)
        waiting = drain_until_stage(ctl, "awaiting_readback")[-1]["payload"]["turnId"]
        assert client.get(f"/api/speech/{waiting}").status_code == 404  # unsettled
        ctl.send_json({"type": "turn.readback_confirm", "payload": {"turnId": waiting}})
        drain_until(ctl, "turn.result")
        assert client.get(f"/api/speech/{waiting}").status_code == 200

        submit(ctl, "physician", "en-CA", DOSE)
        rejected = drain_until_stage(ctl, "awaiting_readback")[-1]["payload"]["turnId"]
        ctl.send_json({"type": "turn.readback_reject", "payload": {"turnId": rejected}})
        drain_until_stage(ctl, "discarded")
        assert client.get(f"/api/speech/{rejected}").status_code == 404
    assert len(voice.said) == 1


def test_blocked_turn_is_never_spoken(kb):
    def wrong(user):
        d = fake_model.translate(user)
        return Draft(**{**d.model_dump(), "translation": d.translation.replace("0.4", "4")})

    voice = FakeVoice()
    with make_client(kb, voice, translate=wrong) as client:
        caption = final_turn(client, DOSE)
        assert caption["status"] == "blocked"
        assert client.get(f"/api/speech/{caption['turnId']}").status_code == 404
    assert voice.said == []


def test_escalated_turn_is_never_spoken(kb):
    def failing(user):
        return ToneCheck(meaning_preserved=True, certainty_preserved=False, warmth_preserved=True, issue="x")

    voice = FakeVoice()
    with make_client(kb, voice, tone_check=failing) as client:
        caption = final_turn(client, "This is very unlikely to be serious.")
        assert caption["status"] == "escalated"
        assert client.get(f"/api/speech/{caption['turnId']}").status_code == 404
    assert voice.said == []


def test_unknown_id_is_never_spoken(kb):
    with make_client(kb, FakeVoice()) as client:
        assert client.get("/api/speech/not-a-turn").status_code == 404


def test_interpreter_line_is_spoken_per_language(kb):
    voice = FakeVoice()
    with make_client(kb, voice) as client, client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        ctl.send_json({"type": "visit.start_introduction", "payload": {}})
        line = drain_until(ctl, "interpreter.line")[-1]["payload"]
        for part in line["lines"]:
            assert client.get(f"/api/speech/{line['lineId']}?language={part['language']}").status_code == 200
        assert client.get(f"/api/speech/{line['lineId']}").status_code == 404  # which language?
        assert client.get(f"/api/speech/{line['lineId']}?language=fr-CA").status_code == 404  # not in this line
    assert [(t, lang) for t, lang, _ in voice.said] == [(p["text"], p["language"]) for p in line["lines"]]
    assert all(d == LINE_DELIVERY for _, _, d in voice.said)


# ---------- falling back to Azure ----------


def test_no_server_voice_means_the_browser_uses_azure(kb):
    with make_client(kb, voice=None) as client:
        caption = final_turn(client)
        assert client.get(f"/api/speech/{caption['turnId']}").status_code == 503
        assert client.get("/api/health").json()["voice"] == "azure"


def test_vendor_failure_means_the_browser_uses_azure(kb):
    with make_client(kb, FakeVoice(fail=True)) as client:
        caption = final_turn(client)
        assert client.get(f"/api/speech/{caption['turnId']}").status_code == 503


def test_sinhala_has_no_server_voice(kb):
    settings = SETTINGS.__class__(**{**SETTINGS.__dict__, "test_languages": True})
    voice = FakeVoice()
    with (
        make_client(kb, voice, settings=settings) as client,
        client.websocket_connect("/ws/visit?role=controller") as ctl,
    ):
        ctl.receive_json()
        ctl.send_json(
            {"type": "visit.set_languages", "payload": {"patientLanguage": "si-LK", "physicianLanguage": "en-CA"}}
        )
        drain_until(ctl, "visit.state")
        submit(ctl, "physician", "en-CA", "Hello, how are you feeling today?")
        caption = drain_until(ctl, "turn.result")[-1]["payload"]
        assert caption["targetLanguage"] == "si-LK"
        assert client.get(f"/api/speech/{caption['turnId']}").status_code == 503
    assert voice.said == []


# ---------- delivery table (task 3.2) ----------


def test_every_emotion_and_certainty_has_a_delivery():
    assert set(EMOTION_DELIVERY) == set(get_args(Emotion))
    for emotion in get_args(Emotion):
        for certainty in get_args(Certainty):
            delivery = delivery_for(emotion, certainty)
            assert delivery.tag.startswith("[") and delivery.tag.endswith("]")
            assert 0.0 <= delivery.stability <= 1.0


def test_certain_content_is_said_more_steadily_never_less():
    for emotion in get_args(Emotion):
        assert delivery_for(emotion, "high").stability >= delivery_for(emotion, "low").stability


def test_tag_leads_and_text_brackets_cannot_act_as_tags():
    said = spoken_text("Take [two] tablets", delivery_for("worried", "high"))
    assert said == "[gently] Take (two) tablets"


# ---------- ElevenLabs adapter ----------


class FakeTextToSpeech:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[dict] = []

    def stream(self, voice_id, **kwargs):
        self.calls.append({"voice_id": voice_id, **kwargs})

        async def chunks():
            if self.error:
                raise self.error
            yield b"one"
            yield b"two"

        return chunks()


def adapter(tts):
    voice = ElevenLabsVoice("test-key", voice_id="voice-1", model="eleven_v4")
    voice.tts = tts
    return voice


async def collect(chunks):
    return b"".join([c async for c in chunks])


@pytest.mark.anyio
async def test_adapter_sends_language_tag_and_stability():
    tts = FakeTextToSpeech()
    audio = await adapter(tts).stream("Bonjour", "fr-CA", delivery_for("calm", "high"))
    assert await collect(audio) == b"onetwo"
    call = tts.calls[0]
    assert call["voice_id"] == "voice-1" and call["model_id"] == "eleven_v4" and call["language_code"] == "fr"
    assert call["text"] == "[calm] Bonjour"
    assert call["voice_settings"].stability == pytest.approx(0.6)


@pytest.mark.anyio
async def test_adapter_fails_before_any_audio_so_the_browser_can_fall_back():
    with pytest.raises(VoiceUnavailable):
        await adapter(FakeTextToSpeech(error=RuntimeError("401"))).stream("Hi", "en-CA", LINE_DELIVERY)


@pytest.mark.anyio
async def test_adapter_refuses_sinhala():
    with pytest.raises(VoiceUnavailable):
        await adapter(FakeTextToSpeech()).stream("ආයුබෝවන්", "si-LK", LINE_DELIVERY)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_adapter_queues_beyond_the_plan_limit_and_frees_slots():
    voice = adapter(FakeTextToSpeech())
    voice.slots = asyncio.Semaphore(1)
    first = await voice.stream("One", "en-CA", LINE_DELIVERY)
    assert voice.slots.locked()  # held while the first stream is open
    await collect(first)
    assert not voice.slots.locked()  # freed once it ends
    with pytest.raises(VoiceUnavailable):
        await adapter(FakeTextToSpeech(error=RuntimeError("down"))).stream("Two", "en-CA", LINE_DELIVERY)


def test_vendor_error_is_reported_without_headers():
    error = Exception("headers: {...}")
    error.status_code = 429
    error.body = {"detail": {"message": "Too many concurrent requests."}}
    assert describe_error(error) == "429 Too many concurrent requests."
