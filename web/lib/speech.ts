"use client";

/**
 * Push-to-talk and hands-free recognition with Azure Speech, and the interpreter's voice.
 * The voice is the server's (ElevenLabs), asked for by turn or line id so the server decides what
 * may be spoken; Azure speaks only when the server has no voice for that language or its vendor fails.
 * Keys stay on the server; the browser uses short-lived Azure tokens.
 * Both voices play through one audio element path, which drives the shared speaking signal.
 *
 * @implements ADR-005: Speech: Azure Speech primary, Google Speech backup
 * @implements ADR-010: Voice output: ElevenLabs Eleven v4 replaces OpenAI text-to-speech; Azure stays fallback
 * @implements IDR-001: Push-to-talk per speaker instead of diarisation
 * @see openspec/tdr/adr/adr-010-elevenlabs-voice-output.md
 */

import type { Language } from "./contracts";
import { RECOGNITION, VOICES } from "./languages";
import { serverHttpUrl } from "./socket";
import { createSpeakingState } from "./speaking";

type Sdk = typeof import("microsoft-cognitiveservices-speech-sdk");

let sdkPromise: Promise<Sdk> | null = null;
const loadSdk = () => (sdkPromise ??= import("microsoft-cognitiveservices-speech-sdk"));

let cached: { token: string; region: string; expiresAt: number } | null = null;

export class SpeechUnavailable extends Error {}

async function token(): Promise<{ token: string; region: string }> {
  if (cached && Date.now() < cached.expiresAt) return cached;
  const response = await fetch(`${serverHttpUrl()}/api/speech-token`);
  if (!response.ok) throw new SpeechUnavailable(`Speech token unavailable (${response.status})`);
  const body = (await response.json()) as { token: string; region: string; expiresInSeconds: number };
  // Refresh a minute early so a long turn never runs on an expired token.
  cached = { token: body.token, region: body.region, expiresAt: Date.now() + (body.expiresInSeconds - 60) * 1000 };
  return cached;
}

export interface Captured {
  text: string;
  confidence: number;
  endOfSpeechAt: number;
}

export interface Capture {
  stop(): Promise<Captured>;
}

/** Starts recognising when the speaker's button is pressed; stop() on release. */
export async function startCapture(language: Language): Promise<Capture> {
  const sdk = await loadSdk();
  const { token: authToken, region } = await token();
  const config = sdk.SpeechConfig.fromAuthorizationToken(authToken, region);
  config.speechRecognitionLanguage = RECOGNITION[language];
  config.outputFormat = sdk.OutputFormat.Detailed;
  const recognizer = new sdk.SpeechRecognizer(config, sdk.AudioConfig.fromDefaultMicrophoneInput());

  // A refused locale, an expired token, or a dropped connection cancels recognition; without this the
  // physician only saw "Nothing was heard".
  let failure: string | null = null;
  recognizer.canceled = (_sender, event) => {
    if (event.reason === sdk.CancellationReason.Error) failure ??= event.errorDetails || "recognition was cancelled";
  };

  const parts: string[] = [];
  const confidences: number[] = [];
  recognizer.recognized = (_sender, event) => {
    if (event.result.reason !== sdk.ResultReason.RecognizedSpeech || !event.result.text) return;
    parts.push(event.result.text);
    try {
      const detail = JSON.parse(event.result.json) as { NBest?: { Confidence?: number }[] };
      const confidence = detail.NBest?.[0]?.Confidence;
      if (typeof confidence === "number") confidences.push(confidence);
    } catch {
      // Detailed output missing: confidence stays unknown for this segment.
    }
  };

  await new Promise<void>((resolve, reject) => recognizer.startContinuousRecognitionAsync(resolve, reject));

  return {
    stop: async () => {
      const releasedAt = Date.now();
      await new Promise<void>((resolve, reject) => recognizer.stopContinuousRecognitionAsync(resolve, reject)).catch(
        (error) => void (failure ??= String(error)),
      );
      recognizer.close();
      const confidence = confidences.length ? confidences.reduce((a, b) => a + b, 0) / confidences.length : 0;
      if (failure && !parts.length) throw new SpeechUnavailable(failure);
      // Push-to-talk: speech ends at release, so the recognition flush after it counts as latency.
      return { text: parts.join(" ").trim(), confidence, endOfSpeechAt: releasedAt };
    },
  };
}

