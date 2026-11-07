// Unit tests for the shared speaking signal (continuous-listening task 1.2). Usage: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import { createSpeakingState } from "./speaking.ts";

const turn = { speechId: "turn-1", language: "pa-IN" };
const line = { speechId: "line-1", language: "en-CA" };

const record = (state) => {
  const seen = [];
  state.onSpeaking((item) => seen.push(item?.speechId ?? null));
  return seen;
};

test("a new listener hears the current item straight away", () => {
  const state = createSpeakingState();
  assert.deepEqual(record(state), [null]);
  state.started(turn);
  assert.deepEqual(record(state), ["turn-1"]);
});

test("an item is current from its start to its end", () => {
  const state = createSpeakingState();
  const seen = record(state);
  const end = state.started(turn);
  assert.deepEqual(state.current(), turn);
  end();
  assert.equal(state.current(), null);
  assert.deepEqual(seen, [null, "turn-1", null]);
});

test("back-to-back items end one before the next starts, for listeners to smooth", () => {
  const state = createSpeakingState();
  const seen = record(state);
  state.started(line)();
  state.started(turn)();
  assert.deepEqual(seen, [null, "line-1", null, "turn-1", null]);
});

test("a start during another item hands over, and the stale end is ignored", () => {
  const state = createSpeakingState();
  const seen = record(state);
  const endLine = state.started(line);
  const endTurn = state.started(turn);
  endLine();
  assert.deepEqual(state.current(), turn);
  endTurn();
  assert.deepEqual(seen, [null, "line-1", "turn-1", null]);
});

test("ending twice, as a failure after an end might, does not end the next item", () => {
  const state = createSpeakingState();
  const seen = record(state);
  const end = state.started(turn);
  end();
  const next = state.started(turn); // the same id spoken again is its own stretch
  end();
  assert.deepEqual(state.current(), turn);
  next();
  assert.deepEqual(seen, [null, "turn-1", null, "turn-1", null]);
});

test("an unsubscribed listener hears nothing more", () => {
  const state = createSpeakingState();
  const seen = [];
  const unsubscribe = state.onSpeaking((item) => seen.push(item));
  unsubscribe();
  state.started(turn);
  assert.deepEqual(seen, [null]);
});
