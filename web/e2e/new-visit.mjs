// New visit end-to-end check (CDR-001 `visit.new`, ADR-007). A visit with consent, two turns, and a patient signal;
// the physician presses "Start a new visit" on /control, cancels, presses again, and confirms. Every screen then
// starts afresh without a server restart: /screen has no captions and no signal and asks for consent, /patient
// shows the consent notice again, /control's turn log and trust view are empty with the saved physician name sent
// again, the latency rows are cleared, and the record badge is verified once the new visit records consent; a
// fresh review socket's visit.state has a new visitId and no turns. Run against a freshly started fake-model
// stack and a web build or dev server made with NEXT_PUBLIC_SPEECH_TEST_HOOKS=on.
// Usage: node e2e/new-visit.mjs [baseUrl] [serverPort] [screenshotDir]
import { giveConsentOnReview } from "./consent-steps.mjs";
import { capture, fakeVoice, open, saySettled, socket, start } from "./visit-steps.mjs";

const base = process.argv[2] ?? "http://localhost:3000";
const serverPort = process.argv[3] ?? "8000";
const shots = process.argv[4];
const { browser, fail, check } = await start();
const serverUrl = `http://${new URL(base).hostname}:${serverPort}`;

const visitId = async () => (await (await fetch(`${serverUrl}/api/health`)).json()).visitId;
/** The first visit.state envelope a new connection in this role receives. */
const firstState = (role) =>
  new Promise((resolve, reject) => {
    const ws = new WebSocket(`ws://${new URL(base).hostname}:${serverPort}/ws/visit?role=${role}`);
    ws.onmessage = (m) => {
      ws.close();
      resolve(JSON.parse(m.data));
    };
    ws.onerror = reject;
  });

const { page: tv } = await open(browser, base, "/screen", { width: 1920, height: 1080 });
const { page: control } = await open(browser, base, "/control", { width: 1440, height: 900 });
const { page: patient } = await open(browser, base, "/patient", { width: 820, height: 1180 });
await fakeVoice(control);
const probe = await socket(base, serverPort, "controller");
if (probe.state.consent || probe.state.turns.length) await fail("run against a freshly started server");
probe.ws.close();

// ---------- a visit: a saved physician name, consent, two turns, and a patient signal ----------
await control.fill('[data-testid="name-physician"]', "Dr Rao");
await control.press('[data-testid="name-physician"]', "Enter");
await control.check('[data-testid="name-default"]');
await giveConsentOnReview(patient);
await control.waitForSelector('[data-testid="consent"][data-state="given"]', { timeout: 10000 });
await saySettled(control, "physician", "How long have you had the pain?");
await saySettled(control, "patient", "ਮੇਰੀ ਛਾਤੀ ਵਿੱਚ ਦਰਦ ਹੈ।");
await control.waitForSelector('[data-testid="trust-turn"]', { timeout: 15000 });
await tv.waitForFunction(() => document.querySelectorAll('[data-testid="caption"]').length === 2, null, { timeout: 15000 });
await patient.waitForSelector('[data-testid="patient-controls"]', { timeout: 10000 });
await patient.click('[data-testid="signal-not-understood"]');
await tv.waitForSelector('[data-testid="patient-signal"]', { timeout: 10000 });
await control.waitForSelector('[data-testid="trust-signal"]', { timeout: 10000 });
await check(
  (await control.locator('[data-testid="record-badge"]').getAttribute("data-status")) === "verified",
  "the visit's record is verified before the new visit",
);
const csv = control.getByRole("button", { name: "Download CSV" });
await check(await csv.isEnabled(), "/control has latency rows to download");
const before = await visitId();

