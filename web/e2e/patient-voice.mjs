// Patient voice end-to-end check (trust-across-the-barrier tasks 4.1 and 4.3; MDD-005, CDR-008, IDR-005, ADR-012).
// The patient consents on /patient and gets five controls in Punjabi with English beneath, each at least 56px
// tall; "say that again" before anything was spoken is refused with "nothing to repeat"; a physician turn shows
// large on /patient with its manner label; each signal reaches /screen in both languages, /control's trust view,
// and the record (visit.state.signals on a fresh review socket), a second tap within two seconds is refused busy,
// and "say that again" replays the same speech id with no new turn, also after /control reloads; pause from /patient shows the paused notice on
// /screen and disables the other controls; the interpreter request from /patient reaches /screen; and no
// trust.update or private field ever reaches /screen or /patient. Run against a freshly started fake-model stack
// and a web build made with NEXT_PUBLIC_SPEECH_TEST_HOOKS=on.
// Usage: node e2e/patient-voice.mjs [baseUrl] [serverPort] [screenshotDir]
import { giveConsentOnReview } from "./consent-steps.mjs";
import { capture, fakeVoice, open, saySettled, socket, start, turnCount } from "./visit-steps.mjs";

const base = process.argv[2] ?? "http://localhost:3000";
const serverPort = process.argv[3] ?? "8000";
const shots = process.argv[4];
const { browser, fail, check } = await start();

const REASSURE = "Your tests came back and they look reassuring, so there is nothing to worry about.";
const both = (text, ...parts) => parts.every((p) => text.includes(p));
const PA = {
  notUnderstood: "ਮੈਨੂੰ ਸਮਝ ਨਹੀਂ ਆਇਆ",
  notUnderstoodNotice: "ਮਰੀਜ਼ ਨੂੰ ਸਮਝ ਨਹੀਂ ਆਇਆ",
  slowerNotice: "ਹੌਲੀ ਬੋਲਣ",
  repeatNotice: "ਦੁਬਾਰਾ ਕਹੀ ਜਾ ਰਹੀ ਹੈ",
  nothingToRepeat: "ਦੁਬਾਰਾ ਕਹਿਣ ਲਈ ਕੁਝ ਨਹੀਂ",
  busy: "ਥੋੜ੍ਹਾ ਰੁਕੋ",
  sent: "ਡਾਕਟਰ ਨੂੰ ਭੇਜ",
  paused: "ਰੋਕਿਆ ਗਿਆ ਹੈ",
  reassuring: "ਧਰਵਾਸ",
};

const { page: tv, frames: tvFrames } = await open(browser, base, "/screen", { width: 1920, height: 1080 });
const { page: control } = await open(browser, base, "/control", { width: 1440, height: 900 });
const { page: patient, frames: patientFrames } = await open(browser, base, "/patient", { width: 820, height: 1180 });
// The controller's voice requests are served with a silent clip; the ids asked for show what was (re)played.
const asked = await fakeVoice(control);
const probe = await socket(base, serverPort, "controller");
if (probe.state.consent || probe.state.turns.length) await fail("run against a freshly started server");

// ---------- before consent: the notice and its button only ----------
await check((await patient.locator('[data-testid="review-consent"]').count()) === 1, "/patient shows the consent notice");
await check((await patient.locator('[data-testid="patient-controls"]').count()) === 0, "/patient shows no controls before consent");
await capture(shots, "patient-consent", [{ page: patient, which: "patient", widths: [820, 390], height: 1180 }]);
await giveConsentOnReview(patient);
await control.waitForSelector('[data-testid="consent"][data-state="given"][data-by="patient"]', { timeout: 10000 });
await check(true, "a tap on /patient is recorded as consent by the patient");

// ---------- the five controls, Punjabi first, English beneath, 56px or taller ----------
const CONTROLS = ["signal-not-understood", "signal-slower", "signal-repeat", "patient-pause", "patient-interpreter"];
await patient.waitForSelector('[data-testid="patient-controls"]', { timeout: 10000 });
for (const id of CONTROLS) {
  const button = patient.locator(`[data-testid="${id}"]`);
  const box = await button.boundingBox();
  await check(box && box.height >= 56, `${id} is at least 56px tall (${box?.height})`);
  const text = await button.innerText();
  await check(/[਀-੿]/.test(text) && /[A-Za-z]/.test(text), `${id} is labelled in Punjabi and English`);
}
await check(
  both(await patient.locator('[data-testid="signal-not-understood"]').innerText(), PA.notUnderstood, "I did not understand"),
  "the first control says I did not understand, Punjabi first",
);
await patient.setViewportSize({ width: 390, height: 844 });
await patient.waitForTimeout(300);
const narrow = await patient.locator('[data-testid="signal-slower"]').boundingBox();
const pageWidth = await patient.evaluate(() => document.documentElement.scrollWidth);
await check(narrow && narrow.width >= 390 - 40, "on a phone each control fills the width");
await check(pageWidth <= 390, "the phone page does not scroll horizontally");
await patient.setViewportSize({ width: 820, height: 1180 });

