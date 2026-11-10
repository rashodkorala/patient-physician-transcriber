// Explain-back end-to-end check (demo-night-mvp task 3.4, CDR-005, ADR-011; docs/demo-script.md beat 7). The
// physician gives a dose with its frequency, opens an explain-back, and the patient says the dose back without the
// frequency. /control shows the frequency as missed, decided by code; /screen and /review show only a prompt in
// both languages, never the outcome. Cancel closes an explain-back without a result. Run against a freshly
// started fake-model stack.
// Usage: node e2e/explain-back.mjs [baseUrl] [serverPort] [screenshotDir]
import { giveConsent } from "./consent-steps.mjs";
import { capture, open, sayConfirmed, saySettled, socket, start } from "./visit-steps.mjs";

const base = process.argv[2] ?? "http://localhost:3000";
const serverPort = process.argv[3] ?? "8000";
const shots = process.argv[4];
const { browser, fail, check } = await start();

const { page: tv, frames: tvFrames } = await open(browser, base, "/screen", { width: 1920, height: 1080 });
const { page: control } = await open(browser, base, "/control", { width: 1280, height: 1000 });
const { page: review, frames: reviewFrames } = await open(browser, base, "/review", { width: 1024, height: 1366 });
const probe = await socket(base, serverPort, "controller");
if (probe.state.turns.length) await fail("run against a freshly started server");
await giveConsent(control);

await check(await control.isDisabled('[data-testid="explainback-start"]'), "explain-back waits until the physician has spoken");
await sayConfirmed(control, "Take metformin 500 milligrams twice a day with food.");
await check(!(await control.isDisabled('[data-testid="explainback-start"]')), "explain-back can start once the plan is spoken");

// A cancelled explain-back leaves no result.
await control.click('[data-testid="explainback-start"]');
await control.waitForSelector('[data-testid="explainback"][data-state="listening"]', { timeout: 10000 });
await control.click('[data-testid="explainback-cancel"]');
await control.waitForSelector('[data-testid="explainback"][data-state="cancelled"]', { timeout: 10000 });
await check((await control.locator('[data-testid="explainback-result"]').count()) === 0, "cancel closes it with no result");

// ---------- the patient explains, leaving out the frequency ----------
await control.click('[data-testid="explainback-start"]');
await control.waitForSelector('[data-testid="explainback"][data-state="listening"]', { timeout: 10000 });
const prompt = tv.locator('[data-testid="explainback-prompt"][data-state="listening"]');
await prompt.waitFor({ timeout: 10000 });
const promptText = await prompt.innerText();
await check(promptText.includes("ਆਪਣੇ ਸ਼ਬਦਾਂ") && promptText.includes("in your own words"), "/screen prompts the patient in Punjabi and English");
await review.waitForSelector('[data-testid="review-explainback"][data-state="listening"]', { timeout: 10000 });
await check(true, "/review shows the same prompt");
await check(await control.isDisabled('[data-testid="explainback-check"]'), "check waits for the patient's explanation");
await saySettled(control, "patient", "ਮੈਂ metformin 500 milligrams ਲਵਾਂਗਾ।");
await control.waitForFunction(() => !document.querySelector('[data-testid="explainback-check"]')?.disabled, null, { timeout: 10000 });
await capture(shots, "explainback-listening", [
  { page: control, which: "control", widths: [1280, 390], height: 1000 },
  { page: tv, which: "screen", widths: [1920, 390], height: 1080, fullPage: false },
  { page: review, which: "review", widths: [1024, 390], height: 1366 },
]);
await control.click('[data-testid="explainback-check"]');
const result = control.locator('[data-testid="explainback-result"]');
await result.waitFor({ timeout: 20000 });
const frequency = result.locator('[data-testid="explainback-item"][data-kind="frequency"]');
await check((await frequency.getAttribute("data-outcome")) === "missed", "the missed frequency is flagged");
await check((await frequency.getAttribute("data-decided-by")) === "code", "the frequency was decided by code");
await check((await frequency.locator('[data-testid="decided-by"]').innerText()) === "checked by code", "/control says code decided it");
const dose = result.locator('[data-testid="explainback-item"][data-kind="dose"]');
await check((await dose.getAttribute("data-outcome")) === "matched", "the dose said back is matched");
await control.waitForSelector('[data-testid="explainback"][data-state="done"]', { timeout: 10000 });
await tv.waitForSelector('[data-testid="explainback-prompt"]', { state: "detached", timeout: 10000 });
await review.waitForSelector('[data-testid="review-explainback"]', { state: "detached", timeout: 10000 });
await check(true, "the prompt leaves /screen and /review when the check is done");
await capture(shots, "explainback-result", [{ page: control, which: "control", widths: [1280, 390], height: 1000 }]);

// ---------- the outcome never leaves the controller ----------
for (const [who, frames, page] of [
  ["/screen", tvFrames, tv],
  ["/review", reviewFrames, review],
]) {
  const wire = frames.join("\n");
  await check(!wire.includes('"explainback.result"') && !wire.includes('"explainBackResults"'), `${who} never receives the result`);
  await check(!/"(items|outcome|decidedBy|instruction)"/.test(wire), `${who} receives no items or outcomes`);
  const text = (await page.locator("main").innerText()).toLowerCase();
  await check(!text.includes("missed") && !text.includes("matched"), `${who} shows no outcome`);
}
const late = await socket(base, serverPort, "screen");
await check(late.state.explainBack?.state === "done" && !("explainBackResults" in late.state), "a late screen gets the state only");

late.ws.close();
probe.ws.close();
await browser.close();
console.log("PASS: explain-back");
