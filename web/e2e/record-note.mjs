// Record view end-to-end check (demo-night-mvp tasks 3.6 and 5.2, CDR-007, CDR-006, ADR-011, TDM-002;
// docs/demo-script.md beat 9). /record connects as a controller and shows the note with exactly one tag per
// sentence and a link to its sources on every sentence; selecting a sentence highlights its source turn with the
// original and the translation, at the version cited (a patient's correction cites its amendment); blocked turns
// are listed as not in the note; the presenter's injected turn is marked; the note turns stale when the record
// grows. Nothing of the note reaches /screen or /review. Run against a freshly started fake-model stack and a
// web build made with NEXT_PUBLIC_SPEECH_TEST_HOOKS=on.
// Usage: node e2e/record-note.mjs [baseUrl] [serverPort] [screenshotDir]
import { giveConsent } from "./consent-steps.mjs";
import { capture, fakeRecogniser, open, say, sayConfirmed, saySettled, socket, start } from "./visit-steps.mjs";

const base = process.argv[2] ?? "http://localhost:3000";
const serverPort = process.argv[3] ?? "8000";
const shots = process.argv[4];
const { browser, fail, check } = await start();

const DOSE = "Use the nitroglycerin spray: 0.4 milligrams, one spray under your tongue when the chest pain starts.";
const TAGS = ["patient_stated", "physician_stated", "companion_stated", "interpreter_stated", "ai_inference"];

const { frames: tvFrames } = await open(browser, base, "/screen", { width: 1920, height: 1080 });
const { page: control } = await open(browser, base, "/control", { width: 1280, height: 1000 });
const { page: review, frames: reviewFrames } = await open(browser, base, "/review", { width: 1024, height: 1366 });
const probe = await socket(base, serverPort, "controller");
if (probe.state.turns.length) await fail("run against a freshly started server");
await giveConsent(control);

// ---------- a short visit: a complaint, a blocked (injected) dose and its repeat, and a correction ----------
await saySettled(control, "patient", "ਪੌੜੀਆਂ ਚੜ੍ਹਦਿਆਂ ਛਾਤੀ ਵਿੱਚ ਦਬਾਅ ਹੁੰਦਾ ਹੈ।");
await saySettled(control, "physician", "You did not have a heart attack. The most likely cause is angina.");
await control.click('[data-testid="presenter"] summary');
await control.click('[data-testid="injection-arm"]');
await control.waitForSelector('[data-testid="injection-state"]', { timeout: 10000 });
await say(control, "physician", DOSE);
await control.waitForSelector('[data-testid="turn"][data-injected]', { timeout: 20000 });
await sayConfirmed(control, DOSE);
await fakeRecogniser(review);
await review.evaluate(() => window.__heard.push("ਪੌੜੀਆਂ ਚੜ੍ਹਦਿਆਂ ਛਾਤੀ ਵਿੱਚ ਭਾਰੀ ਦਬਾਅ ਹੁੰਦਾ ਹੈ।"));
const first = review.locator('[data-testid="review-turn"]').first();
await first.locator('[data-testid="review-correct"]').click();
await first.locator('[data-testid="review-correct"][data-recording]').waitFor({ timeout: 5000 });
await first.locator('[data-testid="review-correct"]').click();
await review.waitForFunction(() => document.querySelector('[data-testid="review-turn"]')?.dataset.version !== "original", null, {
  timeout: 20000,
});
const correctedTurn = await first.getAttribute("data-turn-id");

// ---------- the record view ----------
const { page: record, frames: recordFrames } = await open(browser, base, "/record", { width: 1280, height: 1000 });
await record.waitForSelector('[data-testid="source-turn"][data-injected]', { timeout: 10000 });
await check(true, "/record marks the presenter's injected turn");
await record.click('[data-testid="note-generate"]');
await record.waitForSelector('[data-testid="note-sentence"]', { timeout: 30000 });
const sentences = record.locator('[data-testid="note-sentence"]');
const count = await sentences.count();
await check(count > 0, `the note has ${count} sentences`);
for (let i = 0; i < count; i++) {
  const s = sentences.nth(i);
  const tags = await s.locator('[data-testid="note-tag"]').count();
  const tag = await s.getAttribute("data-tag");
  const links = await s.locator('[data-testid="note-source-links"] > *').count();
  if (tags !== 1 || !TAGS.includes(tag) || links < 1) await fail(`sentence ${i + 1} has ${tags} tags (${tag}) and ${links} source links`);
}
await check(true, "every sentence has exactly one tag and at least one source link");

// Click to source: the cited turn is highlighted with its original and translation.
const patientSentence = record.locator('[data-testid="note-sentence"][data-tag="patient_stated"]').first();
await patientSentence.click();
const selected = record.locator('[data-testid="source-turn"][data-selected]');
await selected.first().waitFor({ timeout: 5000 });
const selectedText = await selected.first().innerText();
await check(
  (await selected.first().getAttribute("data-turn-id")) === correctedTurn && selectedText.includes("ਭਾਰੀ") && selectedText.includes("[en-CA]"),
  "selecting a patient-stated sentence highlights its turn at the corrected version, with original and translation",
);
await check(selectedText.toLowerCase().includes("corrected by the patient"), "the cited version is marked as the patient's correction");
await check((await record.locator('[data-testid="source-turn"][data-selected]').count()) >= 1, "the source is highlighted in the panel");
await check(
  (await record.locator('[data-testid="note-gap"]').count()) >= 1 &&
    (await record.locator('[data-testid="source-turn"][data-gap][data-injected]').count()) === 1,
  "the blocked turn is listed as not in the note",
);
await capture(shots, "record-note", [{ page: record, which: "record", widths: [1280, 390], height: 1000 }]);

// The note in /control's summary row, and the stale mark once the record grows.
await control.waitForSelector('[data-testid="note-row-state"]:has-text("sentence")', { timeout: 10000 });
await saySettled(control, "physician", "Thank you. Rest when you need to.");
await record.waitForSelector('[data-testid="note-stale"]', { timeout: 10000 });
await check(true, "the note is marked stale when the record grows after it");
await check((await record.locator('[data-testid="note-sentence"]').count()) === count, "a stale note is never silently updated");

// ---------- the note never leaves the controllers ----------
for (const [who, frames] of [
  ["/screen", tvFrames],
  ["/review", reviewFrames],
]) {
  const wire = frames.join("\n");
  await check(!wire.includes('"note.ready"') && !wire.includes('"note.status"') && !/"note":\{/.test(wire), `${who} never receives the note`);
}
await check(recordFrames.join("\n").includes('"note.ready"'), "/record, a controller connection, receives note.ready");

probe.ws.close();
await browser.close();
console.log("PASS: the record view, note provenance, and the injection mark");
