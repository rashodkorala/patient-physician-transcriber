// Trust view end-to-end check (trust-across-the-barrier task 4.2, affect-in-words task 4.3; MDD-005, CDR-008, IDR-005, IDR-006). A worried patient
// turn, a reassuring physician turn, and a calm patient turn mark reassurance as landed on /control; calm again
// and a new worry carry no mark (it resets once landed); after a new reassurance, still worried marks it as not
// yet landed;
// the worried turn's cue points to the empathy nudge; a physician question about alcohol shows a culture cue; a
// companion's typed turn is labelled Companion on /screen and in the turn log and produces no nudge; "Ask if anything is unclear" has the
// interpreter ask the patient in Punjabi with the English shown; and no trust data reaches /screen or /patient, live
// or in a late snapshot. Run against a freshly started fake-model stack.
// Usage: node e2e/trust-view.mjs [baseUrl] [serverPort] [screenshotDir]
import { giveConsent } from "./consent-steps.mjs";
import { capture, fakeVoice, open, saySettled, socket, start } from "./visit-steps.mjs";

const base = process.argv[2] ?? "http://localhost:3000";
const serverPort = process.argv[3] ?? "8000";
const shots = process.argv[4];
const { browser, fail, check } = await start();

const SCARED = "ਮੈਂ ਡਰਿਆ ਹੋਇਆ ਹਾਂ। (I am scared)";
const REASSURE = "Your tests were reassuring. This is unlikely to be anything serious.";
const CALM = "ਠੀਕ ਹੈ, ਧੰਨਵਾਦ ਡਾਕਟਰ ਜੀ।";
const WORRIED_AGAIN = "ਮੈਨੂੰ ਅਜੇ ਵੀ ਫ਼ਿਕਰ ਹੈ।";
const ALCOHOL = "How much alcohol do you drink in a week?";
const EVERYDAY = "How long have the symptoms lasted?";
const COMPANION = "ਮੇਰੀ ਮਾਂ ਰਾਤ ਨੂੰ ਠੀਕ ਨਹੀਂ ਸੌਂਦੀ।";
const both = (text, ...parts) => parts.every((p) => text.includes(p));

const { page: tv, frames: tvFrames } = await open(browser, base, "/screen", { width: 1920, height: 1080 });
const { page: control } = await open(browser, base, "/control", { width: 1440, height: 900 });
const { page: patient, frames: patientFrames } = await open(browser, base, "/patient", { width: 820, height: 1180 });
const asked = await fakeVoice(control);
const probe = await socket(base, serverPort, "controller");
if (probe.state.consent || probe.state.turns.length) await fail("run against a freshly started server");
await giveConsent(control);

const trust = control.locator('[data-testid="trust"]');
await check((await trust.count()) === 1, "/control has a trust view");
await check((await trust.locator('[data-testid="trust-turn"]').count()) === 0, "the trust view starts empty");
await check(await control.locator('[data-testid="ask-if-clear"]').isEnabled(), "the closing check is available once consent is given");

// ---------- worry, reassurance, calm: landed ----------
await saySettled(control, "patient", SCARED);
const worried = trust.locator('[data-testid="trust-turn"][data-speaker="patient"]').first();
await worried.waitFor({ timeout: 15000 });
await check((await worried.getAttribute("data-emotion")) === "worried", "the trust view reads the patient as worried");
await check((await worried.innerText()).includes("sounds worried"), "in plain words");
await check((await worried.locator('[data-testid="landed"]').count()) === 0, "no landed mark before any reassurance");
const nudgeCue = worried.locator('[data-testid="cue"][data-kind="reassurance"]');
await nudgeCue.waitFor({ timeout: 15000 });
await check((await nudgeCue.innerText()).trim() === "Empathy nudge shown", "the worried turn points to the empathy nudge instead of repeating it");