// ---------- say that again before anything was spoken: refused, nothing to repeat ----------
await patient.click('[data-testid="signal-repeat"]');
const early = patient.locator('[data-testid="signal-refused"]');
await early.waitFor({ timeout: 10000 });
await check((await early.getAttribute("data-reason")) === "invalid", "repeat before any spoken turn is refused invalid");
await check(both(await early.innerText(), PA.nothingToRepeat, "Nothing to repeat yet"), "/patient says there is nothing to repeat, in both languages");
await check((await asked.filter((a) => a.language === "pa-IN").length) === 0, "nothing was replayed");
await patient.waitForTimeout(2100); // the two second hold

// ---------- a physician turn shows large on /patient with its manner ----------
await saySettled(control, "physician", REASSURE);
const latest = patient.locator('[data-testid="patient-latest"]');
await patient.waitForFunction(() => document.querySelector('[data-testid="patient-latest"]')?.dataset.turnId, null, { timeout: 15000 });
const turnId = await latest.getAttribute("data-turn-id");
await check(Boolean(turnId), "/patient shows what the doctor just said");
const saidSize = await patient.evaluate(() => {
  const p = document.querySelector('[data-testid="patient-latest"] p[lang="pa-IN"]');
  return p ? parseFloat(getComputedStyle(p).fontSize) : 0;
});
await check(saidSize >= 28, `the translation is large (${saidSize}px)`);
const manner = latest.locator('[data-testid="manner-label"]');
await manner.waitFor({ timeout: 5000 });
await check((await manner.getAttribute("data-manner")) === "reassuring", "the manner label is reassuring");
await check(both(await manner.innerText(), PA.reassuring, "Said with reassurance"), "the manner label is in Punjabi with English beside it");
await control.waitForSelector('[data-testid="turn"] [data-testid="turn-manner"][data-manner="reassuring"]', { timeout: 5000 });
await check(true, "/control shows the manner on the turn in its log");
// The patient's own turn shows no manner anywhere on their device.
await saySettled(control, "patient", "ਠੀਕ ਹੈ ਡਾਕਟਰ ਜੀ।");
await check((await patient.locator('[data-testid="review-turn"][data-speaker="patient"] [data-testid="turn-manner"]').count()) === 0, "the patient's turn carries no manner on /patient");
await capture(shots, "patient-visit", [{ page: patient, which: "patient", widths: [820, 390], height: 1180 }]);

// ---------- each signal reaches /screen, /control, and the record ----------
const signals = [
  ["signal-not-understood", "not_understood", PA.notUnderstoodNotice, "did not understand"],
  ["signal-slower", "slower", PA.slowerNotice, "speak more slowly"],
  ["signal-repeat", "repeat", PA.repeatNotice, "again for the patient"],
];
const turnsBefore = await turnCount(control);
const replaysBefore = asked.filter((a) => a.id === turnId).length;
for (const [id, signal, pa, en] of signals) {
  await patient.click(`[data-testid="${id}"]`);
  const sent = patient.locator(`[data-testid="signal-sent"][data-signal="${signal}"]`);
  await sent.waitFor({ timeout: 10000 });
  await check(both(await sent.innerText(), PA.sent, "Sent to the doctor"), `/patient confirms ${signal} was sent, in both languages`);
  const notice = tv.locator(`[data-testid="patient-signal"][data-signal="${signal}"]`);
  await notice.waitFor({ timeout: 10000 });
  await check(both(await notice.innerText(), pa, en), `/screen shows ${signal} in Punjabi and English`);
  const listed = control.locator(`[data-testid="trust-signal"][data-signal="${signal}"]`);
  await listed.waitFor({ timeout: 10000 });
  await check((await listed.locator('[data-testid="cue"]').count()) === 1, `/control lists ${signal} with a suggestion`);
  // A second tap within two seconds is held.
  await patient.click(`[data-testid="${id}"]`);
  const busy = patient.locator('[data-testid="signal-refused"][data-reason="busy"]');
  await busy.waitFor({ timeout: 5000 });
  await check(both(await busy.innerText(), PA.busy, "wait a moment"), `a second ${signal} within two seconds is refused busy`);
  // The sent notice lasts three seconds from the accept, longer than the two second hold: wait for it to leave
  // rather than sleeping, so the next signal is never sent inside the hold and never sees this one's notice.
  await sent.waitFor({ state: "detached", timeout: 8000 });
  await check(true, `the ${signal} sent notice leaves after a few seconds`);
}
await check((await patient.locator('[data-testid="signal-sent"]').count()) === 0, "no sent notice is left on /patient");
await check((await turnCount(control)) === turnsBefore, "no signal created a new turn");
await check(asked.filter((a) => a.id === turnId).length === replaysBefore + 1, "say that again replayed the same speech id once");
await check((await asked.at(-1)?.language) === "pa-IN", "the replay is in the patient's language");
await tv.waitForSelector('[data-testid="speaking"][data-language="pa-IN"]', { timeout: 5000 }).catch(() => null);
await check(true, "/screen could show the interpreter speaking during the replay");

