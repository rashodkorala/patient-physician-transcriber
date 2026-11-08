"""Demo night server: visit channel, speech tokens, and the turn pipeline.

Run with the app factory so nothing loads on import: uvicorn main:create_app --factory

@implements ADR-001: Architecture: Python FastAPI server, Next.js front end, shared TV screen client
@implements ADR-003: Human interpreter escalation on low confidence and high-risk moments
@implements CDR-001: Visit WebSocket event contract
@implements CDR-003: Participant names and interpreter lines on the visit channel
@implements CDR-004: Interpreter voice playback on the visit channel
@implements IDR-001: Push-to-talk per speaker instead of diarisation
@implements TDM-003: Sinhala and Tamil as test-only languages before demo night
@implements TDM-004: Tamil is the chosen live language, alongside Punjabi and French, spoken by ElevenLabs
@implements ADR-010: Voice output: ElevenLabs Eleven v4 replaces OpenAI text-to-speech; Azure stays fallback
@contract ws:/ws/visit
@contract http:GET /api/speech/{speech_id}
@see openspec/tdr/adr/adr-001-system-architecture.md
"""

import asyncio
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from config import LIVE_MODEL, TONE_MODEL, Settings, load_settings
from contracts import (
    CONTROLLER_COMMANDS,
    TEST_LANGUAGES,
    ErrorPayload,
    InterpreterEscalation,
    InterpreterLine,
    Language,
    NameProposed,
    NameRef,
    NameReply,
    Names,
    SetLanguages,
    TurnRef,
    TurnStarted,
    TurnStatus,
    TurnSubmit,
    VoicePlayback,
    to_caption,
)
from empathy import EmpathyAdvisor
from graph.turn_graph import TurnPipeline
from introduction import ask_line, introduction_line, read_name, welcome_line
from kb.embeddings import make_embedder
from kb.store import KnowledgeBase
from llm import ClaudeModel, Model
from speech_token import SpeechNotConfigured, issue_token
from visit_store import Connection, Hub, Speech, TurnRecord, Visit
from voice import (
    DEFAULT_MODEL,
    DEFAULT_VOICE,
    LINE_DELIVERY,
    Delivery,
    ElevenLabsVoice,
    Voice,
    VoiceUnavailable,
    delivery_for,
)

# uvicorn prints this logger, so timing lines and errors show in the dev.sh output.
log = logging.getLogger("uvicorn.error")
ROLES = ("controller", "screen", "review")
# CDR-004: a speech whose end never arrives stops showing as speaking after this long.
VOICE_CEILING_S = 60.0


def make_model(settings: Settings) -> Model:
    if settings.translator == "claude":
        return ClaudeModel()
    from fake_model import fake_model

    return fake_model()


def make_voice(settings: Settings) -> Voice | None:
    if not settings.elevenlabs_api_key:
        return None
    return ElevenLabsVoice(
        settings.elevenlabs_api_key,
        voice_id=settings.elevenlabs_voice_id or DEFAULT_VOICE,
        model=settings.elevenlabs_model or DEFAULT_MODEL,
    )


def describe(settings: Settings) -> str:
    """One start-up line saying what this run will use, so a fake run is never mistaken for live."""
    translator = (
        f"Claude ({LIVE_MODEL}, tone check {TONE_MODEL})"
        if settings.translator == "claude"
        else "fake model (no AI calls)"
    )
    speech = "Azure" if settings.azure_speech_key and settings.azure_speech_region else "not configured"
    if settings.elevenlabs_api_key:
        speech += f", voice ElevenLabs ({settings.elevenlabs_model or DEFAULT_MODEL}) with Azure fallback"
    mode = " TEST MODE: Sinhala selectable (TDM-003), never use on stage." if settings.test_languages else ""
    return f"Translator: {translator}. Speech: {speech}.{mode}"


