"use client";

/**
 * Push-to-talk recognition and spoken translations with Azure Speech.
 * The key stays on the server; the browser uses short-lived tokens.
 *
 * @implements ADR-005: Speech: Azure Speech primary, Google Speech backup
 * @implements IDR-001: Push-to-talk per speaker instead of diarisation
 * @see openspec/tdr/adr/adr-005-speech-provider.md
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

/** Speaks a translation; resolves with the time audio started, for latency logging (task 1.7). */
export async function speak(text: string, language: Language): Promise<{ startedAt: number }> {
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