// ---------- the button asks first, and cancelling keeps the visit ----------
await check(await control.isEnabled('[data-testid="new-visit"]'), "Start a new visit is enabled with no turn in the graph");
await control.click('[data-testid="new-visit"]');
const warning = control.getByText("This clears the current visit on every screen. The record is not kept.");
await warning.waitFor({ timeout: 5000 });
await check(true, "the first press shows the inline confirm with its warning");
await check(
  (await control.locator('[data-testid="new-visit-confirm"]').innerText()) === "Start new visit" &&
    (await control.locator('[data-testid="new-visit-cancel"]').innerText()) === "Keep this visit",
  "the confirm offers Start new visit and Keep this visit",
);
await capture(shots, "new-visit-confirm", [{ page: control, which: "control", widths: [1440, 390], height: 900 }]);
await control.click('[data-testid="new-visit-cancel"]');
await control.waitForSelector('[data-testid="new-visit-confirm"]', { state: "detached", timeout: 5000 });
await check((await visitId()) === before, "Keep this visit leaves the visit as it was");
await check((await control.locator('[data-testid="turn"]').count()) === 2, "/control still has both turns");

// ---------- confirmed: every screen starts afresh ----------
await control.click('[data-testid="new-visit"]');
await control.click('[data-testid="new-visit-confirm"]');
await control.waitForSelector('[data-testid="notice"]:text("New visit started")', { timeout: 10000 });
await check(true, "/control says New visit started");
const after = await visitId();
await check(after !== before, "the health endpoint reports a new visitId");

await control.waitForFunction(() => document.querySelectorAll('[data-testid="turn"]').length === 0, null, { timeout: 10000 });
await check(true, "/control's turn log is empty");
await check(
  (await control.locator('[data-testid="trust-turn"], [data-testid="trust-signal"]').count()) === 0,
  "/control's trust view is empty",
);
await check(await csv.isDisabled(), "/control's latency rows are cleared");
await check(
  (await control.locator('[data-testid="consent"]').getAttribute("data-state")) === "none",
  "/control asks for consent again",
);
await control.waitForFunction(
  () => document.querySelector('[data-testid="name-physician"]')?.value === "Dr Rao",
  null,
  { timeout: 10000 },
);
await check(true, "/control keeps the saved physician name for the new visit");

await tv.waitForFunction(() => document.querySelectorAll('[data-testid="caption"]').length === 0, null, { timeout: 10000 });
await check(true, "/screen has no captions");
await check((await tv.locator('[data-testid="patient-signal"]').count()) === 0, "/screen shows no signal");
await check((await tv.locator('[data-testid="consent-notice"]').count()) === 1, "/screen shows the consent notice again");

await patient.waitForSelector('[data-testid="review-consent"]', { timeout: 10000 });
await check(true, "/patient shows the consent notice again");
await check((await patient.locator('[data-testid="patient-controls"]').count()) === 0, "/patient shows no controls");
await check((await patient.locator('[data-testid="signal-sent"]').count()) === 0, "/patient shows no signal feedback");

const fresh = await firstState("review");
await check(fresh.visitId === after && fresh.visitId !== before, "a fresh review socket's visit.state has the new visitId");
await check(fresh.payload.turns.length === 0 && fresh.payload.signals.length === 0, "and no turns or signals");
await check(fresh.payload.integrity.status === "verified" && fresh.payload.integrity.headHash === "", "and an empty, verified record");
await check(fresh.payload.physicianName === "Dr Rao", "the saved physician name was sent again for the new visit");
await capture(shots, "new-visit-after", [
  { page: control, which: "control", widths: [1440, 390], height: 900 },
  { page: tv, which: "screen", widths: [1920], height: 1080, fullPage: false },
  { page: patient, which: "patient", widths: [820, 390], height: 1180 },
]);

// ---------- the new visit works: consent, then the ready state and a verified record ----------
await giveConsentOnReview(patient);
await tv.waitForSelector('[data-testid="ready"]', { timeout: 10000 });
await check(true, "/screen shows the ready state with no captions and no signal");
await control.waitForSelector('[data-testid="record-badge"][data-status="verified"]', { timeout: 10000 });
await check(true, "/control's record badge is verified for the new visit");
await check((await tv.locator('[data-testid="record-badge"]').getAttribute("data-status")) === "verified", "/screen's record badge is verified");
await saySettled(control, "physician", "Hello again.");
await check((await control.locator('[data-testid="turn"]').count()) === 1, "the new visit's first turn is its only turn");

await browser.close();
console.log("new visit: all checks passed");