/** One utterance heard hands-free: its text and the recognition locale it was identified as. */
export interface Heard {
  text: string;
  recognition: string;
  confidence: number;
  endOfSpeechAt: number;
}

export interface Listening {
  /** Muted, the microphone sends silence, and anything still heard is dropped. */
  mute(muted: boolean): void;
  stop(): Promise<void>;
}

/** What listens hands-free: Azure, or a fake standing in for it in end-to-end tests. */
interface ListeningSource {
  setMuted(muted: boolean): void;
  stop(): Promise<void>;
}

type FakeListening = (recognition: string[], deliver: (heard: Heard) => void) => ListeningSource;

// Silence that ends an utterance: long enough for a pause mid-sentence, short enough to keep turns quick.
const SILENCE_MS = 800;

/**
 * Listens continuously and reports each utterance with the language it was identified as, among the
 * visit's two recognition locales.
 * @implements IDR-004: Hands-free continuous listening, with the speaker found by spoken language
 */
export async function startListening(
  recognition: string[],
  onHeard: (heard: Heard) => void,
  onError: (message: string) => void,
): Promise<Listening> {
  let muted = false;
  const deliver = (heard: Heard) => {
    if (!muted && heard.text.trim()) onHeard(heard);
  };
  const fake = fakeListening();
  const source = fake ? fake(recognition, deliver) : await listenWithAzure(recognition, deliver, onError);
  return {
    mute(next) {
      muted = next;
      source.setMuted(next);
    },
    stop: () => source.stop(),
  };
}

/** End-to-end tests replace the recogniser; the hook exists only in builds made with the test flag. */
function fakeListening(): FakeListening | null {
  if (process.env.NEXT_PUBLIC_SPEECH_TEST_HOOKS !== "on") return null;
  return (window as unknown as { __fakeListening?: FakeListening }).__fakeListening ?? null;
}

async function listenWithAzure(
  recognition: string[],
  deliver: (heard: Heard) => void,
  onError: (message: string) => void,
): Promise<ListeningSource> {
  const sdk = await loadSdk();
  const { token: authToken, region } = await token();
  // Echo cancellation keeps the room's speakers out; muting the track covers the interpreter's own voice.
  const microphone = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
  const config = sdk.SpeechConfig.fromAuthorizationToken(authToken, region);
  config.outputFormat = sdk.OutputFormat.Detailed;
  config.setProperty(sdk.PropertyId.SpeechServiceConnection_LanguageIdMode, "Continuous");
  config.setProperty(sdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, String(SILENCE_MS));
  const recognizer = sdk.SpeechRecognizer.FromConfig(
    config,
    sdk.AutoDetectSourceLanguageConfig.fromLanguages(recognition),
    sdk.AudioConfig.fromStreamInput(microphone),
  );

  recognizer.recognized = (_sender, event) => {
    if (event.result.reason !== sdk.ResultReason.RecognizedSpeech || !event.result.text) return;
    let confidence = 0;
    try {
      const detail = JSON.parse(event.result.json) as { NBest?: { Confidence?: number }[] };
      confidence = detail.NBest?.[0]?.Confidence ?? 0;
    } catch {
      // Detailed output missing: confidence stays unknown for this utterance.
    }
    deliver({
      text: event.result.text,
      recognition: sdk.AutoDetectSourceLanguageResult.fromResult(event.result).language,
      confidence,
      // The utterance ended when the silence that closed it began.
      endOfSpeechAt: Date.now() - SILENCE_MS,
    });
  };
  recognizer.canceled = (_sender, event) => {
    if (event.reason === sdk.CancellationReason.Error) onError(event.errorDetails || "listening stopped");
  };

  // Tokens last ten minutes and a hands-free visit runs longer, so the live recogniser gets fresh ones.
  const refresh = setInterval(() => {
    token()
      .then(({ token: fresh }) => (recognizer.authorizationToken = fresh))
      .catch(() => undefined);
  }, 5 * 60 * 1000);

  try {
    await new Promise<void>((resolve, reject) => recognizer.startContinuousRecognitionAsync(resolve, reject));
  } catch (error) {
    clearInterval(refresh);
    recognizer.close();
    microphone.getTracks().forEach((track) => track.stop());
    throw new SpeechUnavailable(String(error));
  }

  return {
    setMuted: (muted) => microphone.getAudioTracks().forEach((track) => (track.enabled = !muted)),
    stop: async () => {
      clearInterval(refresh);
      await new Promise<void>((resolve, reject) => recognizer.stopContinuousRecognitionAsync(resolve, reject)).catch(
        () => undefined,
      );
      recognizer.close();
      microphone.getTracks().forEach((track) => track.stop());
    },
  };
}

