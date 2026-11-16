// Room screen manner label, affect phrase, and patient signal check (trust-across-the-barrier task 3.2,
// affect-in-words task 4.1; IDR-005, IDR-006, CDR-008, ADR-012).
// A raw controller socket submits a physician turn whose words carry reassurance: /screen must show the manner
// label on that caption in Punjabi and in English, and none on a patient caption. A worried patient caption shows
// no label either, and its translation carries exactly one hedged affect phrase in its opening frame; a plain
// patient caption carries none. A raw review socket (the
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

// IDR-006: a patient turn never carries a manner or an emotion label, whatever the words. A worried one carries its
// affect in words instead: exactly one hedged phrase, inside the opening frame of the translation, and nowhere else.
const AFFECT = /sounding (worried|embarrassed|as if in pain|relieved|confused)/g;
const translationOn = (turnId) => captionOn(turnId).locator(`div[lang="en-CA"] p`).first();
ctl.send("turn.submit", {
  speaker: "patient",
  language: "pa-IN",
  text: "ਮੈਨੂੰ ਬਹੁਤ ਡਰ ਲੱਗਦਾ ਹੈ।",
  recognitionConfidence: 0.95,
});
const patient = (await ctl.next("turn.result")).payload;
await check(patient.manner == null && !("emotion" in patient), "a patient caption carries no manner or emotion on the wire");
await check((patient.translation.match(AFFECT) ?? []).length === 1, `the translation carries exactly one affect phrase (got ${patient.translation})`);
await check(
  patient.translation.startsWith("[en-CA] The patient says, sounding worried, "),
  "the phrase sits inside the opening frame, before the patient's words",
);
await captionOn(patient.turnId).waitFor({ timeout: 15000 });
await check((await captionOn(patient.turnId).locator('[data-testid="manner-label"]').count()) === 0, "a patient caption shows no manner label");
const shown = await translationOn(patient.turnId).innerText();
await check(shown === patient.translation, "/screen shows the translation as spoken, phrase included");
const outsideTranslation = (await captionOn(patient.turnId).innerText()).replace(shown, "");
await check(!outsideTranslation.match(/worried|calm|scared/i), "nothing outside the translation names an emotion");
await shot(tv, "screen-manner-worried-patient");

// A plain patient turn has no phrase and no frame.
ctl.send("turn.submit", { speaker: "patient", language: "pa-IN", text: "ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਡਾਕਟਰ ਜੀ।", recognitionConfidence: 0.95 });
const calm = (await ctl.next("turn.result")).payload;
await check(calm.translation === "[en-CA] ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਡਾਕਟਰ ਜੀ।", `a plain patient turn carries no affect phrase (got ${calm.translation})`);
await captionOn(calm.turnId).waitFor({ timeout: 15000 });
await check(!(await captionOn(calm.turnId).innerText()).match(AFFECT), "/screen shows no phrase on the plain patient turn");
await check((await captionOn(calm.turnId).locator('[data-testid="manner-label"]').count()) === 0, "and no manner label");

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