await saySettled(control, "physician", REASSURE);
const reassuring = trust.locator('[data-testid="trust-turn"][data-speaker="physician"]').first();
await reassuring.waitFor({ timeout: 15000 });
await check((await reassuring.getAttribute("data-manner")) === "reassuring", "the physician's turn carries its manner");
await check((await reassuring.innerText()).includes("said with reassurance"), "shown as said with reassurance");
await check((await trust.locator('[data-testid="cue"][data-kind="culture"]').count()) === 0, "a reassuring turn shows no culture cue");

await saySettled(control, "patient", CALM);
const landed = trust.locator('[data-testid="landed"]').first();
await landed.waitFor({ timeout: 15000 });
await check((await landed.getAttribute("data-landed")) === "true", "a calm turn after reassurance is marked landed");
await check((await landed.innerText()).includes("Reassurance landed"), "in words");
await capture(shots, "trust-landed", [{ page: control, which: "control", widths: [1440], height: 900 }]);

// ---------- landed resets: calm or worried again has no mark; a new reassurance, then still worried: not yet ----------
const patientTrustTurns = (n) =>
  control.waitForFunction((count) => document.querySelectorAll('[data-testid="trust-turn"][data-speaker="patient"]').length >= count, n, { timeout: 15000 });
await saySettled(control, "patient", CALM);
await patientTrustTurns(3);
await check((await trust.locator('[data-testid="landed"]').count()) === 1, "a calm turn after reassurance has landed carries no new mark");
await saySettled(control, "patient", WORRIED_AGAIN);
await patientTrustTurns(4);
await check((await trust.locator('[data-testid="landed"]').count()) === 1, "a new worry with no new reassurance carries no mark");
await saySettled(control, "physician", REASSURE);
await control.waitForFunction(() => document.querySelectorAll('[data-testid="trust-turn"][data-speaker="physician"]').length >= 2, null, { timeout: 15000 });
await saySettled(control, "patient", WORRIED_AGAIN);
await control.waitForFunction(() => document.querySelectorAll('[data-testid="landed"]').length >= 2, null, { timeout: 15000 });
const notYet = trust.locator('[data-testid="landed"]').nth(1);
await check((await notYet.getAttribute("data-landed")) === "false", "a worried turn after reassurance is marked not yet landed");
await check((await notYet.innerText()).includes("Still worried"), "in words");

// ---------- a sensitive question: a culture cue; an everyday one: none ----------
await saySettled(control, "physician", ALCOHOL);
const cue = trust.locator('[data-testid="cue"][data-kind="culture"]');
await cue.waitFor({ timeout: 15000 });
await check((await cue.innerText()).toLowerCase().includes("shame"), "the alcohol question shows a culture cue about shame");
const cuesBefore = await cue.count();
await saySettled(control, "physician", EVERYDAY);
await control.waitForSelector('[data-testid="trust-turn"][data-speaker="physician"]:nth-of-type(n)', { timeout: 15000 });
await control.waitForTimeout(1500);
await check((await cue.count()) === cuesBefore, "an everyday question shows no cue");
await check(!(await tv.locator("main").innerText()).toLowerCase().includes("shame"), "/screen shows no cue");

// ---------- a companion speaks ----------
const nudgesBefore = await control.locator('[data-testid="nudge"]').count();
await check((await control.locator('[data-testid="speak-companion"]').count()) === 1, "/control has a companion push-to-talk control");
await saySettled(control, "companion", COMPANION);
// The screen keeps only the latest captions, so the companion's turn is a new last caption, not a higher count.
await tv.waitForSelector('[data-testid="caption"][data-speaker="companion"]', { timeout: 15000 });
const companionCaption = tv.locator('[data-testid="caption"]').last();
await check((await companionCaption.getAttribute("data-speaker")) === "companion", "the companion's turn is the latest caption on /screen");
await check((await companionCaption.innerText()).includes("Companion"), "/screen labels the companion's turn Companion");
const companionTurn = control.locator('[data-testid="turn"]').last();
await check((await companionTurn.innerText()).toLowerCase().includes("companion"), "the turn log labels it companion");
await check((await control.locator('[data-testid="nudge"]').count()) === nudgesBefore, "a companion turn produces no nudge");
await patient.waitForSelector('[data-testid="review-turn"][data-speaker="companion"]', { timeout: 15000 });
const companionOnPatient = patient.locator('[data-testid="review-turn"][data-speaker="companion"]').last();
await check(both(await companionOnPatient.innerText(), "ਸਾਥੀ", "Your companion"), "/patient labels the companion in Punjabi and English");
const companionTrust = trust.locator('[data-testid="trust-turn"][data-speaker="companion"]');
await companionTrust.first().waitFor({ timeout: 15000 });
await check((await companionTrust.first().locator('[data-testid="landed"]').count()) === 0, "a companion turn carries no landed mark");

