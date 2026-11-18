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
@implements TDM-002: Presenter mismatch control for the blocked-dose beat
@implements CDR-005: Consent and explain-back on the visit channel
@implements CDR-006: Record chain entries, review corrections, interpreter dismissal, and presenter controls
@implements IDR-003: SHA-256 hash chain for the record-verified badge
@implements CDR-007: Clinical note with provenance and patient summary on the visit channel
@implements ADR-011: Explain-back, note, and summary: frozen sources, model proposes, code checks provenance and values
@implements ADR-006: LLM: Claude Sonnet 5.5 for live turns, Opus 5.5 for note and summary
@implements TDM-005: Hidden record-tamper control for the demo
@implements MDD-005: Trust across the barrier
@implements CDR-008: Patient signals, manner, trust updates, companion turns, and the closing check on the visit channel
@implements IDR-005: Manner vocabulary and voice delivery
@implements MDD-006: Affect in words
@implements IDR-006: Affect phrase in the reporting frame, and one constant voice delivery
@contract ws:/ws/visit
@contract http:GET /api/speech/{speech_id}
@see openspec/tdr/adr/adr-001-system-architecture.md
@see openspec/tdr/cdr/cdr-005-consent-and-explain-back-events.md
@see openspec/tdr/cdr/cdr-006-record-entries-review-corrections-and-tamper.md
@see openspec/tdr/cdr/cdr-007-clinical-note-and-patient-summary.md
@see openspec/tdr/cdr/cdr-008-patient-voice-manner-and-trust-events.md
@see openspec/tdr/tdm/tdm-005-hidden-record-tamper-control.md
"""

import asyncio
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from chains.checks import GenerationFailed
from chains.explain_back import check_explain_back
from chains.note import generate_note
from chains.summary import generate_summary
from config import LIVE_MODEL, RECORD_MODEL, TONE_MODEL, Settings, load_settings
from contracts import (
    CONTROLLER_COMMANDS,
    REVIEW_COMMANDS,
    REVIEW_OR_CONTROLLER_COMMANDS,
    TEST_LANGUAGES,
    AmendmentEntryBody,
    ArtefactsStale,
    ArtefactStatus,
    CommandRefused,
    ConfirmationEntryBody,
    ConsentBy,
    ConsentEntryBody,
    ConsentGive,
    ConsentNotice,
    ConsentSpeak,
    ConsentState,
    ConsentWithdraw,
    DemoInjectionState,
    ErrorPayload,
    EscalationEntry,
    EscalationReason,
    ExplainBackRef,
    ExplainBackResultBody,
    ExplainBackState,
    InterpreterDismiss,
    InterpreterDismissed,
    InterpreterEscalation,
    InterpreterLine,
    Language,
    MarkHighRisk,
    NameProposed,
    NameRef,
    NameReply,
    Names,
    PatientSignalCommand,
    PatientSignalEntry,
    RefusedReason,
    SegmentAmend,
    SegmentAmended,
    SegmentAmendmentWithAnalysis,
    SegmentAnalysis,
    SegmentConfirm,
    SegmentConfirmation,
    SegmentStatus,
    SetLanguages,
    SummaryRef,
    SummarySpeak,
    TamperRecord,
    TamperState,
    TranscriptReview,
    TranscriptReviewResolve,
    TranscriptReviewStart,
    TranscriptReviewState,
    TrustUpdate,
    TurnRef,
    TurnStarted,
    TurnStatus,
    TurnSubmit,
    VoicePlayback,
    to_caption,
    wire_explain_back,
    wire_note,
    wire_summary,
    wire_summary_check,
)
from graph.turn_graph import TurnPipeline
from introduction import (
    ask_if_clear_line,
    ask_line,
    ask_to_repeat_line,
    introduction_line,
    notice_sha256,
    read_name,
    signal_line,
    welcome_line,
)
from kb.embeddings import Embedder, embedder_name, make_embedder
from kb.store import KnowledgeBase
from llm import ClaudeModel, Model
from speech_token import SpeechNotConfigured, issue_token
from trust import SpokenTurn, TrustAdvisor, nudge_cue, reassurance_landed, understanding_cue
from visit_store import Connection, Hub, SegmentRecord, Speech, TurnRecord, Visit, new_entry_id, now
from voice import (
    DEFAULT_MODEL,
    DEFAULT_VOICE,
    ElevenLabsVoice,
    Voice,
    VoiceUnavailable,
)

# uvicorn prints this logger, so timing lines and errors show in the dev.sh output.
log = logging.getLogger("uvicorn.error")
ROLES = ("controller", "screen", "review")
# CDR-005 consent rule 1: the error every speech-capturing command gets before consent.
CONSENT_NEEDED = "Consent is needed before the conversation starts"
# CDR-004: a speech whose end never arrives stops showing as speaking after this long.
VOICE_CEILING_S = 60.0
# CDR-008: the same device may not send two patient signals within this many seconds.
SIGNAL_HOLD_S = 2.0


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


def services(settings: Settings, voice: Voice | None, embedder: Embedder) -> dict[str, str]:
    """What this run uses: the API, its models, speech recognition, the voice, and the embedder.

    The one source for both the start-up line (describe) and GET /api/health, so the two cannot drift.
    Every value is a string; a service that is absent is "none" or "".

    @implements ADR-006: LLM: Claude Sonnet 5.5 for live turns, Opus 5.5 for note and summary
    @implements ADR-010: Voice output: ElevenLabs Eleven v4 replaces OpenAI text-to-speech; Azure stays fallback
    """
    claude = settings.translator == "claude"
    recognition = "azure" if settings.azure_speech_key and settings.azure_speech_region else "none"
    # ADR-010: the server voice when there is one; otherwise the browser speaks with Azure, if it has a key.
    if voice:
        spoken = "elevenlabs"
        voice_model = getattr(voice, "model", None) or settings.elevenlabs_model or DEFAULT_MODEL
        voice_id = getattr(voice, "voice_id", None) or settings.elevenlabs_voice_id or DEFAULT_VOICE
    else:
        spoken = "azure" if recognition == "azure" else "none"
        voice_model = voice_id = ""
    return {
        "translator": settings.translator,
        "liveModel": LIVE_MODEL if claude else "",
        "toneModel": TONE_MODEL if claude else "",
        "recordModel": RECORD_MODEL if claude else "",
        "recognition": recognition,
        "voice": spoken,
        "voiceModel": voice_model,
        "voiceId": voice_id,
        "embeddings": embedder_name(embedder),
    }


def describe(used: dict[str, str], test_languages: bool) -> str:
    """One start-up line saying what this run will use, so a fake run is never mistaken for live."""
    translator = (
        f"Claude ({used['liveModel']}, trust cues {used['toneModel']}, note and summary {used['recordModel']})"
        if used["translator"] == "claude"
        else "fake model (no AI calls)"
    )
    speech = "Azure" if used["recognition"] == "azure" else "not configured"
    if used["voice"] == "elevenlabs":
        speech += f", voice ElevenLabs ({used['voiceModel']}, {used['voiceId']}) with Azure fallback"
    elif used["voice"] == "none":
        speech += ", no voice"
    embeddings = "E5" if used["embeddings"] == "e5" else "hashing (test only)"
    mode = " TEST MODE: Sinhala selectable (TDM-003), never use on stage." if test_languages else ""
    return f"Translator: {translator}. Speech: {speech}. Embeddings: {embeddings}.{mode}"


def create_app(
    model: Model | None = None,
    settings: Settings | None = None,
    kb: KnowledgeBase | None = None,
    voice: Voice | None = None,
    voice_ceiling_s: float = VOICE_CEILING_S,
    signal_hold_s: float = SIGNAL_HOLD_S,
    *,
    model_tone_check: bool = False,
) -> FastAPI:
    settings = settings or load_settings()
    model = model or make_model(settings)
    voice = voice or make_voice(settings)
    kb = kb or KnowledgeBase(make_embedder())
    used = services(settings, voice, kb.embedder)
    log.info(describe(used, settings.test_languages))
    pipeline = TurnPipeline(model, kb, model_tone_check=model_tone_check)
    advisor = TrustAdvisor(model, kb)

    app = FastAPI(title="Demo night server")
    # Screens load from the Next.js origin on the demo laptop or the local network.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    hub = Hub(Visit())
    app.state.hub = hub
    background: set[asyncio.Task] = set()
    app.state.background = background
    # CDR-004: the running voice-ceiling timers, so a new visit (CDR-001 `visit.new`) can cancel them.
    ceilings: set[asyncio.Task] = set()
    app.state.ceilings = ceilings

    def live(visit: Visit, epoch: int | None = None) -> bool:
        """Whether work begun in `visit` may still publish: the visit has not been replaced by `visit.new` (CDR-001)
        and, when `epoch` is given, consent has not been withdrawn since (CDR-005 consent rule 3).

        Every slow run (a turn in the graph, the trust advisor, a correction, an explain-back check, the note, and
        the summary) captures its visit when it starts and checks here before it publishes anything.
        """
        return hub.visit is visit and (epoch is None or visit.consent_epoch == epoch)

    @app.get("/api/health")
    async def health() -> dict:
        return {
            "ok": True,
            "visitId": hub.visit.visit_id,
            "translator": settings.translator,
            # TDM-003: the controller shows its banner and the test languages from this; screens never ask.
            "testLanguages": settings.test_languages,
            "voice": "elevenlabs" if voice else "azure",
            # ADR-006, ADR-010: the controller's services line; the same dict the start-up line is made from.
            "services": used,
        }

    @app.get("/api/speech-token")
    async def speech_token() -> dict:
        try:
            return await issue_token(settings.azure_speech_key, settings.azure_speech_region)
        except SpeechNotConfigured as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    def speakable(speech_id: str, language: Language | None) -> tuple[str, Language] | None:
        """What an id may say aloud: a settled final turn, a confirmed read-back, an interpreter line, or the
        visit's current consent notice in the patient's language (CDR-005), whether or not consent is given.
        Each is said in the voice's one constant delivery (IDR-006), so only the text and language are returned.

        Blocked, unclear, escalated, rejected, and unsettled turns, other notices, and unknown ids are never spoken.
        An `ask_to_repeat` line (ADR-003) has one text, in the unclear turn's speaker's language, so it is served in
        that language only.
        """
        visit = hub.visit
        notice = visit.consent_notice()
        if notice and speech_id == notice.speech_id:
            if language != notice.language:
                return None
            return notice.lines[0].text, notice.language
        # CDR-007: `{summaryId}.{n}`, a sentence of the current passed summary only, in its language only. A
        # refused or replaced summary is never held, so never served.
        summary = visit.summary
        if summary and speech_id.startswith(f"{summary.summary_id}."):
            sentence = next((s for s in summary.sentences if s.sentence_id == speech_id), None)
            if sentence is None or language != summary.language:
                return None
            return sentence.text, summary.language
        record = visit.turns.get(speech_id)
        if record and record.result:
            result = record.result
            if (record.settled and result.status == "final") or record.readback_confirmed:
                # IDR-006: the settled translation, frame phrase and all, in the constant delivery; manner, emotion,
                # and certainty no longer change how it is said.
                return result.translation, result.target_language
            return None
        line = visit.interpreter_lines.get(speech_id)
        if line:
            # CDR-008: the closing check is asked of the patient in their language only; the physician's copy is
            # shown, never spoken.
            parts = line.lines[:1] if line.purpose == "ask_if_clear" else line.lines
            for part in parts:
                if part.language == language:
                    return part.text, part.language
        return None

    @app.get("/api/speech/{speech_id}")
    async def speech(speech_id: str, language: Language | None = None) -> StreamingResponse:
        """404: never speak this. 503: speak it, but with the browser's Azure voice."""
        found = speakable(speech_id, language)
        if found is None:
            raise HTTPException(status_code=404, detail="Nothing to speak for that id")
        text, target = found
        if voice is None or not voice.supports(target):
            raise HTTPException(status_code=503, detail=f"No server voice for {target}")
        try:
            audio = await voice.stream(text, target)
        except VoiceUnavailable as exc:
            log.warning("server voice failed for %s, browser falls back to Azure: %s", speech_id, exc)
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return StreamingResponse(audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})

    async def error(conn: Connection, message: str, command: str, reason: RefusedReason = "invalid") -> None:
        """Refuse a command: the controller gets CDR-001 `error`, a review connection the content-free
        `command.refused` (CDR-005), and a screen nothing."""
        if conn.role == "controller":
            await hub.send_to(conn, "error", ErrorPayload(message=message, command=command).wire())
        elif conn.role == "review":
            await hub.send_to(conn, "command.refused", CommandRefused(command=command, reason=reason).wire())

    async def status(turn_id: str, stage: str) -> None:
        record = hub.visit.turns.get(turn_id)
        if record is None:
            return  # a turn of a visit that `visit.new` replaced: the new visit never hears of it (CDR-001)
        record.stage = stage
        await hub.publish("turn.status", TurnStatus(turn_id=turn_id, stage=stage).wire())

    async def publish_integrity() -> None:
        """CDR-006: every role hears the chain's state after every append; CDR-007: then any artefact gone stale."""
        await hub.publish("record.integrity", hub.visit.integrity().wire())
        await refresh_stale()

    async def refresh_stale() -> None:
        """CDR-007 stale rule: mark the note or summary stale once the chain grows past it, and say so once.

        Screens and review never hear about the note, so they get the event only when the summary turns stale.
        """
        visit = hub.visit
        note, summary = visit.stale_flags()
        note_turned, summary_turned = note and not visit.note_stale, summary and not visit.summary_stale
        if not (note_turned or summary_turned):
            return
        visit.note_stale, visit.summary_stale = note, summary
        stale = ArtefactsStale(note=note, summary=summary, head_hash=visit.chain.head_hash)
        public = stale.model_copy(update={"note": False}).wire() if summary_turned else None
        await hub.publish_shaped("artefacts.stale", stale.wire(), public)

    def spawn(coro) -> None:
        """Run slow work (the turn graph, a model chain) off the receive loop, so the socket stays responsive."""
        task = asyncio.create_task(coro)
        background.add(task)
        task.add_done_callback(background.discard)

    async def refuse_without_consent(conn: Connection, command: str) -> bool:
        """CDR-005 consent rule 1: nothing that captures speech runs until consent is given."""
        if hub.visit.consent is None:
            await error(conn, CONSENT_NEEDED, command, "consent_required")
            return True
        return False

    async def set_languages(conn: Connection, payload: dict) -> None:
        cmd = SetLanguages.model_validate(payload)
        visit = hub.visit
        if visit.consent is not None:
            # CDR-005 consent rule 2: consent was given to a notice in one language.
            message = "Languages are fixed while consent is given. Withdraw consent to change them."
            await error(conn, message, "visit.set_languages", "consent_already_given")
            return
        if visit.turns:
            await error(conn, "Languages cannot change once the visit has a turn", "visit.set_languages")
            return
        if cmd.patient_language in TEST_LANGUAGES and not settings.test_languages:
            await error(conn, "This language is coming soon", "visit.set_languages")
            return
        visit.patient_language = cmd.patient_language
        visit.physician_language = cmd.physician_language
        await hub.publish_state()
        # CDR-005: a notice is read aloud on its own once, when it is first set and consent is not given.
        notice = visit.consent_notice()
        if notice and notice.notice_id not in visit.consent_spoken:
            visit.consent_spoken.add(notice.notice_id)
            await hub.publish(
                "consent.speak", ConsentSpeak(speech_id=notice.speech_id, language=notice.language).wire()
            )

    # ---------- CDR-005: consent ----------

    async def change_consent(state: str, by: ConsentBy, notice: ConsentNotice, reason: str | None = None) -> None:
        """Record a consent change as a new chain entry, then tell every role (CDR-005, CDR-006)."""
        visit = hub.visit
        at, entry_id = now(), new_entry_id()
        body = ConsentEntryBody(
            state=state,  # type: ignore[arg-type]
            at=at,
            by=by,
            notice_id=notice.notice_id,
            notice_version=notice.version,
            language=notice.language,
            notice_sha256=notice_sha256(notice),
            reason=reason,
        )
        visit.append("consent", entry_id, body.wire(), at)
        visit.consent_state = ConsentState(
            state=state,  # type: ignore[arg-type]
            at=at,
            by=by,
            notice_id=notice.notice_id,
            notice_version=notice.version,
            language=notice.language,
            entry_id=entry_id,
        )
        visit.consent = at if state == "given" else None
        await hub.publish("consent.changed", visit.consent_state.wire())
        await publish_integrity()

    def consent_by(conn: Connection) -> ConsentBy:
        # The patient's own tap comes from the review screen; the controller acts on the patient's behalf.
        return "patient" if conn.role == "review" else "physician_on_behalf"

    async def give_consent(conn: Connection, payload: dict) -> None:
        cmd = ConsentGive.model_validate(payload)
        visit = hub.visit
        command = "consent.give"
        notice = visit.consent_notice()
        if visit.consent is not None:
            await error(conn, "Consent is already given", command, "consent_already_given")
        elif cmd.language != visit.patient_language:
            await error(conn, "Consent must be given in the patient's language", command, "wrong_language")
        elif notice is None or cmd.notice_version != notice.version:
            await error(conn, "That is not the current consent notice", command, "wrong_notice")
        else:
            await change_consent("given", consent_by(conn), notice)

    async def withdraw_consent(conn: Connection, payload: dict) -> None:
        cmd = ConsentWithdraw.model_validate(payload)
        visit = hub.visit
        notice = visit.consent_notice()
        if visit.consent is None or notice is None:
            await error(conn, "Consent is not given", "consent.withdraw", "consent_not_given")
            return
        # CDR-005 consent rule 3: capture stops at once. A turn still in the graph sees the new epoch and is
        # discarded when it finishes; settled turns stay in the record, since withdrawal is not erasure.
        visit.consent_epoch += 1
        reason = " ".join((cmd.reason or "").split()) or None
        await change_consent("withdrawn", consent_by(conn), notice, reason)
        await clear_transcript_review(visit)
        if visit.pending_readback:
            # Discarded unspoken, exactly as turn.readback_reject.
            turn_id, visit.pending_readback = visit.pending_readback, None
            await status(turn_id, "discarded")
        if visit.explain_back_open():
            # An open explain-back is cancelled. One already checking is cancelled too (the record is silent on
            # it; this is the narrower choice), and its result is discarded unchained when the check returns.
            await set_explain_back("cancelled")

    async def read_consent_aloud(conn: Connection, payload: dict) -> None:
        notice = hub.visit.consent_notice()
        if notice is None:
            await error(conn, "No consent notice for this language", "consent.read_aloud", "not_found")
            return
        await hub.publish("consent.speak", ConsentSpeak(speech_id=notice.speech_id, language=notice.language).wire())

    async def refuse_while_paused(conn: Connection, command: str, reason: RefusedReason = "invalid") -> bool:
        """Off the record: nothing said is captured or relayed until the visit resumes (demo spec, CDR-001)."""
        if hub.visit.paused:
            await error(conn, "Paused: nothing is recorded until you resume", command, reason)
            return True
        return False

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
        # CDR-005: the interpreter introduces itself only after consent, since the introduction captures names.
        if await refuse_without_consent(conn, "visit.start_introduction"):
            return
        if await refuse_while_paused(conn, "visit.start_introduction"):
            return
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
        if await refuse_without_consent(conn, "visit.name_reply"):
            return
        if await refuse_while_paused(conn, "visit.name_reply"):
            return
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

    async def send_trust(visit: Visit, turn_id: str, epoch: int) -> None:
        """MDD-005 and CDR-008: one trust.update per spoken turn, to controllers only, after the trust advisor
        returns, or at once without a cue if it fails. Never on the turn's critical path.

        A patient turn gets the empathy nudge as before (emotion in the nudge set) and the reassurance mark, which
        code decides from the visit's spoken history; a physician turn gets a culture cue when the patient
        language's tone guide marks the topic sensitive; a companion turn gets neither.

        `epoch` is the consent epoch the turn was spoken under (CDR-005 consent rule 3): once consent is withdrawn
        no model call starts, and an advisor call that was running is dropped with its nudge and its update.
        The update is placed in `visit.trust` by its turn's spoken position, however late it returns. `visit` is the
        visit the turn was spoken in; once `visit.new` replaces it, the update is dropped the same way (CDR-001).
        """
        record = visit.turns.get(turn_id)
        if record is None or record.result is None or not live(visit, epoch):
            return
        result = record.result
        history = [SpokenTurn(r.speaker, r.emotion, r.manner) for r in visit.spoken_results_before(turn_id)]
        landed = reassurance_landed(history, result.speaker, result.emotion)
        cue = None
        nudge = None
        try:
            if result.speaker == "physician":
                cue = await advisor.culture_cue(result.source_text, visit.patient_language)
            elif result.speaker == "patient":
                nudge = await advisor.nudge(turn_id, result.emotion, result.translation)
        except Exception:
            log.exception("trust advisor failed")
        if not live(visit, epoch):
            # Consent was withdrawn, or a new visit started, while the advisor was running: nothing of this turn's
            # trust reaches anyone.
            return
        if nudge:
            visit.nudges.append(nudge)
            await hub.publish("empathy.nudge", nudge.wire())
            cue = nudge_cue(nudge)
        update = TrustUpdate(
            turn_id=turn_id,
            speaker=result.speaker,
            emotion=None if result.speaker == "physician" else result.emotion,
            manner=result.manner,
            reassurance_landed=landed,
            signal=None,
            cue=cue,
            at=now(),
        )
        visit.add_trust(update)
        await hub.publish("trust.update", update.wire())

    # @implements CDR-009: Patient confirmation of a captured transcript before translation
    async def publish_transcript_review(visit: Visit) -> None:
        await hub.publish("transcript.review_state", TranscriptReviewState(review=visit.transcript_review).wire())

    async def clear_transcript_review(visit: Visit) -> None:
        if visit.transcript_review is not None:
            visit.transcript_review = None
            await publish_transcript_review(visit)

    async def start_transcript_review(conn: Connection, payload: dict) -> None:
        command = "transcript.review_start"
        cmd = TranscriptReviewStart.model_validate(payload)
        visit = hub.visit
        if await refuse_without_consent(conn, command) or await refuse_while_paused(conn, command):
            return
        text = cmd.text.strip()
        if not text:
            await error(conn, "The transcript is empty", command)
            return
        if visit.transcript_review is not None:
            await error(conn, "A transcript is already waiting for review", command, "busy")
            return
        visit.transcript_review = TranscriptReview(
            review_id=uuid.uuid4().hex, text=text, language=visit.patient_language
        )
        await publish_transcript_review(visit)

    async def resolve_transcript_review(conn: Connection, payload: dict) -> None:
        command = "transcript.review_resolve"
        cmd = TranscriptReviewResolve.model_validate(payload)
        visit = hub.visit
        if await refuse_without_consent(conn, command) or await refuse_while_paused(conn, command):
            return
        review = visit.transcript_review
        if review is None or review.review_id != cmd.review_id:
            await error(conn, "That transcript is no longer waiting for review", command, "not_found")
            return
        if cmd.text is not None and (conn.role != "controller" or cmd.action != "confirm"):
            await error(conn, "Only the physician can confirm edited text", command, "not_allowed")
            return
        text = review.text if cmd.text is None else cmd.text.strip()
        if cmd.action == "confirm" and (not text or visit.pending_readback):
            await error(conn, "A nonempty transcript and a settled dose check are required", command, "busy")
            return
        epoch = visit.consent_epoch
        await clear_transcript_review(visit)
        if cmd.action == "repeat":
            return

        async def submit_reviewed() -> None:
            if live(visit, epoch) and not visit.paused:
                await submit_turn(
                    conn,
                    TurnSubmit(speaker="patient", language=review.language, text=text, recognition_confidence=1).wire(),
                )

        spawn(submit_reviewed())

    async def submit_turn(conn: Connection, payload: dict) -> None:
        cmd = TurnSubmit.model_validate(payload)
        visit = hub.visit
        if await refuse_without_consent(conn, "turn.submit"):
            return
        if await refuse_while_paused(conn, "turn.submit"):
            return
        if visit.pending_readback:
            await error(conn, "Confirm or reject the highlighted dose before the next turn", "turn.submit")
            return
        patient, physician = visit.patient_language, visit.physician_language
        if cmd.language not in (patient, physician):
            await error(conn, f"{cmd.language} is not a language of this visit", "turn.submit")
            return
        if cmd.speaker == "companion" and cmd.language != patient:
            # CDR-008: a companion is a third speaker in the patient's language, labelled companion everywhere.
            await error(conn, "A companion speaks the patient's language", "turn.submit")
            return
        target = physician if cmd.language == patient else patient
        if visit.introduction in ("pending", "asking_physician", "asking_patient"):
            # Speaking is how the physician skips the introduction, before or part way through it.
            visit.introduction = "skipped"
            visit.proposed_names.clear()
            await hub.publish_state()

        turn_id = uuid.uuid4().hex[:10]
        epoch = visit.consent_epoch
        # CDR-005 explain-back rule 2: only a patient turn begun and settled final while the same explain-back is
        # listening joins the explanation. A turn begun before it opened does not (narrowest reading).
        eb = visit.explain_back
        listening_to = eb.explain_back_id if eb is not None and eb.state == "listening" else None
        record = TurnRecord(result=None, speaker=cmd.speaker, source_text=cmd.text, stage="listening")
        visit.turns[turn_id] = record
        visit.current_turn_id = turn_id
        await hub.publish(
            "turn.started", TurnStarted(turn_id=turn_id, speaker=cmd.speaker, language=cmd.language).wire()
        )

        async def claim_injection() -> bool:
            # TDM-002: one shot; spent on the first physician turn with a dose number, then disarmed.
            if not visit.injection_armed or not live(visit):
                return False
            visit.injection_armed = False
            visit.injected_turns.append(turn_id)
            await hub.publish("demo.injection_state", DemoInjectionState(state="fired").wire())
            return True

        started = time.perf_counter()
        try:
            result, reason = await pipeline.run(
                turn_id=turn_id,
                speaker=cmd.speaker,
                source=cmd.language,
                target=target,
                text=cmd.text,
                recognition_confidence=cmd.recognition_confidence,
                # ADR-003: the speaker's streak before this turn decides between unclear and escalated.
                unclear_streak=visit.unclear_streak[cmd.speaker],
                physician_name=visit.physician_name,
                patient_name=visit.patient_name,
                emit=lambda stage: status(turn_id, stage),
                claim_injection=claim_injection if cmd.speaker == "physician" else None,
                # IDR-006: a patient or companion turn in the physician's language is relayed to the patient, so it
                # carries no affect phrase; the phrase is only ever for the physician.
                listener="physician" if target == physician else "patient",
            )
        except Exception as exc:  # refusal or API failure: nothing is spoken
            log.exception("turn pipeline failed")
            if live(visit):
                await status(turn_id, "failed")
                await error(conn, f"Translation failed: {exc}", "turn.submit")
            return
        log.info(
            "turn %s %s, attempts %d, in %.2fs", turn_id, result.status, result.attempts, time.perf_counter() - started
        )

        if not live(visit):
            # CDR-001 `visit.new`: the visit this turn began in was replaced while it was in the graph. It belongs
            # to no visit now, so nothing of it is published, spoken, or chained, not even its discard.
            return
        if visit.consent_epoch != epoch:
            # CDR-005 consent rule 3: consent was withdrawn while this turn was in the graph. Never spoken,
            # never published, never chained; the controller sees it discarded.
            if visit.current_turn_id == turn_id:
                visit.current_turn_id = None
            await status(turn_id, "discarded")
            return

        record.result = result
        # ADR-003: unclear adds one, final and the third unclear's escalation reset, blocked and a tone escalation
        # leave it; a read-back resets it only when confirmed (readback below).
        visit.unclear_streak[result.speaker] = result.unclear_streak
        await hub.publish("turn.analysis", result.wire())

        if result.status == "readback_required":
            visit.pending_readback = turn_id
            await hub.publish("turn.readback_required", TurnRef(turn_id=turn_id).wire())
            await status(turn_id, "awaiting_readback")
            return

        # final, blocked, unclear, or escalated: the turn is settled and shared screens may show it. Blocked,
        # unclear, and escalated turns are never spoken and their captions carry no translation (CDR-002).
        record.settled = True
        record.stage = {"final": "spoken"}.get(result.status, result.status)
        visit.append_turn(turn_id)
        await hub.publish("turn.result", to_caption(result).wire())
        await publish_integrity()
        if result.status == "escalated" and reason:
            await escalate(reason, turn_id)  # type: ignore[arg-type]
        if result.status == "unclear":
            # ADR-003: the interpreter asks the speaker, aloud and in their language only, to say it again.
            speaker_name = {"physician": visit.physician_name, "patient": visit.patient_name}.get(result.speaker)
            await say(ask_to_repeat_line(cmd.language, speaker_name))
        eb = visit.explain_back
        if (
            result.status == "final"
            and result.speaker == "patient"
            and eb is not None
            and eb.state == "listening"
            and eb.explain_back_id == listening_to
        ):
            await set_explain_back("listening", [*eb.explanation_turn_ids, turn_id])
        if result.status == "final":
            spawn(send_trust(visit, turn_id, epoch))

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
        # ADR-003: a read-back-confirmed turn is spoken, so it resets its speaker's unclear streak.
        assert record.result is not None
        record.result = record.result.model_copy(update={"unclear_streak": 0})
        visit.unclear_streak[record.result.speaker] = 0
        visit.append_turn(ref.turn_id)
        await hub.publish("turn.result", to_caption(record.result, readback_confirmed=True).wire())  # type: ignore[arg-type]
        await publish_integrity()
        # A confirmed read-back is a spoken turn, so it gets its trust update like every other (CDR-008).
        spawn(send_trust(visit, ref.turn_id, visit.consent_epoch))

    # ---------- ADR-003 and CDR-001: off-the-record pause, interpreter, and high-risk marks ----------

    def record_escalation(entry: EscalationEntry) -> None:
        """Keep an interpreter event for the controller and chain it (ADR-003, CDR-006)."""
        visit = hub.visit
        visit.escalations.append(entry)
        visit.append("interpreter", entry.entry_id, entry.model_dump(by_alias=True, exclude={"entry_id"}), entry.at)

    async def escalate(reason: EscalationReason, turn_id: str | None = None, note: str | None = None) -> None:
        """Record an interpreter offer, request, or high-risk mark in the visit, and tell every screen.

        A high-risk mark is one `mark` entry; the offer it causes is not a second entry (CDR-006).
        """
        action = {"requested": "request", "high_risk": "mark"}.get(reason, "offer")
        entry = EscalationEntry(
            entry_id=new_entry_id(),
            action=action,  # type: ignore[arg-type]
            reason=reason,
            at=now(),
            turn_id=turn_id,
            note=note,
        )
        record_escalation(entry)
        hub.visit.interpreter_open = True
        await hub.publish("interpreter.escalation", InterpreterEscalation(reason=reason, turn_id=turn_id).wire())
        await publish_integrity()

    async def dismiss_interpreter(conn: Connection, payload: dict) -> None:
        # CDR-006: controller only, allowed while paused; clears the offer on every screen, the TV included.
        cmd = InterpreterDismiss.model_validate(payload)
        visit = hub.visit
        if not visit.interpreter_open:
            await error(conn, "No interpreter offer or request is open", "interpreter.dismiss", "not_found")
            return
        entry = EscalationEntry(entry_id=new_entry_id(), action="dismiss", reason=cmd.reason, at=now())
        record_escalation(entry)
        visit.interpreter_open = False
        dismissed = InterpreterDismissed(reason=cmd.reason, at=entry.at, entry_id=entry.entry_id)
        await hub.publish("interpreter.dismissed", dismissed.wire())
        await publish_integrity()

    async def set_paused(conn: Connection, paused: bool) -> None:
        command = "visit.pause" if paused else "visit.resume"
        if hub.visit.paused == paused:
            await error(conn, "The visit is already paused" if paused else "The visit is not paused", command)
            return
        hub.visit.paused = paused
        if paused:
            await clear_transcript_review(hub.visit)
        await hub.publish("visit.paused" if paused else "visit.resumed", {})

    async def request_interpreter(conn: Connection, payload: dict) -> None:
        # Either party, from any screen, at any time, paused or not (ADR-003).
        await escalate("requested")

    async def mark_high_risk(conn: Connection, payload: dict) -> None:
        cmd = MarkHighRisk.model_validate(payload)
        if cmd.turn_id is not None and cmd.turn_id not in hub.visit.turns:
            await error(conn, "No turn with that id in this visit", "visit.mark_high_risk")
            return
        note = " ".join((cmd.note or "").split()) or None
        await escalate("high_risk", cmd.turn_id, note)

    # ---------- TDM-002: presenter mismatch control ----------

    async def inject_mismatch(conn: Connection, payload: dict) -> None:
        # Arming again while armed changes nothing: it still fires once.
        hub.visit.injection_armed = True
        await hub.publish("demo.injection_state", DemoInjectionState(state="armed").wire())

    async def cancel_injection(conn: Connection, payload: dict) -> None:
        if not hub.visit.injection_armed:
            await error(conn, "No mismatch injection is armed", "demo.cancel_injection")
            return
        hub.visit.injection_armed = False
        await hub.publish("demo.injection_state", DemoInjectionState(state="cancelled").wire())

    # ---------- TDM-005: hidden record-tamper control ----------

    async def tamper_record(conn: Connection, payload: dict) -> None:
        # @implements TDM-005: Hidden record-tamper control for the demo
        # Controller only (dropped from other roles in the receive loop), once per visit, turn or amendment
        # entries only. Removed after demo night with demo.tamper_state and visit.state.tamper (TDM-005).
        cmd = TamperRecord.model_validate(payload)
        visit = hub.visit
        command = "demo.tamper_record"
        if visit.tamper is not None:
            await error(conn, "The tamper control has already been used in this visit", command, "not_allowed")
            return
        if cmd.entry_id not in visit.entry_ids:
            await error(conn, "No record entry with that id", command, "not_found")
            return
        if not visit.tamper_entry(cmd.entry_id):
            await error(conn, "Only a turn or a correction can be altered", command, "not_allowed")
            return
        visit.tamper = TamperState(entry_id=cmd.entry_id, at=now())
        await hub.publish("demo.tamper_state", visit.tamper.wire())
        # The normal IDR-003 verification names the altered entry in brokenAt; screens learn of it only this way.
        await publish_integrity()

    # ---------- CDR-006: review corrections and confirmations ----------

    async def own_final_turn(conn: Connection, segment_id: str, command: str) -> bool:
        """Refuse unless the segment is a settled final patient turn (the patient corrects only their own turns)."""
        record = hub.visit.turns.get(segment_id)
        if record is None or not record.settled or record.result is None:
            await error(conn, "No settled turn with that id", command, "not_found")
            return False
        if record.result.speaker != "patient" or record.result.status != "final":
            await error(
                conn, "Only the patient's own spoken turns can be confirmed or corrected", command, "not_allowed"
            )
            return False
        return True

    async def confirm_segment(conn: Connection, payload: dict) -> None:
        cmd = SegmentConfirm.model_validate(payload)
        visit = hub.visit
        command = "segment.confirm"
        if not await own_final_turn(conn, cmd.segment_id, command):
            return
        segment = visit.segments.get(cmd.segment_id) or SegmentRecord()
        if cmd.version != segment.current:
            await error(conn, "That version is no longer current", command, "not_current")
            return
        if segment.confirmed is not None and segment.confirmed.version == segment.current:
            await error(conn, "That version is already confirmed", command, "not_allowed")
            return
        at, entry_id = now(), new_entry_id()
        visit.append(
            "confirmation", entry_id, ConfirmationEntryBody(segment_id=cmd.segment_id, version=cmd.version).wire(), at
        )
        segment.confirmed = SegmentConfirmation(version=cmd.version, at=at, entry_id=entry_id)
        visit.segments[cmd.segment_id] = segment
        amended = SegmentAmended(
            segment_id=cmd.segment_id, by="patient", action="confirm", version=cmd.version, entry_id=entry_id
        )
        await hub.publish("segment.amended", amended.wire())
        await publish_integrity()

    async def amend_segment(conn: Connection, payload: dict) -> None:
        cmd = SegmentAmend.model_validate(payload)
        visit = hub.visit
        command = "segment.amend"
        # Re-speaking captures speech, so it waits for consent (CDR-005) and stops while paused (CDR-006).
        if await refuse_without_consent(conn, command):
            return
        if await refuse_while_paused(conn, command, "not_allowed"):
            return
        if not await own_final_turn(conn, cmd.segment_id, command):
            return
        if cmd.language != visit.patient_language:
            await error(conn, "A correction is spoken in the patient's language", command, "wrong_language")
            return
        if not cmd.text.strip():
            await error(conn, "Nothing was heard", command, "invalid")
            return
        if visit.amend_in_flight is not None:
            await error(conn, "Another correction is still being checked", command, "busy")
            return
        visit.amend_in_flight = cmd.segment_id
        spawn(run_amendment(visit, conn, cmd, new_entry_id()))

    async def run_amendment(visit: Visit, conn: Connection, cmd: SegmentAmend, amendment_id: str) -> None:
        """The correction through the same turn graph as a live turn; applied and chained only if it ends final."""
        segment_id, epoch = cmd.segment_id, visit.consent_epoch

        async def segment_status(stage: str, reason: str | None = None) -> None:
            if not live(visit):
                return  # the visit was replaced by `visit.new` (CDR-001)
            event = SegmentStatus(segment_id=segment_id, amendment_id=amendment_id, stage=stage, reason=reason)  # type: ignore[arg-type]
            await hub.publish("segment.status", event.wire())

        async def emit(stage: str) -> None:
            if stage in ("translating", "verifying", "retrying"):
                await segment_status(stage)

        try:
            try:
                # The TurnResult is named by the amendmentId, so it never collides with the original turn.
                result, _ = await pipeline.run(
                    turn_id=amendment_id,
                    speaker="patient",
                    source=visit.patient_language,
                    target=visit.physician_language,
                    text=cmd.text,
                    recognition_confidence=cmd.recognition_confidence,
                    physician_name=visit.physician_name,
                    patient_name=visit.patient_name,
                    emit=emit,
                )
            except Exception:
                log.exception("correction pipeline failed")
                await segment_status("refused", "failed")
                return
            if not live(visit, epoch):
                # Consent was withdrawn, or a new visit started, while it was checked: discarded like a live turn,
                # never chained or shown (segment_status says nothing into a new visit).
                await segment_status("refused", "failed")
                return
            await hub.publish(
                "segment.analysis",
                SegmentAnalysis(segment_id=segment_id, amendment_id=amendment_id, result=result).wire(),
            )
            if result.status != "final":
                # Blocked, unclear, or escalated: refused, unchained, the current version stays, no translation
                # anywhere public. No interpreter offer either: an offer would be chained, and a refused correction
                # is not. A correction is not a live turn, so it starts no unclear streak and keeps none (ADR-003);
                # CDR-006 has no `unclear` reason, so an unclear correction is refused as `failed`.
                reason = result.status if result.status in ("blocked", "escalated") else "failed"
                await segment_status("refused", reason)
                return
            caption = to_caption(result)
            assert caption.translation is not None and caption.tone_label is not None
            segment = visit.segments.get(segment_id) or SegmentRecord()
            at = now()
            body = AmendmentEntryBody(
                segment_id=segment_id,
                amendment_id=amendment_id,
                replaces=segment.current,
                source_text=cmd.text,
                translation=caption.translation,
                tone_label=caption.tone_label,
                critical_values=caption.critical_values,
            )
            visit.append("amendment", amendment_id, body.wire(), at)
            segment.amendments.append(
                SegmentAmendmentWithAnalysis(
                    amendment_id=amendment_id,
                    source_text=cmd.text,
                    translation=caption.translation,
                    tone_label=caption.tone_label,
                    critical_values=caption.critical_values,
                    at=at,
                    entry_id=amendment_id,
                    analysis=result,
                )
            )
            visit.segments[segment_id] = segment
            amended = SegmentAmended(
                segment_id=segment_id,
                by="patient",
                action="amend",
                new_text=cmd.text,
                amendment_id=amendment_id,
                translation=caption.translation,
                tone_label=caption.tone_label,
                critical_values=caption.critical_values,
                entry_id=amendment_id,
            )
            await hub.publish("segment.amended", amended.wire())
            await segment_status("applied")
            await publish_integrity()
        finally:
            visit.amend_in_flight = None

    # ---------- CDR-005: explain-back ----------

    async def set_explain_back(state: str, turn_ids: list[str] | None = None) -> None:
        visit = hub.visit
        assert visit.explain_back is not None
        update: dict = {"state": state}
        if turn_ids is not None:
            update["explanation_turn_ids"] = turn_ids
        visit.explain_back = visit.explain_back.model_copy(update=update)
        await hub.publish("explainback.state", visit.explain_back.wire())

    async def start_explain_back(conn: Connection, payload: dict) -> None:
        visit = hub.visit
        command = "explainback.start"
        if await refuse_without_consent(conn, command):
            return
        if await refuse_while_paused(conn, command, "not_allowed"):
            return
        if visit.pending_readback:
            await error(conn, "Confirm or reject the highlighted dose first", command, "busy")
            return
        if visit.explain_back_open():
            await error(conn, "An explain-back is already open", command, "busy")
            return
        if not any(visit.spoken(t) and r.speaker == "physician" for t, r in visit.turns.items()):
            await error(conn, "Explain the plan before asking the patient to explain it back", command, "not_allowed")
            return
        # Opening freezes the plan: the physician turns spoken so far, at their effective versions (ADR-011).
        visit.explain_back_plan = visit.freeze()
        visit.explain_back = ExplainBackState(
            explain_back_id=new_entry_id(), state="listening", explanation_turn_ids=[]
        )
        await hub.publish("explainback.state", visit.explain_back.wire())

    async def open_explain_back(conn: Connection, payload: dict, command: str) -> str | None:
        """The id named, if it is the open explain-back and still listening; otherwise refused."""
        ref = ExplainBackRef.model_validate(payload)
        eb = hub.visit.explain_back
        if eb is None or eb.explain_back_id != ref.explain_back_id:
            await error(conn, "No explain-back with that id", command, "not_found")
            return None
        if eb.state != "listening":
            await error(conn, "That explain-back is not listening", command, "not_allowed")
            return None
        return eb.explain_back_id

    async def check_explain_back_cmd(conn: Connection, payload: dict) -> None:
        command = "explainback.check"
        explain_back_id = await open_explain_back(conn, payload, command)
        if explain_back_id is None:
            return
        visit = hub.visit
        assert visit.explain_back is not None
        turn_ids = list(visit.explain_back.explanation_turn_ids)
        if not turn_ids:
            await error(conn, "The patient has not explained anything back yet", command, "not_allowed")
            return
        await set_explain_back("checking")
        spawn(run_explain_back(visit, conn, explain_back_id, turn_ids))

    async def run_explain_back(visit: Visit, conn: Connection, explain_back_id: str, turn_ids: list[str]) -> None:
        plan = visit.explain_back_plan
        assert plan is not None
        # The explanation at its effective versions now, so a correction made while listening is used.
        explanation = visit.freeze().turns_by_id(turn_ids)

        def current() -> bool:
            eb = visit.explain_back
            return live(visit) and eb is not None and eb.explain_back_id == explain_back_id and eb.state == "checking"

        try:
            result = await check_explain_back(
                model, explain_back_id=explain_back_id, plan=plan, explanation=explanation
            )
        except Exception as exc:
            log.exception("explain-back check failed")
            if current():
                # Failed: nothing is chained, and the controller hears why (CDR-005 explain-back rule 3).
                await set_explain_back("failed")
                detail = "; ".join(exc.problems) if isinstance(exc, GenerationFailed) else str(exc)
                await error(conn, f"The explain-back check failed: {detail}", "explainback.check")
            return
        if not current():
            return  # cancelled by a consent withdrawal while checking: discarded, never chained
        wired = wire_explain_back(result)
        body = ExplainBackResultBody(**wired.model_dump(exclude={"entry_id"}))
        visit.append("explain_back", wired.entry_id, body.wire())
        visit.explain_back_results.append(wired)
        await hub.publish("explainback.result", wired.wire())
        await set_explain_back("done")
        await publish_integrity()

    async def cancel_explain_back(conn: Connection, payload: dict) -> None:
        if await open_explain_back(conn, payload, "explainback.cancel") is not None:
            await set_explain_back("cancelled")

    # ---------- CDR-007: clinical note and patient summary ----------

    async def refuse_artefact(conn: Connection, command: str) -> bool:
        """CDR-007 generation rules shared by note.generate and summary.generate."""
        visit = hub.visit
        if not any(visit.spoken(t) for t in visit.turns):
            await error(conn, "Nothing has been spoken yet", command, "not_allowed")
        elif visit.pending_readback:
            await error(conn, "Confirm or reject the highlighted dose first", command, "busy")
        elif visit.amend_in_flight is not None:
            await error(conn, "A correction is still being checked", command, "busy")
        elif visit.explain_back is not None and visit.explain_back.state == "checking":
            await error(conn, "The explain-back is still being checked", command, "busy")
        else:
            return False
        return True

    async def generate_note_cmd(conn: Connection, payload: dict) -> None:
        visit = hub.visit
        if await refuse_artefact(conn, "note.generate"):
            return
        if visit.note_generating:
            await error(conn, "A note is already being written", "note.generate", "busy")
            return
        visit.note_generating = True
        spawn(run_note(visit, new_entry_id(), visit.freeze()))

    async def run_note(visit: Visit, note_id: str, snapshot) -> None:
        async def note_status(stage: str, detail: str | None = None) -> None:
            if not live(visit):
                return  # the visit was replaced by `visit.new` (CDR-001)
            event = ArtefactStatus(artefact_id=note_id, kind="note", stage=stage, detail=detail)  # type: ignore[arg-type]
            await hub.publish("note.status", event.wire())

        try:
            try:
                note = await generate_note(model, snapshot, note_id=note_id, on_stage=note_status)
            except Exception as exc:
                log.exception("note generation failed")
                detail = "; ".join(exc.problems) if isinstance(exc, GenerationFailed) else str(exc)
                await note_status("failed", detail)
                return
            if not live(visit):
                return
            # Regenerating replaces the current note; it is fresh until the chain grows past its head.
            visit.note, visit.note_stale = wire_note(note), False
            await note_status("ready")
            await hub.publish("note.ready", visit.note.wire())
            await refresh_stale()
        finally:
            visit.note_generating = False

    async def generate_summary_cmd(conn: Connection, payload: dict) -> None:
        visit = hub.visit
        if await refuse_artefact(conn, "summary.generate"):
            return
        if visit.summary_generating:
            await error(conn, "A summary is already being written", "summary.generate", "busy")
            return
        visit.summary_generating = True
        spawn(run_summary(visit, new_entry_id(), visit.patient_language, visit.freeze()))

    async def run_summary(visit: Visit, summary_id: str, language: str, snapshot) -> None:
        async def summary_status(stage: str, detail: str | None = None) -> None:
            if not live(visit):
                return  # the visit was replaced by `visit.new` (CDR-001)
            # Every role hears the stage; only controllers hear the detail (CDR-007).
            event = ArtefactStatus(artefact_id=summary_id, kind="summary", stage=stage, detail=detail)  # type: ignore[arg-type]
            await hub.publish_shaped("summary.status", event.wire(), event.model_copy(update={"detail": None}).wire())

        try:
            try:
                outcome = await generate_summary(
                    model, snapshot, summary_id=summary_id, language=language, on_stage=summary_status
                )
            except Exception as exc:
                log.exception("summary generation failed")
                await summary_status("refused", str(exc))
                return
            if not live(visit):
                return
            for check in outcome.checks:
                wired = wire_summary_check(check)
                visit.summary_checks.append(wired)
                await hub.publish("summary.check", wired.wire())
            if outcome.summary is None:
                # Refused: never published, spoken, or chained. A summary that passed earlier stays current (the
                # records are silent; a refused attempt makes no artefact, so it replaces nothing).
                await summary_status("refused", outcome.detail)
                return
            summary = wire_summary(outcome.summary)
            head_before = visit.chain.head_hash
            visit.append("summary", summary.summary_id, summary.wire())
            visit.summary = summary
            # Its own entry never makes it stale, but entries appended while it was written do.
            visit.summary_head = visit.chain.head_hash if head_before == summary.based_on_head else ""
            visit.summary_stale = False
            await summary_status("ready")
            await hub.publish("summary.ready", summary.wire())
            await publish_integrity()
        finally:
            visit.summary_generating = False

    async def read_summary_aloud(conn: Connection, payload: dict) -> None:
        ref = SummaryRef.model_validate(payload)
        summary = hub.visit.summary
        if summary is None or summary.summary_id != ref.summary_id:
            await error(conn, "That is not the current summary", "summary.read_aloud", "not_current")
            return
        speak = SummarySpeak(
            summary_id=summary.summary_id, action="play", speech_ids=[s.sentence_id for s in summary.sentences]
        )
        await hub.publish("summary.speak", speak.wire())

    async def stop_summary(conn: Connection, payload: dict) -> None:
        # Stopping is always safe, so any summary id is accepted (the record sets no rule); it names no sentences.
        ref = SummaryRef.model_validate(payload)
        await hub.publish("summary.speak", SummarySpeak(summary_id=ref.summary_id, action="stop", speech_ids=[]).wire())

    # ---------- CDR-008: the patient's signals and the closing check (MDD-005) ----------

    async def patient_signal(conn: Connection, payload: dict) -> None:
        """A signal from the patient's own device (review role only; the receive loop refuses other roles).

        Refused `invalid` before consent, while paused, and for `repeat` when nothing has yet been spoken in the
        patient's language; `busy` within the hold of the same device's previous signal. Accepted: chained as a
        `signal` entry, shown to every role, relayed to the physician for not_understood and slower, and listed
        for the controller with an understanding cue. `repeat` says nothing new: the controller replays the last
        spoken translation by id.
        """
        cmd = PatientSignalCommand.model_validate(payload)
        visit = hub.visit
        command = "patient.signal"
        if visit.consent is None:
            await error(conn, CONSENT_NEEDED, command, "invalid")
            return
        if visit.paused:
            await error(conn, "Paused: nothing is recorded until you resume", command, "invalid")
            return
        if cmd.signal == "repeat" and not visit.spoken_in(visit.patient_language):
            await error(conn, "Nothing has been spoken in the patient's language yet", command, "invalid")
            return
        held_since = conn.last_signal_at
        if held_since is not None and time.monotonic() - held_since < signal_hold_s:
            await error(conn, "A signal was just sent; wait a moment", command, "busy")
            return
        conn.last_signal_at = time.monotonic()
        at, signal_id = now(), new_entry_id()
        entry = PatientSignalEntry(
            signal_id=signal_id, signal=cmd.signal, after_turn_id=visit.last_settled_turn_id(), at=at
        )
        visit.append("signal", signal_id, entry.wire(), at)
        visit.signals.append(entry)
        await hub.publish("patient.signal", entry.wire())
        await publish_integrity()
        if cmd.signal in ("not_understood", "slower"):
            await say(signal_line(cmd.signal, visit.physician_language, visit.patient_name))
        update = TrustUpdate(
            turn_id=entry.after_turn_id,
            speaker=None,
            emotion=None,
            manner=None,
            reassurance_landed=None,
            signal=cmd.signal,
            cue=understanding_cue(cmd.signal),
            at=at,
        )
        # Sorted just after the turn it followed, so a slow advisor's update for that turn still lands before it.
        visit.add_trust(update)
        await hub.publish("trust.update", update.wire())

    async def ask_if_clear(conn: Connection, payload: dict) -> None:
        """The closing check: the interpreter asks the patient, in their language, whether anything the doctor said
        should be explained again, with the physician's language shown (controller only)."""
        visit = hub.visit
        command = "visit.ask_if_clear"
        if await refuse_without_consent(conn, command):
            return
        if await refuse_while_paused(conn, command):
            return
        if visit.pending_readback:
            await error(conn, "Confirm or reject the highlighted dose first", command, "busy")
            return
        await say(ask_if_clear_line(visit.physician_language, visit.patient_language, visit.patient_name))

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
        ceilings.add(task)
        task.add_done_callback(background.discard)
        task.add_done_callback(ceilings.discard)

    # ---------- CDR-001: a new visit ----------

    async def new_visit(conn: Connection, payload: dict) -> None:
        """Replace the in-memory visit with a fresh one and send every role its new visit.state (CDR-001, ADR-007).

        Controller only. Allowed at any time, including during a read-back or an open explain-back, which go with
        the old visit. The old visit is dropped, not kept: nothing of it is chained into the new one. Work still
        running for it (a turn in the graph, the trust advisor, a correction, a check, the note, or the summary)
        finds `live` false and publishes nothing; the voice ceiling timers are cancelled, and the new visit
        starts silent. Each device's signal hold restarts, as if it had just connected.
        """
        for task in list(ceilings):
            task.cancel()
        hub.visit = Visit()
        for other in hub.connections:
            other.last_signal_at = None
        log.info("new visit %s", hub.visit.visit_id)
        await hub.publish_state()

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
        "transcript.review_start": start_transcript_review,
        "transcript.review_resolve": resolve_transcript_review,
        "turn.readback_confirm": lambda conn, payload: readback(conn, payload, True),
        "turn.readback_reject": lambda conn, payload: readback(conn, payload, False),
        "voice.started": voice_started,
        "voice.ended": voice_ended,
        "visit.pause": lambda conn, payload: set_paused(conn, True),
        "visit.resume": lambda conn, payload: set_paused(conn, False),
        "interpreter.request": request_interpreter,
        "visit.mark_high_risk": mark_high_risk,
        "demo.inject_mismatch": inject_mismatch,
        "demo.cancel_injection": cancel_injection,
        "interpreter.dismiss": dismiss_interpreter,
        "consent.give": give_consent,
        "consent.withdraw": withdraw_consent,
        "consent.read_aloud": read_consent_aloud,
        "demo.tamper_record": tamper_record,
        "segment.confirm": confirm_segment,
        "segment.amend": amend_segment,
        "explainback.start": start_explain_back,
        "explainback.check": check_explain_back_cmd,
        "explainback.cancel": cancel_explain_back,
        "note.generate": generate_note_cmd,
        "summary.generate": generate_summary_cmd,
        "summary.read_aloud": read_summary_aloud,
        "summary.stop": stop_summary,
        "patient.signal": patient_signal,
        "visit.ask_if_clear": ask_if_clear,
        "visit.new": new_visit,
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
        if hub.visit.injection_armed:
            # TDM-002: a controller that reloads still sees the control armed; send_to keeps it from screens.
            await hub.send_to(conn, "demo.injection_state", DemoInjectionState(state="armed").wire())
        # Turns from one connection run one at a time, in the order sent, but off the receive loop, so a
        # withdrawal, pause, or interpreter request sent while a turn is in the graph acts at once (CDR-005
        # consent rule 3) instead of waiting for that turn to be spoken.
        turn_lock = asyncio.Lock()

        async def dispatch(command: str, payload: dict) -> None:
            handler = handlers[command]
            try:
                await handler(conn, payload)
            except ValidationError as exc:
                await error(conn, f"Invalid payload: {exc.errors()[0]['msg']}", command)

        async def dispatch_turn(payload: dict) -> None:
            async with turn_lock:
                await dispatch("turn.submit", payload)

        try:
            while True:
                message = await ws.receive_json()
                command = message.get("type", "")
                if command == "visit.new" and conn.role == "review":
                    # CDR-001: the patient's device may not end the visit; it is told so, without content.
                    await error(conn, "Only the physician can start a new visit", command, "not_allowed")
                    continue
                if command in CONTROLLER_COMMANDS and conn.role != "controller":
                    continue  # screens may not send controller commands
                if command in REVIEW_OR_CONTROLLER_COMMANDS and conn.role == "screen":
                    continue  # CDR-005 and CDR-007: the TV has no input; a screen's copy is dropped
                if command in REVIEW_COMMANDS and conn.role != "review":
                    # CDR-006: only the patient's review screen confirms or corrects; the controller is refused
                    # with `error`, and a screen, which never receives refusals, hears nothing.
                    await error(conn, "Only the patient's review screen can do that", command, "not_allowed")
                    continue
                if command not in handlers:
                    await error(conn, f"Unsupported command: {command}", command)
                    continue
                payload = message.get("payload", {})
                if command == "turn.submit":
                    task = asyncio.create_task(dispatch_turn(payload))
                    background.add(task)
                    task.add_done_callback(background.discard)
                else:
                    await dispatch(command, payload)
        except WebSocketDisconnect:
            pass
        finally:
            hub.remove(conn)
            # A controller that drops off mid-speech can never report the end, so the speech ends with it.
            if hub.visit.speech is not None and hub.visit.speech.conn is conn:
                await set_speech(None)

    return app
