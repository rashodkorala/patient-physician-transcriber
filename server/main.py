"""Demo night server: visit channel, speech tokens, and the turn pipeline.

Run with the app factory so nothing loads on import: uvicorn main:create_app --factory

@implements ADR-001: Architecture: Python FastAPI server, Next.js front end, shared TV screen client
@implements ADR-003: Human interpreter escalation on low confidence and high-risk moments
@implements CDR-001: Visit WebSocket event contract
@implements IDR-001: Push-to-talk per speaker instead of diarisation
@contract ws:/ws/visit
@see openspec/tdr/adr/adr-001-system-architecture.md
"""

import asyncio
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from config import LIVE_MODEL, TONE_MODEL, Settings, load_settings
from contracts import (
    CONTROLLER_COMMANDS,
    ErrorPayload,
    InterpreterEscalation,
    SetLanguages,
    TurnRef,
    TurnStarted,
    TurnStatus,
    TurnSubmit,
    to_caption,
)
from empathy import EmpathyAdvisor
from graph.turn_graph import TurnPipeline
from kb.embeddings import make_embedder
from kb.store import KnowledgeBase
from llm import ClaudeModel, Model
from speech_token import SpeechNotConfigured, issue_token
from visit_store import Connection, Hub, TurnRecord, Visit

# uvicorn prints this logger, so timing lines and errors show in the dev.sh output.
log = logging.getLogger("uvicorn.error")
ROLES = ("controller", "screen", "review")


def make_model(settings: Settings) -> Model:
    if settings.translator == "claude":
        return ClaudeModel()
    from fake_model import fake_model

    return fake_model()


def describe(settings: Settings) -> str:
    """One start-up line saying what this run will use, so a fake run is never mistaken for live."""
    translator = (
        f"Claude ({LIVE_MODEL}, tone check {TONE_MODEL})"
        if settings.translator == "claude"
        else "fake model (no AI calls)"
    )
    speech = "Azure" if settings.azure_speech_key and settings.azure_speech_region else "not configured"
    return f"Translator: {translator}. Speech: {speech}."


def create_app(
    model: Model | None = None, settings: Settings | None = None, kb: KnowledgeBase | None = None
) -> FastAPI:
    settings = settings or load_settings()
    log.info(describe(settings))
    model = model or make_model(settings)
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
        return {"ok": True, "visitId": hub.visit.visit_id, "translator": settings.translator}

    @app.get("/api/speech-token")
    async def speech_token() -> dict:
        try:
            return await issue_token(settings.azure_speech_key, settings.azure_speech_region)
        except SpeechNotConfigured as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

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
        hub.visit.patient_language = cmd.patient_language
        hub.visit.physician_language = cmd.physician_language
        await hub.publish_state()

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

    handlers = {
        "visit.set_languages": set_languages,
        "turn.submit": submit_turn,
        "turn.readback_confirm": lambda conn, payload: readback(conn, payload, True),
        "turn.readback_reject": lambda conn, payload: readback(conn, payload, False),
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

    return app
