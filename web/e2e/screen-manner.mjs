// Room screen manner label and patient signal check (trust-across-the-barrier task 3.2; IDR-005, CDR-008, ADR-012).
// A raw controller socket submits a physician turn whose words carry reassurance: /screen must show the manner
// label on that caption in Punjabi and in English, and none on a patient caption. A raw review socket (the
// patient's device) then sends a signal: /screen must show the notice in both languages, a screen joining within
// a few seconds must still show it, and it must leave after about eight seconds. Run against a freshly started
// fake-model stack (TRANSLATOR=fake) whose model reads manner from the words.
// Usage: node e2e/screen-manner.mjs [baseUrl] [serverPort] [screenshotDir]
import { readFileSync } from "node:fs";
import { giveConsentOnSocket } from "./consent-steps.mjs";
import { open, socket, start } from "./visit-steps.mjs";

const base = process.argv[2] ?? "http://localhost:3000";
const serverPort = process.argv[3] ?? "8000";
const shots = process.argv[4];
const { browser, fail, check } = await start();
const shot = async (page, name) => shots && page.screenshot({ path: `${shots}/${name}.png`, fullPage: true });

const pa = JSON.parse(readFileSync(new URL("../i18n/pa.json", import.meta.url), "utf8"));
const en = JSON.parse(readFileSync(new URL("../i18n/en.json", import.meta.url), "utf8"));

const { page: tv } = await open(browser, base, "/screen", { width: 1920, height: 1080 });
const ctl = await socket(base, serverPort, "controller");
if (ctl.state.patientLanguage !== "pa-IN") await fail("run against a freshly started server with Punjabi as the patient language");
await giveConsentOnSocket(ctl, ctl.state);

const captionOn = (turnId) => tv.locator(`[data-testid="caption"][data-turn-id="${turnId}"]`);

// IDR-005: a reassuring physician turn carries its label beneath the translation, Punjabi first, English beside.
ctl.send("turn.submit", {
  speaker: "physician",
  language: "en-CA",
  text: "The tests were reassuring. You did not have a heart attack.",
  recognitionConfidence: 0.95,
});
const reassuring = (await ctl.next("turn.result")).payload;
await check(reassuring.manner === "reassuring", `the caption carries manner reassuring (got ${reassuring.manner})`);
await captionOn(reassuring.turnId).waitFor({ timeout: 15000 });
const label = captionOn(reassuring.turnId).locator('[data-testid="manner-label"]');
await check((await label.count()) === 1, "/screen shows one manner label on the reassuring physician caption");
await check((await label.getAttribute("data-manner")) === "reassuring", "the label names the manner");
const labelText = await label.innerText();
await check(labelText.includes(pa.mannerReassuring), "the label is in Punjabi");
await check(labelText.includes(en.mannerReassuring), "the English label sits beside it");
await check(
  (await label.locator(`[lang="pa-IN"]`).count()) === 1 && (await label.locator(`[lang="en-CA"]`).count()) === 1,
  "each half of the label is marked with its language",
);
await shot(tv, "screen-manner-reassuring");

// A plain physician turn shows no label.
ctl.send("turn.submit", {
  speaker: "physician",
  language: "en-CA",
  text: "How long have you had the pain?",
  recognitionConfidence: 0.95,
});
const plain = (await ctl.next("turn.result")).payload;
await captionOn(plain.turnId).waitFor({ timeout: 15000 });
await check((await captionOn(plain.turnId).locator('[data-testid="manner-label"]').count()) === 0, "a plain physician turn has no label");

// A patient turn never carries a manner or an emotion label, whatever the words.
ctl.send("turn.submit", {
  speaker: "patient",
  language: "pa-IN",
  text: "ਮੈਨੂੰ ਬਹੁਤ ਡਰ ਲੱਗਦਾ ਹੈ।",
  recognitionConfidence: 0.95,
});
const patient = (await ctl.next("turn.result")).payload;
await check(patient.manner == null, "a patient caption carries no manner on the wire");
await captionOn(patient.turnId).waitFor({ timeout: 15000 });
await check((await captionOn(patient.turnId).locator('[data-testid="manner-label"]').count()) === 0, "a patient caption shows no manner label");
await check(!(await captionOn(patient.turnId).innerText()).match(/worried|calm|scared/i), "a patient caption shows no emotion");

// CDR-008: the patient signals from their device; the room sees it in both languages for a few seconds.
const device = await socket(base, serverPort, "review");
device.send("patient.signal", { signal: "slower" });
const signalled = await ctl.next("patient.signal");
await check(signalled.payload.signal === "slower", "every role receives the signal");
const notice = tv.locator('[data-testid="patient-signal"][data-signal="slower"]');
await notice.waitFor({ timeout: 5000 });
const noticeText = await notice.innerText();
await check(noticeText.includes(pa.signalSlowerNotice) && noticeText.includes(en.signalSlowerNotice), "/screen shows the signal in Punjabi and English");
await shot(tv, "screen-signal-slower");

const late = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await late.goto(`${base}/screen`);
await late.waitForSelector('[data-testid="patient-signal"][data-signal="slower"]', { timeout: 5000 });
await check(true, "a screen joining within a few seconds still shows the signal");

await notice.waitFor({ state: "detached", timeout: 10000 });
await late.waitForSelector('[data-testid="patient-signal"]', { state: "detached", timeout: 10000 });
await check(true, "the signal leaves both screens after about eight seconds");
await late.close();

ctl.ws.close();
device.ws.close();
await browser.close();
