"""Server voice tests: what /api/speech/{id} will and will not speak, the one constant delivery for every turn and
interpreter line (IDR-006, MDD-006), and the ElevenLabs adapter's fallback signal (ADR-010, CDR-003,
mediator-voice tasks 3.1 and 3.4, affect-in-words task 1.1)."""

import asyncio
from itertools import islice
from typing import get_args

import pytest
from test_visit_channel import DOSE, SETTINGS, ConsentedClient, drain_until, drain_until_stage, submit

import fake_model
from contracts import Certainty, Emotion, Manner
from graph.turn_graph import Draft, ToneCheck
from kb.embeddings import HashingEmbedder
from kb.store import KnowledgeBase
from llm import ScriptedModel
from main import create_app
from voice import ElevenLabsVoice, VoiceUnavailable, describe_error, spoken_text


class FakeVoice:
    """Records what it was asked to say; speaks every language but Sinhala, like ElevenLabs."""

    name = "fake"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.said: list[tuple[str, str]] = []

    def supports(self, language):
        return language != "si-LK"

    async def stream(self, text, language):
        if self.fail:
            raise VoiceUnavailable("vendor down")
        self.said.append((text, language))

        async def chunks():
            yield b"ID3"
            yield b"audio"

        return chunks()


@pytest.fixture(scope="module")
def kb():
    return KnowledgeBase(HashingEmbedder())


def make_client(kb, voice=None, translate=None, tone_check=None, settings=SETTINGS, language="pa-IN"):
    model = ScriptedModel(
        {
            "translate": translate or fake_model.translate,
            "tone_check": tone_check or fake_model.tone_check,
            "trust": fake_model.trust,
            "name_extract": fake_model.name_extract,
        }
    )
    return ConsentedClient(
        create_app(model=model, settings=settings, kb=kb, voice=voice, model_tone_check=tone_check is not None),
        language=language,
    )


def final_turn(client, text="Hello, how are you feeling today?"):
    with client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        submit(ctl, "physician", "en-CA", text)
        return drain_until(ctl, "turn.result")[-1]["payload"]


# ---------- what may be spoken (task 3.1) ----------


def test_final_turn_streams_its_translation(kb):
    voice = FakeVoice()
    with make_client(kb, voice) as client:
        caption = final_turn(client)
        response = client.get(f"/api/speech/{caption['turnId']}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg" and response.content == b"ID3audio"
        assert voice.said == [(caption["translation"], "pa-IN")]


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
    assert voice.said == [(p["text"], p["language"]) for p in line["lines"]]


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
        make_client(kb, voice, settings=settings, language="si-LK") as client,
        client.websocket_connect("/ws/visit?role=controller") as ctl,
    ):
        ctl.receive_json()
        submit(ctl, "physician", "en-CA", "Hello, how are you feeling today?")
        caption = drain_until(ctl, "turn.result")[-1]["payload"]
        assert caption["targetLanguage"] == "si-LK"
        assert client.get(f"/api/speech/{caption['turnId']}").status_code == 503
    assert voice.said == []


# ---------- one constant delivery (IDR-006) ----------


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


def reads(*values):
    """Cycles each list of values together until the longest has been used once, so every value appears."""
    longest = max(len(v) for v in values)
    return list(islice(zip(*(v * longest for v in values), strict=True), longest))