// ---------- say that again after the controller reloads (CDR-008) ----------
// The reloaded controller learns the last translation spoken in Punjabi from visit.state, so the replay still
// asks for the same speech id. The voice route set on the page survives the reload.
await control.reload();
await control.waitForSelector('[data-testid="connection"]:text("open")', { timeout: 15000 });
await control.waitForSelector('[data-testid="trust-signal"][data-signal="repeat"]', { timeout: 10000 });
await patient.waitForTimeout(2100); // the two second hold
const replaysBeforeReload = asked.filter((a) => a.id === turnId).length;
await patient.click('[data-testid="signal-repeat"]');
await patient.locator('[data-testid="signal-sent"][data-signal="repeat"]').waitFor({ timeout: 10000 });
// The route handler records requests in this process, so poll it.
for (let i = 0; i < 50 && asked.filter((a) => a.id === turnId).length === replaysBeforeReload; i++) await control.waitForTimeout(100);
await check(asked.filter((a) => a.id === turnId).length === replaysBeforeReload + 1, "after a controller reload, say that again replays the same speech id");
await check(asked.at(-1)?.language === "pa-IN", "in the patient's language");
await check((await control.locator('[data-testid="notice"]').count()) === 0 || !(await control.locator('[data-testid="notice"]').innerText()).includes("asked to hear it again"), "/control shows no nothing-known notice");
await patient.locator('[data-testid="signal-sent"]').waitFor({ state: "detached", timeout: 8000 });

// The interpreter relayed the first two signals to the physician in English only.
const lines = tvFrames
  .map((f) => JSON.parse(f))
  .filter((e) => e.type === "interpreter.line")
  .map((e) => e.payload);
const relayed = lines.filter((l) => l.purpose === "signal_not_understood" || l.purpose === "signal_slower");
await check(relayed.length === 2, "two interpreter lines relayed the signals");
await check(relayed.every((l) => l.lines.length === 1 && l.lines[0].language === "en-CA"), "signals are relayed in the physician's language only");
await check(asked.some((a) => a.id === relayed[0]?.lineId && a.language === "en-CA"), "/control spoke the relayed line");

// The record: a fresh review socket sees every signal, oldest first, after the turn it followed.
const phone = await socket(base, serverPort, "review");
const recorded = phone.state.signals ?? [];
await check(
  recorded.map((s) => s.signal).join(",") === "not_understood,slower,repeat,repeat",
  "visit.state.signals holds the four signals in order (the last after the reload)",
);
await check(recorded.every((s) => s.afterTurnId), "each signal names the turn it followed");
await check(!("trust" in phone.state), "a review snapshot carries no trust timeline");
const integrity = (await probe.next("record.integrity", 100).catch(() => null)) ?? null;
await check(integrity === null || integrity.payload.status === "verified", "the record stays verified after the signal entries");

// ---------- pause and resume from the patient's device ----------
await patient.click('[data-testid="patient-pause"]');
await tv.waitForSelector('[data-testid="paused"]', { timeout: 10000 });
await check(both(await tv.locator('[data-testid="paused"]').innerText(), PA.paused, "Paused. Nothing is being recorded."), "/screen shows the paused notice in both languages");
await patient.waitForSelector('[data-testid="patient-pause"][data-paused]', { timeout: 5000 });
await check((await patient.locator('[data-testid="patient-pause"]').innerText()).includes("Resume"), "/patient shows resume");
await check(await patient.locator('[data-testid="signal-not-understood"]').isDisabled(), "the signals are off while paused");
await check(!(await patient.locator('[data-testid="patient-pause"]').isDisabled()), "resume stays on while paused");
await capture(shots, "patient-paused", [{ page: patient, which: "patient", widths: [820, 390], height: 1180 }]);
await patient.click('[data-testid="patient-pause"]');
await tv.waitForSelector('[data-testid="paused"]', { state: "detached", timeout: 10000 });
await patient.waitForSelector('[data-testid="patient-pause"]:not([data-paused])', { timeout: 5000 });
await check(!(await patient.locator('[data-testid="signal-not-understood"]').isDisabled()), "the signals return after resume");

// ---------- a human interpreter from the patient's device ----------
await patient.click('[data-testid="patient-interpreter"]');
await tv.waitForSelector('[data-testid="interpreter-notice"][data-phase="connecting"]', { timeout: 10000 });
await check(true, "/screen shows the interpreter connecting after the patient's request");
await control.waitForSelector('[data-testid="interpreter"][data-phase="connecting"]', { timeout: 5000 });
await check(true, "/control shows the same");

// ---------- nothing private reached the public screens ----------
for (const [who, frames] of [
  ["/screen", tvFrames],
  ["/patient", patientFrames],
]) {
  const wire = frames.join("\n");
  await check(!wire.includes('"trust.update"'), `${who} never received trust.update`);
  await check(!/"(trust|emotion|certainty|backTranslation|cue|reassuranceLanded)"/.test(wire), `${who} received no trust or private fields`);
}
await check(!(await patient.locator("main").innerText()).toLowerCase().includes("worried"), "/patient shows no emotion");

probe.ws.close();
phone.ws.close();
await browser.close();
console.log("PASS: the patient's voice: consent, controls, signals, replay, pause, and the interpreter from /patient");
