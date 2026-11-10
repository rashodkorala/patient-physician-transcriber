// Review screen end-to-end check (demo-night-mvp tasks 3.5 and 5.2, CDR-005, CDR-006, TDM-002; docs/demo-script.md
// beats 2, 5, and 8). The patient consents with their own tap on /review; the presenter's injected dose shows on
// /review as blocked, then repeated, with no wrong dose and no injection label; the patient corrects their own
// turn by re-speaking it and the history keeps both versions; a correction whose dose changes is refused and the
// current version stays; a confirmation names the current version; a refused command reaches only the review
// connection as command.refused. Run against a freshly started fake-model stack and a web build made with
// NEXT_PUBLIC_SPEECH_TEST_HOOKS=on.
// Usage: node e2e/review.mjs [baseUrl] [serverPort] [screenshotDir]
import { giveConsentOnReview } from "./consent-steps.mjs";
import { capture, fakeRecogniser, open, say, sayConfirmed, saySettled, socket, start, turnCount } from "./visit-steps.mjs";

const base = process.argv[2] ?? "http://localhost:3000";
const serverPort = process.argv[3] ?? "8000";
const shots = process.argv[4];
const { browser, fail, check } = await start();

const DOSE = "Use the nitroglycerin spray: 0.4 milligrams, one spray under your tongue when the chest pain starts.";
const HEARD = "ਮੇਰੇ ਪਿਤਾ ਜੀ 65 ਸਾਲ ਦੀ ਉਮਰ ਵਿੱਚ ਗੁਜ਼ਰ ਗਏ ਸਨ।"; // "65" misheard for "55" (beat 3.4)
const CORRECTED = "ਮੇਰੇ ਪਿਤਾ ਜੀ 55 ਸਾਲ ਦੀ ਉਮਰ ਵਿੱਚ ਗੁਜ਼ਰ ਗਏ ਸਨ।";

const { page: tv, frames: tvFrames } = await open(browser, base, "/screen", { width: 1920, height: 1080 });
const { page: control } = await open(browser, base, "/control", { width: 1280, height: 1000 });
const { page: review, frames: reviewFrames } = await open(browser, base, "/review", { width: 1024, height: 1366 });

const probe = await socket(base, serverPort, "controller");
if (probe.state.consent || probe.state.turns.length) await fail("run against a freshly started server");

// ---------- beat 2: the patient's own consent ----------
await check((await review.locator('[data-testid="review-consent"]').innerText()).includes("ਦੁਭਾਸ਼ੀਆ"), "/review shows the notice in Punjabi");
await capture(shots, "review-consent", [{ page: review, which: "review", widths: [1024, 390], height: 1366 }]);
await giveConsentOnReview(review);
await control.waitForSelector('[data-testid="consent"][data-state="given"][data-by="patient"]', { timeout: 10000 });
await check(true, "a tap on /review is recorded as consent by the patient");

// ---------- beat 3.4, then beat 5: the injected dose is blocked and repeated ----------
await saySettled(control, "patient", HEARD);
await control.click('[data-testid="presenter"] summary');
await control.click('[data-testid="injection-arm"]');
await control.waitForSelector('[data-testid="injection-state"]', { timeout: 10000 });
const before = await turnCount(control);
await say(control, "physician", DOSE);
await control.waitForSelector('[data-testid="turn"][data-injected]', { timeout: 20000 });
await check((await turnCount(control)) === before + 1, "the injected dose is blocked on /control");
await sayConfirmed(control, DOSE);

const blocked = review.locator('[data-testid="review-turn"][data-status="blocked"]');
await blocked.waitFor({ timeout: 15000 });
const blockedText = await blocked.innerText();
await check(
  blockedText.includes("ਹੇਠਾਂ ਦੁਬਾਰਾ ਕਿਹਾ ਗਿਆ") && blockedText.includes("Said again below"),
  "/review shows the injected turn as not spoken, then said again, in both languages",
);
await check(!/(?<![\d.])4 ਮਿਲੀਗ੍ਰਾਮ/.test(await review.locator("main").innerText()), "/review never shows the wrong dose");
const reviewText = (await review.locator("main").innerText()).toLowerCase();
await check(!reviewText.includes("mismatch") && !reviewText.includes("presenter") && !reviewText.includes("inject"), "/review shows no injection label");
const repeatedHref = await blocked.locator('[data-testid="repeated-link"]').getAttribute("href");
const repeatedId = repeatedHref?.replace("#turn-", "");
await check(
  (await review.locator(`[data-testid="review-turn"][data-turn-id="${repeatedId}"]`).getAttribute("data-status")) === "final",
  "the blocked turn links to the repeated turn, which was spoken",
);

