// Contrast check of the clinic tokens (ADR-012, trust-across-the-barrier task 3.1): every text token meets WCAG AA
// (4.5:1) on the backgrounds it is drawn on, in the light set and in the dark set of web/app/globals.css.
//
// @implements ADR-012: Clinic design system
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const css = readFileSync(new URL("../app/globals.css", import.meta.url), "utf8");

/** The hex tokens in the first block after `marker`. */
function tokens(marker) {
  const start = css.indexOf(marker);
  assert.ok(start >= 0, `globals.css has ${marker}`);
  const open = css.indexOf("{", css.indexOf(":root", start));
  const block = css.slice(open, css.indexOf("}", open));
  return Object.fromEntries([...block.matchAll(/--([a-z-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)].map((m) => [m[1], m[2]]));
}

const light = tokens(":root");
const dark = { ...light, ...tokens("@media (prefers-color-scheme: dark)") };

function luminance(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// Each text token, with the backgrounds it sits on: the page, a card, and its own soft tint where it has one.
const PAIRS = [
  ["ink", ["paper", "surface", "field", "care-soft", "physician-soft", "patient-soft", "companion-soft", "ok-soft", "wait-soft", "stop-soft"]],
  ["muted", ["paper", "surface", "care-soft", "physician-soft", "patient-soft", "companion-soft"]],
  ["care", ["paper", "surface", "care-soft"]],
  ["care-ink", ["care"]],
  ["physician", ["paper", "surface", "physician-soft"]],
  ["patient", ["paper", "surface", "patient-soft"]],
  ["companion", ["paper", "surface", "companion-soft"]],
  ["ok", ["paper", "surface", "ok-soft"]],
  ["wait", ["paper", "surface", "wait-soft"]],
  ["stop", ["paper", "surface", "stop-soft"]],
];

for (const [scheme, set] of [
  ["light", light],
  ["dark", dark],
]) {
  test(`every text token meets AA on its backgrounds in the ${scheme} set (ADR-012)`, () => {
    const failures = [];
    for (const [text, backgrounds] of PAIRS) {
      for (const background of backgrounds) {
        assert.ok(set[text] && set[background], `${scheme} defines --${text} and --${background}`);
        const r = ratio(set[text], set[background]);
        if (r < 4.5) failures.push(`--${text} on --${background}: ${r.toFixed(2)}`);
      }
    }
    assert.deepEqual(failures, []);
  });
}
