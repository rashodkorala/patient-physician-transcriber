// Tamper control end-to-end check (demo-night-mvp tasks 3.8 and 5.2, CDR-006, IDR-003, TDM-005; docs/demo-script.md
// beat 9). The presenter opens the folded Presenter section on /control and alters one stored turn: the record
// badge turns red live on /control, /screen, and /review and names that turn; /control and /record mark the
// altered turn as changed by the tamper control; /screen and /review show only the broken badge and the turn,
// never a tamper label, live or after a reload. The control fires once per visit, and only from a controller.
// Run against a freshly started fake-model stack.
// Usage: node e2e/tamper.mjs [baseUrl] [serverPort] [screenshotDir]
import { giveConsent } from "./consent-steps.mjs";
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
await giveConsent(control);

await saySettled(control, "patient", "ਪੌੜੀਆਂ ਚੜ੍ਹਦਿਆਂ ਛਾਤੀ ਵਿੱਚ ਦਬਾਅ ਹੁੰਦਾ ਹੈ।");
await saySettled(control, "physician", "Thank you for telling me. Let us find out why.");
for (const page of [control, tv, review]) {
  await page.waitForSelector('[data-testid="record-badge"][data-status="verified"]', { timeout: 10000 });
}
await check(true, "the record is verified on /control, /screen, and /review");
const firstTurn = (await probe.next("turn.result")).payload.turnId;

// Screens and the review screen cannot fire it: their copies are dropped.
for (const role of ["screen", "review"]) {
  const other = await socket(base, serverPort, role);
  other.send("demo.tamper_record", { entryId: firstTurn });
  await check(!(await other.arrives("record.integrity", 1000)), `a ${role} connection's tamper command is dropped`);
  other.ws.close();
}
await check((await tv.locator('[data-testid="record-badge"]').getAttribute("data-status")) === "verified", "the record is still verified");

// ---------- the presenter alters turn 1 ----------
await control.click('[data-testid="presenter"] summary');
await control.selectOption('[data-testid="tamper-target"]', firstTurn);
await capture(shots, "tamper-ready", [{ page: control, which: "control", widths: [1280, 390], height: 1000 }]);
const fired = Date.now();
await control.click('[data-testid="tamper-fire"]');
await tv.waitForSelector('[data-testid="record-badge"][data-status="broken"]', { timeout: 5000 });
await check(Date.now() - fired < 3000, `the TV badge turns red live (${Date.now() - fired} ms)`);
for (const [who, page] of [
  ["/control", control],
  ["/screen", tv],
  ["/review", review],
]) {
  const badge = page.locator('[data-testid="record-badge"][data-status="broken"]');
  await badge.waitFor({ timeout: 5000 });
  await check((await badge.getAttribute("data-broken-at")) === firstTurn, `${who} names the altered entry`);
  await check((await badge.innerText()).toLowerCase().includes("turn 1"), `${who}'s badge says turn 1`);
}
await check(
  (await tv.locator(`[data-testid="caption"][data-turn-id="${firstTurn}"] [data-testid="record-broken-here"]`).count()) === 1,
  "/screen marks the altered turn",
);
await check(
  (await review.locator(`[data-testid="review-turn"][data-turn-id="${firstTurn}"] [data-testid="record-broken-here"]`).count()) === 1,
  "/review marks the altered turn",
);
await control.waitForSelector('[data-testid="turn"][data-tampered] [data-testid="tampered"]', { timeout: 5000 });
await control.waitForSelector('[data-testid="tamper"][data-state="fired"]', { timeout: 5000 });
await check(true, "/control marks the turn as altered by the tamper control, and the control is spent");

const { page: record } = await open(browser, base, "/record", { width: 1280, height: 1000 });
await record.waitForSelector(`[data-testid="source-turn"][data-turn-id="${firstTurn}"][data-tampered]`, { timeout: 10000 });
await check(true, "/record marks the altered turn after a reload");
await capture(shots, "tamper-fired", [
  { page: control, which: "control", widths: [1280, 390], height: 1000 },
  { page: tv, which: "screen", widths: [1920, 390], height: 1080, fullPage: false },
  { page: review, which: "review", widths: [1024, 390], height: 1366 },
  { page: record, which: "record", widths: [1280, 390], height: 1000 },
]);

// ---------- once per visit ----------
probe.send("demo.tamper_record", { entryId: firstTurn });
const second = (await probe.next("error")).payload;
await check(second.command === "demo.tamper_record", "a second tamper in the visit is refused");

// ---------- no tamper label on the public screens, live or after a reload ----------
await tv.reload();
await tv.waitForSelector('[data-testid="record-badge"][data-status="broken"]', { timeout: 10000 });
await review.reload();
await review.waitForSelector('[data-testid="record-badge"][data-status="broken"]', { timeout: 10000 });
for (const [who, page, frames] of [
  ["/screen", tv, tvFrames],
  ["/review", review, reviewFrames],
]) {
  const text = (await page.locator("main").innerText()).toLowerCase();
  await check(!text.includes("tamper") && !text.includes("presenter") && !text.includes("altered"), `${who} shows no tamper label`);
  const wire = frames.join("\n");
  await check(!wire.includes('"demo.tamper_state"') && !wire.includes('"tamper"'), `${who} never receives tamper state`);
}

probe.ws.close();
await browser.close();
console.log("PASS: the tamper control and the live broken badge");