// ---------- beat 8: the patient re-speaks a correction ----------
await fakeRecogniser(review);
const mine = review.locator('[data-testid="review-turn"]').first();
const turnId = await mine.getAttribute("data-turn-id");
await review.evaluate((text) => window.__heard.push(text), CORRECTED);
await mine.locator('[data-testid="review-correct"]').click();
await mine.locator('[data-testid="review-correct"][data-recording]').waitFor({ timeout: 5000 });
await capture(shots, "review-recording", [{ page: review, which: "review", widths: [1024], height: 1366, fullPage: false }]);
await mine.locator('[data-testid="review-correct"]').click();
await review.waitForFunction(
  (id) => document.querySelector(`[data-testid="review-turn"][data-turn-id="${id}"]`)?.dataset.version !== "original",
  turnId,
  { timeout: 20000 },
);
await check((await mine.innerText()).includes("55"), "the corrected turn shows the correction");
await mine.locator('[data-testid="review-history"] summary').click();
const history = mine.locator('[data-testid="history-version"]');
await check((await history.count()) === 2, "the history shows both versions");
await check(
  (await history.nth(0).innerText()).includes("65") && (await history.nth(1).innerText()).includes("55"),
  "the original stays in the history beside the correction",
);
await check((await history.nth(1).getAttribute("data-current")) !== null, "the correction is the current version");
await control.waitForSelector(`[data-testid="turn"] [data-testid="corrected"]`, { timeout: 10000 });
await check(true, "/control marks the turn as corrected by the patient");
await tv.waitForTimeout(300);

// A correction whose dose changes in translation is refused, and the current version stays.
const version = await mine.getAttribute("data-version");
await review.evaluate(() => window.__heard.push("ਮੈਂ 500 ਮਿਲੀਗ੍ਰਾਮ ਲੈਂਦਾ ਹਾਂ (test: mismatch)"));
await mine.locator('[data-testid="review-correct"]').click();
await mine.locator('[data-testid="review-correct"][data-recording]').waitFor({ timeout: 5000 });
await mine.locator('[data-testid="review-correct"]').click();
await mine.locator('[data-testid="correction-refused"]').waitFor({ timeout: 20000 });
await check((await mine.getAttribute("data-version")) === version, "a refused correction keeps the current version");
await check(
  (await mine.locator('[data-testid="correction-refused"]').innerText()).includes("Please say it again"),
  "the patient is asked to say it again, in both languages",
);

// Confirm the current version.
await mine.locator('[data-testid="review-confirm"]').click();
await review.waitForSelector(`[data-testid="review-turn"][data-turn-id="${turnId}"][data-confirmed]`, { timeout: 10000 });
await check(true, "the patient confirms the current version");
await capture(shots, "review-corrected", [{ page: review, which: "review", widths: [1024, 390], height: 1366 }]);

// ---------- refusals reach only the review connection ----------
const phone = await socket(base, serverPort, "review");
phone.send("segment.confirm", { segmentId: turnId, version: "original" });
const refused = (await phone.next("command.refused")).payload;
await check(refused.command === "segment.confirm" && refused.reason === "not_current", "an old version is refused as not_current");
await check(!(await phone.arrives("error", 800)), "a review connection never receives error");
probe.send("segment.amend", { segmentId: turnId, text: CORRECTED, language: "pa-IN", recognitionConfidence: 1 });
await check(!(await phone.arrives("segment.status", 1200)), "a controller's correction is not run");

// ---------- nothing private on the public screens ----------
for (const [who, frames] of [
  ["/screen", tvFrames],
  ["/review", reviewFrames],
]) {
  const wire = frames.join("\n");
  await check(!/"(emotion|certainty|backTranslation|injection|injectedTurnIds|tamper|analysis)"/.test(wire), `${who} receives no private fields`);
  await check(!wire.includes('"segment.analysis"') && !wire.includes('"demo.injection_state"'), `${who} receives no controller-only events`);
}

probe.ws.close();
phone.ws.close();
await browser.close();
console.log("PASS: review corrections, consent by the patient, and the injected turn on the review screen");