type Synthesizer = import("microsoft-cognitiveservices-speech-sdk").SpeechSynthesizer;

// One synthesizer per language, connected ahead of time: a new one per turn opened a fresh
// connection to Azure every time, adding its set-up to every spoken translation.
const synthesizers = new Map<Language, Promise<Synthesizer>>();

function synthesizerFor(language: Language): Promise<Synthesizer> {
  let ready = synthesizers.get(language);
  if (!ready) {
    ready = (async () => {
      const sdk = await loadSdk();
      const { token: authToken, region } = await token();
      const config = sdk.SpeechConfig.fromAuthorizationToken(authToken, region);
      config.speechSynthesisVoiceName = VOICES[language];
      // MP3 with no speaker output: the SDK's own player plays a reused synthesizer's audio as one
      // endless stream, so it never says when an utterance ends. playStream plays it instead.
      config.speechSynthesisOutputFormat = sdk.SpeechSynthesisOutputFormat.Audio24Khz48KBitRateMonoMp3;
      const synthesizer = new sdk.SpeechSynthesizer(config, null);
      sdk.Connection.fromSynthesizer(synthesizer).openConnection();
      return synthesizer;
    })();
    // A failed start (no key, no network) is not cached, so the next turn tries again.
    ready.catch(() => synthesizers.delete(language));
    synthesizers.set(language, ready);
  }
  return ready;
}

/** Loads the SDK, fetches a token, and connects a voice per language; failures stay silent here. */
export async function warmUp(languages: Language[]): Promise<void> {
  await Promise.all([...new Set(languages)].map((language) => synthesizerFor(language).catch(() => undefined)));
}

/**
 * Speaks checked text, a turn's translation or an interpreter line, by its id.
 * Resolves with the time audio started, for latency logging (task 1.7).
 */
export function speak(text: string, language: Language, speechId: string): Promise<{ startedAt: number }> {
  const audio = serverSpeech(speechId, language); // fetched now, while anything before it still plays
  const next = queue.then(async () => {
    const response = await audio;
    const item = { speechId, language };
    return response ? playStream(response, item) : speakWithAzure(text, item);
  });
  queue = next.catch(() => undefined);
  return next;
}

// One voice at a time, in the order asked for, whichever voice says it.
let queue: Promise<unknown> = Promise.resolve();

/** A turn or interpreter line, by the id its audio is asked for by, in one language. */
export interface Speaking {
  speechId: string;
  language: Language;
}

const speaking = createSpeakingState<Speaking>();

/** The item whose audio is audible now, whichever voice says it, or null. */
export const current = speaking.current;

export const isSpeaking = (): boolean => speaking.current() !== null;

/** Calls the listener with the current item now, then on every change; returns an unsubscribe. */
export const onSpeaking = speaking.onSpeaking;