def test_every_turn_and_interpreter_line_gets_the_one_constant_delivery_idr_006(kb):
    """Every speaker, manner, emotion, and certainty, and an introduction, a name question, and a signal line,
    reach the vendor in the identical delivery: the same tag and the same stability (IDR-006, MDD-006)."""
    combos = reads(list(get_args(Manner)), list(get_args(Emotion)), list(get_args(Certainty)))
    current = {}

    def translate(user):
        draft = fake_model.translate(user)
        return Draft(**{**draft.model_dump(), **current})

    tts = FakeTextToSpeech()
    spoken = []

    def speak_lines(client, lines):
        for line in lines:
            for part in line["lines"]:
                assert client.get(f"/api/speech/{line['lineId']}?language={part['language']}").status_code == 200
                spoken.append(part["text"])

    # The introduction and the physician's name question, in a visit of their own: turns wait until it ends.
    with make_client(kb, adapter(tts)) as client, client.websocket_connect("/ws/visit?role=controller") as ctl:
        ctl.receive_json()
        ctl.send_json({"type": "visit.start_introduction", "payload": {}})
        lines = [drain_until(ctl, "interpreter.line")[-1]["payload"] for _ in range(2)]
        assert [line["purpose"] for line in lines] == ["introduction", "ask_physician_name"]
        speak_lines(client, lines)
    with (
        make_client(kb, adapter(tts), translate=translate) as client,
        client.websocket_connect("/ws/visit?role=controller") as ctl,
        client.websocket_connect("/ws/visit?role=review") as review,
    ):
        ctl.receive_json(), review.receive_json()
        for speaker, language in (("physician", "en-CA"), ("patient", "pa-IN"), ("companion", "pa-IN")):
            for manner, emotion, certainty in combos:
                current.update(manner=manner, emotion=emotion, certainty=certainty)
                submit(ctl, speaker, language, "Hello, how are you feeling today?")
                caption = drain_until(ctl, "turn.result")[-1]["payload"]
                assert caption["status"] == "final"
                assert client.get(f"/api/speech/{caption['turnId']}").status_code == 200
                spoken.append(caption["translation"])
        review.send_json({"type": "patient.signal", "payload": {"signal": "not_understood"}})
        line = drain_until(ctl, "interpreter.line")[-1]["payload"]
        assert line["purpose"] == "signal_not_understood"
        speak_lines(client, [line])
    assert len(tts.calls) == len(spoken) == 3 * len(combos) + 4
    for call, text in zip(tts.calls, spoken, strict=True):
        assert call["text"] == spoken_text(text)
        assert call["voice_settings"].stability == pytest.approx(0.55)


def test_text_brackets_cannot_act_as_performance_tags_idr_006():
    assert spoken_text("Take [two] tablets") == "Take (two) tablets"


@pytest.mark.anyio
async def test_adapter_sends_language_tag_and_stability():
    tts = FakeTextToSpeech()
    audio = await adapter(tts).stream("Bonjour", "fr-CA")
    assert await collect(audio) == b"onetwo"
    call = tts.calls[0]
    assert call["voice_id"] == "voice-1" and call["model_id"] == "eleven_v4" and call["language_code"] == "fr"
    assert call["text"] == "Bonjour"
    assert call["voice_settings"].stability == pytest.approx(0.55)


@pytest.mark.anyio
async def test_adapter_fails_before_any_audio_so_the_browser_can_fall_back():
    with pytest.raises(VoiceUnavailable):
        await adapter(FakeTextToSpeech(error=RuntimeError("401"))).stream("Hi", "en-CA")


@pytest.mark.anyio
async def test_adapter_refuses_sinhala():
    with pytest.raises(VoiceUnavailable):
        await adapter(FakeTextToSpeech()).stream("ආයුබෝවන්", "si-LK")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_adapter_queues_beyond_the_plan_limit_and_frees_slots():
    voice = adapter(FakeTextToSpeech())
    voice.slots = asyncio.Semaphore(1)
    first = await voice.stream("One", "en-CA")
    assert voice.slots.locked()  # held while the first stream is open
    await collect(first)
    assert not voice.slots.locked()  # freed once it ends
    with pytest.raises(VoiceUnavailable):
        await adapter(FakeTextToSpeech(error=RuntimeError("down"))).stream("Two", "en-CA")


def test_vendor_error_is_reported_without_headers():
    error = Exception("headers: {...}")
    error.status_code = 429
    error.body = {"detail": {"message": "Too many concurrent requests."}}
    assert describe_error(error) == "429 Too many concurrent requests."
