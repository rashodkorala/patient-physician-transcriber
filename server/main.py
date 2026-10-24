"""Demo night server: visit channel, speech tokens, and the week 1 translation path.

@implements ADR-001: Architecture: Python FastAPI server, Next.js front end, shared TV screen client
@implements CDR-001: Visit WebSocket event contract
@implements IDR-001: Push-to-talk per speaker instead of diarisation
@contract ws:/ws/visit
@see openspec/tdr/adr/adr-001-system-architecture.md
"""

import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from config import Settings, load_settings
from contracts import (
    CONTROLLER_COMMANDS,
    ErrorPayload,
    SetLanguages,
    TurnResult,
    TurnStarted,
    TurnStatus,
    TurnSubmit,
    to_caption,
)
from speech_token import SpeechNotConfigured, issue_token
from translate import ClaudeTranslator, FakeTranslator, Translator
from visit_store import Connection, Hub, TurnRecord, Visit

ROLES = ("controller", "screen", "review")


def make_translator(settings: Settings) -> Translator:
    return ClaudeTranslator() if settings.translator == "claude" else FakeTranslator()


def create_app(translator: Translator | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Demo night server")
    # Screens load from the Next.js origin on the demo laptop or the local network.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    hub = Hub(Visit())
    app.state.hub = hub
    app.state.translator = translator or make_translator(settings)

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

    async def set_languages(conn: Connection, payload: dict) -> None:
        cmd = SetLanguages.model_validate(payload)
        if hub.visit.turns:
            await error(conn, "Languages cannot change once the visit has a turn", "visit.set_languages")
            return
        hub.visit.patient_language = cmd.patient_language
        hub.visit.physician_language = cmd.physician_language
        await hub.publish_state()

    async def submit_turn(conn: Connection, payload: dict) -> None:
        cmd = TurnSubmit.model_validate(payload)
        visit = hub.visit
        patient, physician = visit.patient_language, visit.physician_language
        if cmd.language not in (patient, physician):
            await error(conn, f"{cmd.language} is not a language of this visit", "turn.submit")
            return
        target = physician if cmd.language == patient else patient

        turn_id = uuid.uuid4().hex[:10]
        record = TurnRecord(result=None, speaker=cmd.speaker, source_text=cmd.text, stage="translating")
        visit.turns[turn_id] = record
        visit.current_turn_id = turn_id
        await hub.publish("turn.started", TurnStarted(turn_id=turn_id, speaker=cmd.speaker, language=cmd.language).wire())
        await hub.publish("turn.status", TurnStatus(turn_id=turn_id, stage="translating").wire())

        try:
            out = await app.state.translator.translate(cmd.text, cmd.language, target, cmd.speaker)
        except Exception as exc:  # refusal or API failure: nothing is spoken
            record.stage = "failed"
            await hub.publish("turn.status", TurnStatus(turn_id=turn_id, stage="failed").wire())
            await error(conn, f"Translation failed: {exc}", "turn.submit")
            return

        # Week 1 plain path: no critical value checks yet (task 2.6), so every turn is final.
        result = TurnResult(
            turn_id=turn_id,
            speaker=cmd.speaker,
            source_language=cmd.language,
            target_language=target,  # type: ignore[arg-type]
            source_text=cmd.text,
            translation=out.translation,
            back_translation=out.back_translation,
            tone_tags=out.tone_tags,
            emotion=out.emotion,
            certainty=out.certainty,
            glossary_used=[],
            critical_values=[],
            confidence=out.confidence,
            status="final",
            attempts=1,
        )
        record.result = result
        record.stage = "spoken"
        record.settled = True
        await hub.publish("turn.analysis", result.wire())
        # The controller speaks the translation when this public caption arrives.
        await hub.publish("turn.result", to_caption(result).wire())

    handlers = {"visit.set_languages": set_languages, "turn.submit": submit_turn}

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
                    continue  # silently ignored: screens may not send controller commands
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


app = create_app()