def create_app(
    model: Model | None = None,
    settings: Settings | None = None,
    kb: KnowledgeBase | None = None,
    voice: Voice | None = None,
    voice_ceiling_s: float = VOICE_CEILING_S,
) -> FastAPI:
    settings = settings or load_settings()
    log.info(describe(settings))
    model = model or make_model(settings)
    voice = voice or make_voice(settings)
    kb = kb or KnowledgeBase(make_embedder())
    pipeline = TurnPipeline(model, kb)
    advisor = EmpathyAdvisor(model, kb)

    app = FastAPI(title="Demo night server")
    # Screens load from the Next.js origin on the demo laptop or the local network.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    hub = Hub(Visit())
    app.state.hub = hub
    background: set[asyncio.Task] = set()
    app.state.background = background

    @app.get("/api/health")
    async def health() -> dict:
        return {
            "ok": True,
            "visitId": hub.visit.visit_id,
            "translator": settings.translator,
            # TDM-003: the controller shows its banner and the test languages from this; screens never ask.
            "testLanguages": settings.test_languages,
            "voice": "elevenlabs" if voice else "azure",
        }

    @app.get("/api/speech-token")
    async def speech_token() -> dict:
        try:
            return await issue_token(settings.azure_speech_key, settings.azure_speech_region)
        except SpeechNotConfigured as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    def speakable(speech_id: str, language: Language | None) -> tuple[str, Language, Delivery] | None:
        """What an id may say aloud: a settled final turn, a confirmed read-back, or an interpreter line.

        Blocked, escalated, rejected, and unsettled turns, and unknown ids, are never spoken.
        """
        visit = hub.visit
        record = visit.turns.get(speech_id)
        if record and record.result:
            result = record.result
            if (record.settled and result.status == "final") or record.readback_confirmed:
                return result.translation, result.target_language, delivery_for(result.emotion, result.certainty)
            return None
        line = visit.interpreter_lines.get(speech_id)
        if line:
            for part in line.lines:
                if part.language == language:
                    return part.text, part.language, LINE_DELIVERY
        return None

    @app.get("/api/speech/{speech_id}")
    async def speech(speech_id: str, language: Language | None = None) -> StreamingResponse:
        """404: never speak this. 503: speak it, but with the browser's Azure voice."""
        found = speakable(speech_id, language)
        if found is None:
            raise HTTPException(status_code=404, detail="Nothing to speak for that id")
        text, target, delivery = found
        if voice is None or not voice.supports(target):
            raise HTTPException(status_code=503, detail=f"No server voice for {target}")
        try:
            audio = await voice.stream(text, target, delivery)
        except VoiceUnavailable as exc:
            log.warning("server voice failed for %s, browser falls back to Azure: %s", speech_id, exc)
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return StreamingResponse(audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})

    async def error(conn: Connection, message: str, command: str | None = None) -> None:
        await hub.send_to(conn, "error", ErrorPayload(message=message, command=command).wire())

    async def status(turn_id: str, stage: str) -> None:
        record = hub.visit.turns.get(turn_id)
        if record:
            record.stage = stage
        await hub.publish("turn.status", TurnStatus(turn_id=turn_id, stage=stage).wire())

    async def set_languages(conn: Connection, payload: dict) -> None:
        cmd = SetLanguages.model_validate(payload)
        if hub.visit.turns:
            await error(conn, "Languages cannot change once the visit has a turn", "visit.set_languages")
            return
        if cmd.patient_language in TEST_LANGUAGES and not settings.test_languages:
            await error(conn, "This language is coming soon", "visit.set_languages")
            return
        hub.visit.patient_language = cmd.patient_language
        hub.visit.physician_language = cmd.physician_language
        await hub.publish_state()

    async def say(line: InterpreterLine) -> None:
        hub.visit.interpreter_lines[line.line_id] = line
        await hub.publish("interpreter.line", line.wire())

    async def advance_introduction() -> None:
        """Ask for the next unknown name, physician first, or welcome both once every name is known."""
        visit = hub.visit
        if not visit.physician_name:
            visit.introduction = "asking_physician"
            line = ask_line("physician", visit.physician_language, visit.patient_language, None)
        elif not visit.patient_name:
            visit.introduction = "asking_patient"
            line = ask_line("patient", visit.physician_language, visit.patient_language, visit.physician_name)
        else:
            visit.introduction = "done"
            line = welcome_line(visit.physician_language, visit.patient_language, visit.patient_name)
        await hub.publish_state()
        await say(line)

    async def start_introduction(conn: Connection, payload: dict) -> None:
        visit = hub.visit
        if visit.turns:
            await error(conn, "The introduction is only offered before the first turn", "visit.start_introduction")
            return
        if visit.introduction != "pending":
            await error(conn, "The introduction has already started", "visit.start_introduction")
            return
        await say(introduction_line(visit.physician_language, visit.patient_language))
        await advance_introduction()

    async def name_reply(conn: Connection, payload: dict) -> None:
        cmd = NameReply.model_validate(payload)
        visit = hub.visit
        if visit.introduction != f"asking_{cmd.role}":
            await error(conn, f"The interpreter is not asking for the {cmd.role}'s name", "visit.name_reply")
            return
        try:
            name = await read_name(model, cmd.role, cmd.text)
        except Exception:
            log.exception("name extraction failed")
            name = None
        if not name:
            await error(conn, "No name was heard. Ask again or type the name.", "visit.name_reply")
            return
        visit.proposed_names[cmd.role] = name
        await hub.publish("visit.name_proposed", NameProposed(role=cmd.role, name=name).wire())

    async def name_decision(conn: Connection, payload: dict, confirmed: bool) -> None:
        cmd = NameRef.model_validate(payload)
        visit = hub.visit
        command = "visit.name_confirm" if confirmed else "visit.name_reject"
        name = visit.proposed_names.pop(cmd.role, None)
        if name is None or visit.introduction != f"asking_{cmd.role}":
            await error(conn, f"No {cmd.role} name is waiting for confirmation", command)
            return
        if not confirmed:
            # Ask again; the physician can also type the name instead.
            await say(ask_line(cmd.role, visit.physician_language, visit.patient_language, visit.physician_name))
            return
        setattr(visit, f"{cmd.role}_name", name)
        await hub.publish("visit.names", visit.names().wire())
        await advance_introduction()

    async def set_names(conn: Connection, payload: dict) -> None:
        # Allowed at any time; earlier turns keep the names they were relayed with (CDR-003).
        cmd = Names.model_validate(payload)
        visit = hub.visit
        if "physician_name" in cmd.model_fields_set:
            visit.physician_name = cmd.physician_name
        if "patient_name" in cmd.model_fields_set:
            visit.patient_name = cmd.patient_name
        await hub.publish("visit.names", visit.names().wire())
        # A name typed while the interpreter is asking for it answers the question.
        asking = {"asking_physician": visit.physician_name, "asking_patient": visit.patient_name}
        if asking.get(visit.introduction):
            visit.proposed_names.clear()
            await advance_introduction()

    async def send_nudge(turn_id: str, emotion: str, text_en: str) -> None:
        try:
            nudge = await advisor.nudge(turn_id, emotion, text_en)  # type: ignore[arg-type]
        except Exception:
            log.exception("empathy nudge failed")
            return
        if nudge:
            hub.visit.nudges.append(nudge)
            await hub.publish("empathy.nudge", nudge.wire())

    async def submit_turn(conn: Connection, payload: dict) -> None:
        cmd = TurnSubmit.model_validate(payload)
        visit = hub.visit
        if visit.pending_readback:
            await error(conn, "Confirm or reject the highlighted dose before the next turn", "turn.submit")
            return
        patient, physician = visit.patient_language, visit.physician_language
        if cmd.language not in (patient, physician):
            await error(conn, f"{cmd.language} is not a language of this visit", "turn.submit")
            return
        target = physician if cmd.language == patient else patient
        if visit.introduction in ("pending", "asking_physician", "asking_patient"):
            # Speaking is how the physician skips the introduction, before or part way through it.
            visit.introduction = "skipped"
            visit.proposed_names.clear()
            await hub.publish_state()

        turn_id = uuid.uuid4().hex[:10]
        record = TurnRecord(result=None, speaker=cmd.speaker, source_text=cmd.text, stage="listening")
        visit.turns[turn_id] = record
        visit.current_turn_id = turn_id
        await hub.publish(
            "turn.started", TurnStarted(turn_id=turn_id, speaker=cmd.speaker, language=cmd.language).wire()
        )

        started = time.perf_counter()
        try:
            result, reason = await pipeline.run(
                turn_id=turn_id,
                speaker=cmd.speaker,
                source=cmd.language,
                target=target,
                text=cmd.text,
                recognition_confidence=cmd.recognition_confidence,
                physician_name=visit.physician_name,
                patient_name=visit.patient_name,
                emit=lambda stage: status(turn_id, stage),
            )
        except Exception as exc:  # refusal or API failure: nothing is spoken
            log.exception("turn pipeline failed")
            await status(turn_id, "failed")
            await error(conn, f"Translation failed: {exc}", "turn.submit")
            return
        log.info(
            "turn %s %s, attempts %d, in %.2fs", turn_id, result.status, result.attempts, time.perf_counter() - started
        )

        record.result = result
        await hub.publish("turn.analysis", result.wire())

        if result.status == "readback_required":
            visit.pending_readback = turn_id
            await hub.publish("turn.readback_required", TurnRef(turn_id=turn_id).wire())
            await status(turn_id, "awaiting_readback")
            return

        # final, blocked, or escalated: the turn is settled and shared screens may show it.
        record.settled = True
        record.stage = {"final": "spoken"}.get(result.status, result.status)
        await hub.publish("turn.result", to_caption(result).wire())
        if result.status == "escalated" and reason:
            await hub.publish("interpreter.escalation", InterpreterEscalation(reason=reason, turn_id=turn_id).wire())  # type: ignore[arg-type]
        if result.status == "final" and result.speaker == "patient":
            task = asyncio.create_task(send_nudge(turn_id, result.emotion, result.translation))
            background.add(task)
            task.add_done_callback(background.discard)

    async def readback(conn: Connection, payload: dict, confirmed: bool) -> None:
        ref = TurnRef.model_validate(payload)
        visit = hub.visit
        command = "turn.readback_confirm" if confirmed else "turn.readback_reject"
        if visit.pending_readback != ref.turn_id:
            await error(conn, "No dose is waiting for confirmation on that turn", command)
            return
        record = visit.turns[ref.turn_id]
        visit.pending_readback = None
        if not confirmed:
            # Discarded unspoken; the speaker repeats (covers recognition errors).
            await status(ref.turn_id, "discarded")
            return
        record.settled = True
        record.readback_confirmed = True
        record.stage = "spoken"
        await hub.publish("turn.result", to_caption(record.result, readback_confirmed=True).wire())  # type: ignore[arg-type]

    # ---------- CDR-004: interpreter voice playback ----------

    async def set_speech(speech: Speech | None) -> None:
        hub.visit.speech = speech
        await hub.publish("voice.speaking", hub.visit.speaking().wire())

    async def clear_after_ceiling(speech: Speech) -> None:
        await asyncio.sleep(voice_ceiling_s)
        if hub.visit.speech is speech:
            log.warning("no voice.ended for %s within %.0f s; showing silent", speech.speech_id, voice_ceiling_s)
            await set_speech(None)

    async def voice_started(conn: Connection, payload: dict) -> None:
        cmd = VoicePlayback.model_validate(payload)
        # The same gate as GET /api/speech/{id}, so nothing that may not be spoken can show as speaking.
        found = speakable(cmd.speech_id, cmd.language)
        if found is None or found[1] != cmd.language:
            await error(conn, "Nothing may be spoken for that id in that language", "voice.started")
            return
        current = hub.visit.speech
        if current and current.is_(cmd.speech_id, cmd.language):
            return
        speech = Speech(speech_id=cmd.speech_id, language=cmd.language, conn=conn)
        await set_speech(speech)
        task = asyncio.create_task(clear_after_ceiling(speech))
        background.add(task)
        task.add_done_callback(background.discard)

    async def voice_ended(conn: Connection, payload: dict) -> None:
        cmd = VoicePlayback.model_validate(payload)
        current = hub.visit.speech
        # The controller's queue can end a speech after a newer one started; only the current one counts.
        if current and current.is_(cmd.speech_id, cmd.language):
            await set_speech(None)

    handlers = {
        "visit.set_languages": set_languages,
        "visit.set_names": set_names,
        "visit.start_introduction": start_introduction,
        "visit.name_reply": name_reply,
        "visit.name_confirm": lambda conn, payload: name_decision(conn, payload, True),
        "visit.name_reject": lambda conn, payload: name_decision(conn, payload, False),
        "turn.submit": submit_turn,
        "turn.readback_confirm": lambda conn, payload: readback(conn, payload, True),
        "turn.readback_reject": lambda conn, payload: readback(conn, payload, False),
        "voice.started": voice_started,
        "voice.ended": voice_ended,
    }

    @app.websocket("/ws/visit")
    async def visit_channel(ws: WebSocket) -> None:
        role = ws.query_params.get("role", "screen")
        if role not in ROLES:
            await ws.close(code=4400)
            return
        await ws.accept()
        conn = hub.add(ws, role)  # type: ignore[arg-type]
        await hub.send_state(conn)
        try:
            while True:
                message = await ws.receive_json()
                command = message.get("type", "")
                if command in CONTROLLER_COMMANDS and conn.role != "controller":
                    continue  # screens may not send controller commands
                handler = handlers.get(command)
                if handler is None:
                    await error(conn, f"Unsupported command: {command}", command)
                    continue
                try:
                    await handler(conn, message.get("payload", {}))
                except ValidationError as exc:
                    await error(conn, f"Invalid payload: {exc.errors()[0]['msg']}", command)
        except WebSocketDisconnect:
            pass
        finally:
            hub.remove(conn)
            # A controller that drops off mid-speech can never report the end, so the speech ends with it.
            if hub.visit.speech is not None and hub.visit.speech.conn is conn:
                await set_speech(None)

    return app
