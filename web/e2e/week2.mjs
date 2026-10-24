// Week 2 end-to-end check (tasks 2.4, 2.5, and 2.6): run against `scripts/dev.sh --prod` with
// TRANSLATOR=fake. Drives typed turns on /control and checks what /control and /screen show:
// tone labels and glossary explanations, empathy nudges on /control only, read-back confirm and
// reject, a blocked dose, and an escalated turn, with no private data ever reaching /screen.
// Usage: node e2e/week2.mjs [baseUrl] [screenshotDir]
import { chromium } from "playwright-core";

const base = process.argv[2] ?? "http://localhost:3000";
const shots = process.argv[3];
const DOSE = "Use the nitroglycerin spray: 0.4 milligrams, one spray under your tongue.";
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH ?? "/opt/pw-browsers/chromium" });

const fail = async (message) => {
  console.error(`FAIL: ${message}`);
  await browser.close();
  process.exit(1);
};
const check = async (condition, message) => (condition ? console.log(`ok: ${message}`) : fail(message));
const shot = async (page, name) => shots && page.screenshot({ path: `${shots}/${name}.png`, fullPage: true });

const tv = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const tvFrames = [];
tv.on("websocket", (ws) => ws.on("framereceived", (f) => tvFrames.push(String(f.payload))));
await tv.goto(`${base}/screen`);
await tv.waitForSelector('[data-testid="connection"][data-state="open"]', { timeout: 15000 });

const control = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
await control.goto(`${base}/control`);
await control.waitForSelector('[data-testid="connection"]:text("open")', { timeout: 15000 });

const say = async (speaker, text) => {
  await control.selectOption('[data-testid="typed-speaker"]', speaker);
  await control.fill('[data-testid="typed-text"]', text);
  await control.click('[data-testid="typed-send"]');
};
const lastCaption = () => tv.locator('[data-testid="caption"]').last();
const captionCount = () => tv.locator('[data-testid="caption"]').count();
const waitForCaption = async (before) => {
  await tv.waitForFunction((n) => document.querySelectorAll('[data-testid="caption"]').length > n, before, { timeout: 15000 });
  return lastCaption();
};

// 2.4: tone label and glossary explanation on a spoken caption.
let n = await captionCount();
await say("physician", "You did not have a heart attack.");
let caption = await waitForCaption(n);
await check((await caption.locator('[data-testid="tone-label"]').count()) === 1, "spoken caption carries one tone label");
await check((await caption.locator('[data-testid="tone-label"]').innerText()) === "reassuring", "reassurance is labelled reassuring");
await check((await caption.locator('[data-testid="glossary"]').innerText()).includes("ਦਿਲ ਦਾ ਦੌਰਾ"), "approved term explained beside the translation");

// 2.5: empathy nudge on /control only.
n = await captionCount();
await say("patient", "ਮੈਨੂੰ ਬਹੁਤ ਡਰ ਲੱਗਦਾ ਹੈ, I am scared about the cost.");
await waitForCaption(n);
await control.waitForSelector('[data-testid="nudge"]', { timeout: 15000 });
await check(true, "/control shows the empathy nudge");
await check((await tv.locator("text=Empathy nudge").count()) === 0, "/screen shows no nudge");
await shot(control, "control-nudge");

// 2.6: a matched dose waits for read-back; the screen shows the notice in both languages, not the translation.
await say("physician", DOSE);
await control.waitForSelector('[data-testid="readback"]', { timeout: 15000 });
await tv.waitForSelector('[data-testid="pending"][data-stage="awaiting_readback"]', { timeout: 15000 });
const pendingText = await tv.locator('[data-testid="pending"]').innerText();
await check(pendingText.includes("Checking the dose") && pendingText.includes("ਖ਼ੁਰਾਕ ਦੀ ਜਾਂਚ ਹੋ ਰਹੀ ਹੈ"), "screen shows checking the dose in both languages");
await check(!pendingText.includes("ਮਿਲੀਗ੍ਰਾਮ"), "screen shows no translation during read-back");
await shot(control, "control-readback");
await shot(tv, "screen-readback");

const late = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const lateFrames = [];
late.on("websocket", (ws) => ws.on("framereceived", (f) => lateFrames.push(String(f.payload))));
await late.goto(`${base}/screen`);
await late.waitForSelector('[data-testid="pending"][data-stage="awaiting_readback"]', { timeout: 15000 });
await check((await late.locator('[data-testid="pending"]').innerText()).includes("0.4 milligrams"), "screen opened mid read-back shows the original");
await shot(late, "screen-late-readback");
await late.close();

n = await captionCount();
await control.click('[data-testid="readback-confirm"]');
caption = await waitForCaption(n);
const marks = await caption.locator("mark").allInnerTexts();
await check(marks.includes("0.4 milligrams") && marks.includes("0.4 ਮਿਲੀਗ੍ਰਾਮ"), "confirmed dose highlighted in both languages");
await shot(tv, "screen-confirmed");

// Rejected read-back: discarded unspoken, the physician repeats.
await say("physician", DOSE);
await control.waitForSelector('[data-testid="readback"]', { timeout: 15000 });
await control.click('[data-testid="readback-reject"]');
await tv.waitForSelector('[data-testid="pending"][data-stage="discarded"] [data-testid="notice-pleaseRepeat"]', { timeout: 15000 });
await check((await control.locator('[data-testid="notice"]').innerText()).includes("say it again"), "rejected dose asks the physician to repeat");

// Blocked: the dose still changes after a retry.
n = await captionCount();
await say("physician", `${DOSE} (test: mismatch)`);
caption = await waitForCaption(n);
await check((await caption.getAttribute("data-status")) === "blocked", "mismatched dose is blocked");
const blockedText = await caption.innerText();
await check(blockedText.includes("Please repeat") && !blockedText.includes("ਮਿਲੀਗ੍ਰਾਮ"), "screen shows repeat notice and never the wrong dose");
await control.waitForSelector('[data-testid="turn"][data-status="blocked"] table', { timeout: 15000 });
await check(true, "/control shows the mismatched values");
await shot(control, "control-blocked");
await shot(tv, "screen-blocked");

// Escalated: tone check fails after a retry.
n = await captionCount();
await say("physician", "This is very unlikely to be serious. (test: tone)");
caption = await waitForCaption(n);
await check((await caption.getAttribute("data-status")) === "escalated", "failed tone check escalates");
await check((await caption.locator('[data-testid="notice-interpreterOffered"]').count()) === 1, "screen offers a human interpreter in both languages");
await check((await control.locator('[data-testid="notice"]').innerText()).includes("tone check failed"), "/control names the escalation reason");
await shot(control, "control-escalated");
await shot(tv, "screen-escalated");

const PRIVATE = /"turn\.analysis"|"turn\.readback_required"|"empathy\.nudge"|"emotion"|"backTranslation"|"certainty"|"nudges"/;
const leaked = [...tvFrames, ...lateFrames].filter((f) => PRIVATE.test(f));
if (leaked.length) await fail(`/screen received private data: ${leaked[0].slice(0, 200)}`);
await check(true, `/screen received ${tvFrames.length + lateFrames.length} frames, none private`);
const wrongDose = tvFrames.filter((f) => f.includes("[pa-IN]") && f.includes("(test: mismatch)") && f.includes('"translation":"'));
await check(wrongDose.length === 0, "the blocked translation never reached /screen");

await browser.close();