// A companion turn in the physician's language is refused.
const before = tvFrames.length;
probe.send("turn.submit", { speaker: "companion", language: "en-CA", text: "She does not sleep well.", recognitionConfidence: 1 });
const refusal = await probe.next("error", 10000).catch(() => null);
await check(refusal !== null, "a companion turn in English is refused");
await check(!tvFrames.slice(before).some((f) => f.includes("She does not sleep well")), "/screen never saw the refused turn");

// ---------- the closing check ----------
await control.click('[data-testid="ask-if-clear"]');
const line = tv.locator('[data-testid="interpreter-line"][data-purpose="ask_if_clear"]');
await line.waitFor({ timeout: 10000 });
const lineText = await line.innerText();
await check(/[਀-੿]/.test(lineText) && lineText.includes("explained again"), "/screen shows the closing check in Punjabi and English");
const closing = tvFrames.map((f) => JSON.parse(f)).find((e) => e.type === "interpreter.line" && e.payload.purpose === "ask_if_clear")?.payload;
await check(closing && closing.lines[0].language === "pa-IN" && closing.lines[1].language === "en-CA", "the patient's language comes first, English second");
await control.waitForFunction((id) => window.__asked?.some?.((a) => a.id === id) ?? true, closing?.lineId, { timeout: 100 }).catch(() => null);
await control.waitForTimeout(500);
await check(asked.some((a) => a.id === closing?.lineId && a.language === "pa-IN"), "/control speaks the closing check in Punjabi");
await check(!asked.some((a) => a.id === closing?.lineId && a.language === "en-CA"), "and not in English");
await check((await control.locator('[data-testid="notice"]').innerText()).includes("explained again"), "/control shows the English to the physician");
await capture(shots, "trust-closing", [{ page: control, which: "control", widths: [1440], height: 900 }, { page: tv, which: "screen", widths: [1920], height: 1080, fullPage: false }]);

// ---------- no trust data reaches the public screens, live or late ----------
const late = await socket(base, serverPort, "screen");
for (const [who, wire] of [
  ["/screen", tvFrames.join("\n")],
  ["/patient", patientFrames.join("\n")],
  ["a late screen snapshot", JSON.stringify(late.state)],
]) {
  await check(!wire.includes("trust.update") && !/"(trust|reassuranceLanded|cue|emotion)"/.test(wire), `${who} carries no trust data`);
}
await check(!("trust" in late.state) && Array.isArray(late.state.signals), "a late snapshot has signals but no trust");
// IDR-006: a worried patient's translation carries "sounding worried" in its frame, as spoken; past that, neither
// screen names an emotion (no "sounds worried", no "Still worried", no label).
const withoutPhrase = async (page) => (await page.locator("main").innerText()).toLowerCase().replaceAll("sounding worried", "");
await check((await tv.locator("main").innerText()).includes("sounding worried"), "/screen shows the affect phrase inside a translation");
await check(
  !(await withoutPhrase(patient)).includes("worried") && !(await withoutPhrase(tv)).includes("worried"),
  "/screen and /patient show no emotion label",
);
await check((await tv.locator("[data-emotion]").count()) === 0 && (await patient.locator("[data-emotion]").count()) === 0, "and no emotion attribute");

probe.ws.close();
late.ws.close();
await browser.close();
console.log("PASS: the trust view: landed, not yet, a culture cue, a companion turn, and the closing check");
