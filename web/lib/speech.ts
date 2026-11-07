"use client";

/**
 * Push-to-talk recognition with Azure Speech, and the interpreter's voice.
 * The voice is the server's (ElevenLabs), asked for by turn or line id so the server decides what
 * may be spoken; Azure speaks only when the server has no voice for that language or its vendor fails.
 * Keys stay on the server; the browser uses short-lived Azure tokens.
 *
 * @implements ADR-005: Speech: Azure Speech primary, Google Speech backup
 * @implements ADR-010: Voice output: ElevenLabs Eleven v4 replaces OpenAI text-to-speech; Azure stays fallback
 * @implements IDR-001: Push-to-talk per speaker instead of diarisation
 * @see openspec/tdr/adr/adr-010-elevenlabs-voice-output.md
 */

import type { Language } from "./contracts";
import { VOICES } from "./languages";
import { serverHttpUrl } from "./socket";

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
  config.speechRecognitionLanguage = language;
  config.outputFormat = sdk.OutputFormat.Detailed;
  const recognizer = new sdk.SpeechRecognizer(config, sdk.AudioConfig.fromDefaultMicrophoneInput());

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
      await new Promise<void>((resolve, reject) => recognizer.stopContinuousRecognitionAsync(resolve, reject));
      recognizer.close();
      const confidence = confidences.length ? confidences.reduce((a, b) => a + b, 0) / confidences.length : 0;
      // Push-to-talk: speech ends at release, so the recognition flush after it counts as latency.
      return { text: parts.join(" ").trim(), confidence, endOfSpeechAt: releasedAt };
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
      const synthesizer = new sdk.SpeechSynthesizer(config, sdk.AudioConfig.fromDefaultSpeakerOutput());
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
    return response ? playStream(response) : speakWithAzure(text, language);
  });
  queue = next.catch(() => undefined);
  return next;
}

// One voice at a time, in the order asked for, whichever voice says it.
let queue: Promise<unknown> = Promise.resolve();

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

async function playStream(response: Response): Promise<{ startedAt: number }> {
  const streams = response.body && typeof MediaSource !== "undefined" && MediaSource.isTypeSupported("audio/mpeg");
  const url = streams ? streamUrl(response.body!) : URL.createObjectURL(await response.blob());
  const audio = new Audio(url);
  try {
    return await new Promise((resolve, reject) => {
      let startedAt = 0;
      audio.onplaying = () => (startedAt ||= Date.now());
      audio.onended = () => resolve({ startedAt: startedAt || Date.now() });
      audio.onerror = () => reject(new SpeechUnavailable("the voice could not be played"));
      audio.play().catch((error: Error) => reject(new SpeechUnavailable(error.message)));
    });
  } finally {
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

async function speakWithAzure(text: string, language: Language): Promise<{ startedAt: number }> {
  const sdk = await loadSdk();
  let synthesizer: Synthesizer;
  try {
    synthesizer = await synthesizerFor(language);
    synthesizer.authorizationToken = (await token()).token; // tokens expire after 10 minutes
  } catch (error) {
    throw error instanceof SpeechUnavailable ? error : new SpeechUnavailable(String(error));
  }

  return new Promise((resolve, reject) => {
    const fail = (reason: string) => {
      // Drop a broken synthesizer so the next turn connects afresh.
      synthesizers.delete(language);
      synthesizer.close();
      reject(new SpeechUnavailable(reason));
    };
    let startedAt = 0;
    synthesizer.synthesisStarted = () => {
      startedAt = Date.now();
    };
    synthesizer.speakTextAsync(
      text,
      (result) => {
        // A cancelled synthesis (an expired token, a dropped connection) still lands here.
        if (result.reason === sdk.ResultReason.SynthesizingAudioCompleted) {
          resolve({ startedAt: startedAt || Date.now() });
        } else {
          fail(result.errorDetails || "speech was cancelled");
        }
      },
      (error) => fail(String(error)),
    );
  });
}
