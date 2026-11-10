// Refused patient summary end-to-end check (demo-night-mvp task 3.7, CDR-007, ADR-011). A summary the value check
// cannot pass is refused: /control shows why, while /screen and /review say only, in both languages, that it is
// not ready, and nothing of it is published, chained, or spoken. With the fake model every summary in Punjabi,
// French, or Tamil passes, so this uses Sinhala, whose numbers and units the checker does not know (TDM-003):
// run against a freshly started fake-model stack started with TEST_LANGUAGES=on.
// Usage: node e2e/summary-refused.mjs [baseUrl] [serverPort] [screenshotDir]
import { chooseLanguage, giveConsent } from "./consent-steps.mjs";
import { capture, open, saySettled, socket, start } from "./visit-steps.mjs";

const base = process.argv[2] ?? "http://localhost:3000";
const serverPort = process.argv[3] ?? "8000";
const shots = process.argv[4];
const { browser, fail, check } = await start();

const { page: tv, frames: tvFrames } = await open(browser, base, "/screen", { width: 1920, height: 1080 });
const { page: control } = await open(browser, base, "/control", { width: 1280, height: 1000 });
const { page: review, frames: reviewFrames } = await open(browser, base, "/review", { width: 1024, height: 1366 });
const probe = await socket(base, serverPort, "controller");
if (probe.state.turns.length) await fail("run against a freshly started server");
await control.waitForSelector('[data-testid="test-mode-banner"]', { timeout: 10000 }).catch(() => fail("start the server with TEST_LANGUAGES=on"));
await chooseLanguage(control, "si-LK");
await giveConsent(control);
await saySettled(control, "patient", "මට සති දෙකක සිට පපුවේ තදයක් දැනෙනවා.");
await saySettled(control, "physician", "Thank you. Let us find out what is causing it.");

await control.click('[data-testid="summary-generate"]');
await control.waitForSelector('[data-testid="summary-refusal"]', { timeout: 30000 });
await check(
  (await control.locator('[data-testid="summary-row-state"]').innerText()).startsWith("Refused"),
  "/control shows the summary as refused",
);
await check(
  (await control.locator('[data-testid="summary-refusal-detail"]').innerText()).includes("si-LK"),
  "/control shows why it was refused",
);
await review.waitForSelector('[data-testid="summary-refused"]', { timeout: 10000 });
const reviewText = await review.locator('[data-testid="summary-refused"]').innerText();
await check(reviewText.includes("It is not ready yet") && reviewText.includes("සූදානම් නැත"), "/review says only that it is not ready, in Sinhala and English");
await tv.waitForSelector('[data-testid="summary"][data-state="refused"]', { timeout: 10000 });
await check(true, "/screen says the same, in both languages");
await check((await review.locator('[data-testid="summary-listen"]').count()) === 0, "a refused summary cannot be played");
for (const [who, frames] of [
  ["/screen", tvFrames],
  ["/review", reviewFrames],
]) {
  const wire = frames.join("\n");
  await check(!wire.includes('"summary.check"') && !wire.includes('"summary.ready"') && !wire.includes('"detail":"'), `${who} never learns why or sees any text`);
}
await capture(shots, "summary-refused", [
  { page: control, which: "control", widths: [1280, 390], height: 1000 },
  { page: review, which: "review", widths: [1024, 390], height: 1366 },
  { page: tv, which: "screen", widths: [1920], height: 1080, fullPage: false },
]);

probe.ws.close();
await browser.close();
console.log("PASS: a refused summary is shown to the controller only");
