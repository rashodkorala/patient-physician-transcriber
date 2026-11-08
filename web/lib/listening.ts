/**
 * Hands-free listening rules: whose turn an utterance is, which turns wait for the physician, and when
 * the microphone is muted. Type imports only, so it is unit-tested without the speech SDK.
 *
 * @implements IDR-004: Hands-free continuous listening, with the speaker found by spoken language
 * @see openspec/changes/continuous-listening/design.md
 */

import type { Language, Speaker } from "./contracts";

/** One party: who they are, the language of their turns, and the locale their speech is recognised in. */
export interface Side {
  speaker: Speaker;
  language: Language;
  recognition: string;
}

/** The side whose recognition locale was detected, or null when it is neither. */
export function sideFor(detected: string, sides: readonly Side[]): Side | null {
  return sides.find((side) => side.recognition === detected) ?? null;
}

/** Replies this short are often heard in the wrong language, so the physician says whose they were. */
export const SHORT_REPLY_WORDS = 2;

export function isShortReply(text: string): boolean {
  const words = text.replace(/[\p{P}\p{S}]/gu, " ").split(/\s+/).filter(Boolean);
  return words.length <= SHORT_REPLY_WORDS;
}

/** How long the microphone stays muted after the interpreter's voice stops, for its echo to die away. */
export const VOICE_TAIL_MS = 300;

export interface MuteReasons {
  /** The interpreter's voice is playing, or stopped less than VOICE_TAIL_MS ago. */
  voice: boolean;
  /** A dose is waiting for read-back, so no new turn may slip in. */
  readback: boolean;
  /** The physician is holding a push-to-talk control, which takes over. */
  pushToTalk: boolean;
}

export type ListeningState = "listening" | "voice" | "readback" | "pushToTalk";

/** What hands-free listening is doing; anything but "listening" means the microphone is muted. */
export function listeningState(reasons: MuteReasons): ListeningState {
  if (reasons.pushToTalk) return "pushToTalk";
  if (reasons.readback) return "readback";
  if (reasons.voice) return "voice";
  return "listening";
}
