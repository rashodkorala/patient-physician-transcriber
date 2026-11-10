// Patient summary end-to-end check (demo-night-mvp task 3.7, CDR-007, CDR-004, ADR-011; docs/demo-script.md
// beat 9). The summary appears on /review, /screen, and /control only once it has passed its value check, in the
// patient's language with the confirmed dose; Listen on /review has /control read it aloud a sentence at a time as
// {summaryId}.{n} through the speak queue, with the sentence being read marked; Stop ends it. The refusal is
// checked by e2e/summary-refused.mjs. Run against a freshly started fake-model stack.
// Usage: node e2e/summary.mjs [baseUrl] [serverPort] [screenshotDir]
import { giveConsent } from "./consent-steps.mjs";
import { capture, fakeVoice, open, sayConfirmed, saySettled, socket, start } from "./visit-steps.mjs";

const base = process.argv[2] ?? "http://localhost:3000";
const serverPort = process.argv[3] ?? "8000";
const shots = process.argv[4];
const { browser, fail, check } = await start();

const { page: tv, frames: tvFrames } = await open(browser, base, "/screen", { width: 1920, height: 1080 });
const { page: control, frames: controlFrames } = await open(browser, base, "/control", { width: 1280, height: 1000 });
const { page: review, frames: reviewFrames } = await open(browser, base, "/review", { width: 1024, height: 1366 });
// Turns and the consent notice play a short clip; summary sentences (ids with a dot) a long one.
const asked = await fakeVoice(control, (id) => /\.\d+$/.test(id));
const probe = await socket(base, serverPort, "controller");
if (probe.state.turns.length) await fail("run against a freshly started server");
await giveConsent(control);

await saySettled(control, "patient", "ਪੌੜੀਆਂ ਚੜ੍ਹਦਿਆਂ ਛਾਤੀ ਵਿੱਚ ਦਬਾਅ ਹੁੰਦਾ ਹੈ।");
await sayConfirmed(control, "Take one aspirin, 81 milligrams, once a day.");
await sayConfirmed(control, "If the pain is not better after 5 minutes, call 911.");
await check((await review.locator('[data-testid="review-summary"]').count()) === 0, "/review shows no summary before one is made");

// ---------- a passed summary ----------
await control.click('[data-testid="summary-generate"]');
await review.waitForSelector('[data-testid="review-summary"][data-state="ready"]', { timeout: 30000 });
const summary = (await probe.next("summary.ready", 30000)).payload;
const sentences = review.locator('[data-testid="summary-sentence"]');
await check((await sentences.count()) === summary.sentences.length && summary.sentences.length > 0, "/review shows every summary sentence");
const reviewText = await review.locator('[data-testid="review-summary"]').innerText();
await check(reviewText.includes("81") && reviewText.includes("911"), "the summary keeps the confirmed dose and number");
await check(
  (await review.locator('[data-testid="review-summary"] ol').getAttribute("lang")) === "pa-IN",
  "the summary is in the patient's language",
);
await tv.waitForSelector('[data-testid="summary"][data-state="ready"]', { timeout: 10000 });
await control.waitForSelector('[data-testid="control-summary"]', { timeout: 10000 });
await check(true, "/screen and /control show the passed summary");

// ---------- read aloud from the review screen, a sentence at a time ----------
await review.click('[data-testid="summary-listen"]');
const ids = summary.sentences.map((s) => s.sentenceId);
for (let i = 0; i < 50 && asked.filter((a) => ids.includes(a.id)).length < ids.length; i++) await control.waitForTimeout(100);
const spoken = asked.filter((a) => ids.includes(a.id));
await check(
  spoken.map((a) => a.id).join(",") === summary.sentences.map((_, n) => `${summary.summaryId}.${n}`).join(","),
  `/control asks for each sentence in order as {summaryId}.{n} (${spoken.map((a) => a.id).join(", ")})`,
);
await check(spoken.every((a) => a.language === "pa-IN"), "each sentence is asked for in Punjabi");
await review.waitForSelector('[data-testid="summary-sentence"][data-playing]', { timeout: 10000 });
await check(
  (await review.locator('[data-testid="summary-sentence"]').first().getAttribute("data-playing")) !== null,
  "/review marks the first sentence while it is read",
);
await tv.waitForSelector('[data-testid="speaking"]', { timeout: 5000 });
await check(true, "/screen shows the interpreter speaking");
// Each clip lasts 6 seconds, so the first sentence is still playing while these are taken.
await capture(shots, "summary-reading", [
  { page: review, which: "review", widths: [1024], height: 1366 },
  { page: tv, which: "screen", widths: [1920], height: 1080, fullPage: false },
]);
await check(
  (await review.locator('[data-testid="summary-sentence"]').first().getAttribute("data-playing")) !== null,
  "the first sentence is still being read",
);
await review.click('[data-testid="summary-stop"]');
await tv.waitForSelector('[data-testid="speaking"]', { state: "detached", timeout: 5000 });
await review.waitForSelector('[data-testid="summary-sentence"][data-playing]', { state: "detached", timeout: 5000 });
await check(true, "Stop ends the reading at once");
await control.waitForTimeout(7000);
await check((await tv.locator('[data-testid="speaking"]').count()) === 0, "no later sentence plays after Stop");
await check(!reviewFrames.join("\n").includes('"summary.speak"'), "/review never receives summary.speak");
await check(!tvFrames.join("\n").includes('"summary.speak"'), "/screen never receives summary.speak");
await check(controlFrames.join("\n").includes('"summary.speak"'), "/control receives summary.speak");
await capture(shots, "summary-ready", [
  { page: control, which: "control", widths: [1280, 390], height: 1000 },
  { page: review, which: "review", widths: [390], height: 1366 },
  { page: tv, which: "screen", widths: [390], height: 1080, fullPage: false },
]);

probe.ws.close();
await browser.close();
console.log("PASS: the patient summary, read aloud and stopped");