/** The server's audio, or null when Azure should speak instead. */
async function serverSpeech(speechId: string, language: Language): Promise<Response | null> {
  let response: Response;
  try {
    const query = new URLSearchParams({ language });
    response = await fetch(`${serverHttpUrl()}/api/speech/${encodeURIComponent(speechId)}?${query}`);
  } catch {
    return null; // server unreachable for audio: the turn already passed its checks, so Azure says it
  }
  if (response.ok) return response;
  // 404 is the server refusing: this was never cleared to speak, so no voice may say it.
  if (response.status === 404) throw new SpeechUnavailable("the server did not clear this to be spoken");
  return null; // 503: no server voice for this language, or the vendor failed before any audio
}

async function playStream(response: Response, item: Speaking): Promise<{ startedAt: number }> {
  const streams = response.body && typeof MediaSource !== "undefined" && MediaSource.isTypeSupported("audio/mpeg");
  const url = streams ? streamUrl(response.body!) : URL.createObjectURL(await response.blob());
  const audio = new Audio(url);
  let ended: (() => void) | undefined;
  try {
    return await new Promise((resolve, reject) => {
      let startedAt = 0;
      audio.onplaying = () => {
        startedAt ||= Date.now();
        ended ??= speaking.started(item);
      };
      audio.onended = () => resolve({ startedAt: startedAt || Date.now() });
      audio.onerror = () => reject(new SpeechUnavailable("the voice could not be played"));
      audio.play().catch((error: Error) => reject(new SpeechUnavailable(error.message)));
    });
  } finally {
    ended?.();
    URL.revokeObjectURL(url);
  }
}

/** Feeds audio to the element as it arrives, so speech starts before synthesis finishes. */
function streamUrl(body: ReadableStream<Uint8Array<ArrayBuffer>>): string {
  const source = new MediaSource();
  source.addEventListener(
    "sourceopen",
    async () => {
      const buffer = source.addSourceBuffer("audio/mpeg");
      const reader = body.getReader();
      try {
        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer.appendBuffer(value);
          await new Promise((resolve) => buffer.addEventListener("updateend", resolve, { once: true }));
        }
        source.endOfStream();
      } catch {
        if (source.readyState === "open") source.endOfStream("network");
      }
    },
    { once: true },
  );
  return URL.createObjectURL(source);
}

async function speakWithAzure(text: string, item: Speaking): Promise<{ startedAt: number }> {
  const { language } = item;
  const sdk = await loadSdk();
  let synthesizer: Synthesizer;
  try {
    synthesizer = await synthesizerFor(language);
    synthesizer.authorizationToken = (await token()).token; // tokens expire after 10 minutes
  } catch (error) {
    throw error instanceof SpeechUnavailable ? error : new SpeechUnavailable(String(error));
  }

  // Chunks reach the player as Azure makes them, so speech starts before synthesis finishes.
  let firstChunk: () => void;
  let failed: (error: SpeechUnavailable) => void;
  const audible = new Promise<void>((resolve, reject) => ((firstChunk = resolve), (failed = reject)));
  const body = new ReadableStream<Uint8Array<ArrayBuffer>>({
    start(controller) {
      const fail = (reason: string) => {
        // Drop a broken synthesizer so the next turn connects afresh.
        synthesizers.delete(language);
        synthesizer.close();
        const error = new SpeechUnavailable(reason);
        failed(error);
        controller.error(error);
      };
      synthesizer.synthesizing = (_sender, event) => {
        controller.enqueue(new Uint8Array(event.result.audioData));
        firstChunk();
      };
      synthesizer.speakTextAsync(
        text,
        (result) => {
          // A cancelled synthesis (an expired token, a dropped connection) still lands here.
          if (result.reason === sdk.ResultReason.SynthesizingAudioCompleted) {
            firstChunk(); // an empty text has no chunks, and nothing to wait for
            controller.close();
          } else {
            fail(result.errorDetails || "speech was cancelled");
          }
        },
        (error) => fail(String(error)),
      );
    },
  });
  // A failure before any audio keeps its own reason, instead of a generic playback error.
  await audible;
  return playStream(new Response(body, { headers: { "Content-Type": "audio/mpeg" } }), item);
}
