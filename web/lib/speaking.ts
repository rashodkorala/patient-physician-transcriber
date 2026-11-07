/**
 * What the interpreter's voice is saying right now, whichever voice says it: the item whose audio is
 * audible, or null. Hands-free listening pauses on it so it never transcribes the interpreter, and the
 * controller reports it to the visit. Timing policy (tails, easing) belongs to each listener, not here.
 * No imports, so it is unit-tested without the speech SDK.
 *
 * @implements ADR-005: Speech: Azure Speech primary, Google Speech backup
 * @see openspec/changes/continuous-listening/design.md
 */

export interface SpeakingState<Item> {
  current(): Item | null;
  /** Calls the listener with the current item now, then on every change; returns an unsubscribe. */
  onSpeaking(listener: (item: Item | null) => void): () => void;
  /**
   * Marks the item's audio as audible, taking over from any other; call the returned function once its
   * audio ends or fails. It does nothing if called again, or if another item has taken over since.
   */
  started(item: Item): () => void;
}

export function createSpeakingState<Item>(): SpeakingState<Item> {
  // A fresh object per start, so an item spoken twice still ends only its own stretch.
  let audible: { item: Item } | null = null;
  const listeners = new Set<(item: Item | null) => void>();
  const set = (stretch: { item: Item } | null) => {
    audible = stretch;
    listeners.forEach((listener) => listener(stretch?.item ?? null));
  };

  return {
    current: () => audible?.item ?? null,
    onSpeaking(listener) {
      listeners.add(listener);
      listener(audible?.item ?? null);
      return () => listeners.delete(listener);
    },
    started(item) {
      const stretch = { item };
      set(stretch);
      return () => {
        if (audible === stretch) set(null);
      };
    },
  };
}
