// Week 2 end-to-end check (tasks 2.4, 2.5, and 2.6): run against `scripts/dev.sh --prod` with
// TRANSLATOR=fake. Drives typed turns on /control and checks what /control and /screen show:
// manner labels and glossary explanations, empathy nudges on /control only, read-back confirm and
// reject, a blocked dose, an escalated turn, and two unclear turns then a third that escalates (ADR-003), with no
// private data ever reaching /screen.
// Usage: node e2e/week2.mjs [baseUrl] [screenshotDir]
import { chromium } from "playwright-core";
import { giveConsent } from "./consent-steps.mjs";

// Only the visit channel; in dev mode pages also hold the Next.js hot-reload socket.
const visitChannel = (ws) => new URL(ws.url()).pathname === "/ws/visit";

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
tv.on("websocket", (ws) => visitChannel(ws) && ws.on("framereceived", (f) => tvFrames.push(String(f.payload))));
await tv.goto(`${base}/screen`);
await tv.waitForSelector('[data-testid="connection"][data-state="open"]', { timeout: 15000 });

const control = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
await control.goto(`${base}/control`);
await control.waitForSelector('[data-testid="connection"]:text("open")', { timeout: 15000 });
await giveConsent(control);

const say = async (speaker, text) => {
  await control.selectOption('[data-testid="typed-speaker"]', speaker);
  await control.fill('[data-testid="typed-text"]', text);
  await control.click('[data-testid="typed-send"]');
};
const lastCaption = () => tv.locator('[data-testid="caption"]').last();
// The screen keeps only the latest captions, so a new turn is a new last turn id, not a higher count.
const lastTurnId = () => tv.evaluate(() => [...document.querySelectorAll('[data-testid="caption"]')].at(-1)?.dataset.turnId ?? null);
const waitForCaption = async (before) => {
  await tv.waitForFunction(
    (id) => ([...document.querySelectorAll('[data-testid="caption"]')].at(-1)?.dataset.turnId ?? null) !== id,
    before,
    { timeout: 15000 },
  );
  return lastCaption();
};

// 2.4: manner label and glossary explanation on a spoken caption.
let n = await lastTurnId();
await say("physician", "You did not have a heart attack.");
let caption = await waitForCaption(n);
// IDR-005: the manner label replaced the tone-register pill; a reassuring physician turn carries it.
await check((await caption.locator('[data-testid="manner-label"]').count()) === 1, "spoken physician caption carries one manner label");
await check((await caption.locator('[data-testid="manner-label"]').getAttribute("data-manner")) === "reassuring", "reassurance is labelled reassuring");
await check((await caption.locator('[data-testid="tone-label"]').count()) === 0, "the old tone pill is gone");
await check((await caption.locator('[data-testid="glossary"]').innerText()).includes("ਦਿਲ ਦਾ ਦੌਰਾ"), "approved term explained beside the translation");

// 2.5: empathy nudge on /control only.
n = await lastTurnId();
await say("patient", "ਮੈਨੂੰ ਬਹੁਤ ਡਰ ਲੱਗਦਾ ਹੈ, I am scared about the cost.");
caption = await waitForCaption(n);
await check((await caption.locator('[data-testid="manner-label"]').count()) === 0, "a patient caption shows no manner label");
await check((await caption.locator('[data-testid="tone-label"]').count()) === 0, "a patient caption shows no tone label");
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
late.on("websocket", (ws) => visitChannel(ws) && ws.on("framereceived", (f) => lateFrames.push(String(f.payload))));
await late.goto(`${base}/screen`);
await late.waitForSelector('[data-testid="pending"][data-stage="awaiting_readback"]', { timeout: 15000 });
await check((await late.locator('[data-testid="pending"]').innerText()).includes("0.4 milligrams"), "screen opened mid read-back shows the original");
await shot(late, "screen-late-readback");
await late.close();

n = await lastTurnId();
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
n = await lastTurnId();
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
n = await lastTurnId();
await say("physician", "This is very unlikely to be serious. (test: tone)");
caption = await waitForCaption(n);
await check((await caption.getAttribute("data-status")) === "escalated", "failed tone check escalates");
await check((await caption.locator('[data-testid="notice-interpreterOffered"]').count()) === 1, "screen offers a human interpreter in both languages");
await check((await control.locator('[data-testid="notice"]').innerText()).includes("tone check failed"), "/control names the escalation reason");
await shot(control, "control-escalated");
await shot(tv, "screen-escalated");

// ADR-003: a turn not caught is unclear twice, never translated on the screen, and the interpreter asks again in
// the speaker's language; the same speaker's third in a row escalates with a human interpreter offered.
const UNCLEAR = "ਮੈਨੂੰ ਕੱਲ੍ਹ ਤੋਂ ਚੱਕਰ ਆ ਰਹੇ ਹਨ। (test: unclear)";
const ASK_AGAIN_PA = "ਇਹ ਗੱਲ ਸਾਫ਼ ਸੁਣਾਈ ਨਹੀਂ ਦਿੱਤੀ";
const lastControlTurn = () => control.locator('[data-testid="turn"]').last();
for (const attempt of [1, 2]) {
  n = await lastTurnId();
  await say("patient", UNCLEAR);
  caption = await waitForCaption(n);
  await check((await caption.getAttribute("data-status")) === "unclear", `unclear turn ${attempt} is unclear on /screen`);
  const notice = caption.locator('[data-testid="notice-didNotCatch"]');
  await check(
    (await notice.count()) === 1 &&
      (await notice.innerText()).includes("Sorry, I did not catch that. Please say it again.") &&
      (await notice.innerText()).includes("ਮਾਫ਼ ਕਰਨਾ ਜੀ"),
    `unclear turn ${attempt}: the say-it-again notice in both languages`,
  );
  const unclearText = await caption.innerText();
  await check(unclearText.includes("Not spoken") && !unclearText.includes("[en-CA]"), `unclear turn ${attempt}: not spoken, no translation`);
  await tv.waitForSelector('[data-testid="interpreter-line"][data-purpose="ask_to_repeat"]', { timeout: 15000 });
  const line = tv.locator('[data-testid="interpreter-line"][data-purpose="ask_to_repeat"]');
  await check(
    (await line.count()) === 1 && (await line.innerText()).includes(ASK_AGAIN_PA) && !(await line.innerText()).includes("Sorry"),
    `unclear turn ${attempt}: the interpreter asks again in Punjabi only`,
  );
  await control.waitForFunction(
    (attemptNo) => {
      const turns = document.querySelectorAll('[data-testid="turn"]');
      return turns[turns.length - 1]?.textContent?.includes(`unclear, not spoken (attempt ${attemptNo} of 2)`);
    },
    attempt,
    { timeout: 15000 },
  );
  await check((await lastControlTurn().getAttribute("data-status")) === "unclear", `/control logs attempt ${attempt} of 2`);
  const streakLine = await control.locator('[data-testid="unclear-streak"] li[data-speaker="patient"]').innerText();
  await check(
    attempt === 1
      ? streakLine.includes("Patient: not caught once")
      : streakLine === "Patient: not caught twice in a row; a human interpreter is offered on the next",
    `/control shows the patient's streak after attempt ${attempt}`,
  );
}
await shot(control, "control-unclear");
await shot(tv, "screen-unclear");
n = await lastTurnId();
await say("patient", UNCLEAR);
caption = await waitForCaption(n);
await check((await caption.getAttribute("data-status")) === "escalated", "the third unclear turn in a row escalates");
await check((await caption.locator('[data-testid="notice-interpreterOffered"]').count()) === 1, "the third offers a human interpreter in both languages");
await check((await tv.locator('[data-testid="interpreter-line"][data-purpose="ask_to_repeat"]').count()) === 0, "the third is not asked again");
await control.waitForFunction(
  () => document.querySelector('[data-testid="notice"]')?.textContent?.includes("not caught three times in a row"),
  undefined,
  { timeout: 15000 },
);
await check(true, "/control names the low-confidence escalation");
await check((await control.locator('[data-testid="unclear-streak"]').count()) === 0, "/control clears the streak after the third");
await shot(control, "control-unclear-escalated");

const PRIVATE = /"turn\.analysis"|"turn\.readback_required"|"empathy\.nudge"|"emotion"|"backTranslation"|"certainty"|"nudges"/;
const leaked = [...tvFrames, ...lateFrames].filter((f) => PRIVATE.test(f));
if (leaked.length) await fail(`/screen received private data: ${leaked[0].slice(0, 200)}`);
await check(true, `/screen received ${tvFrames.length + lateFrames.length} frames, none private`);
// Every caption a screen received, live or in a visit.state snapshot.
const captionsSeen = [...tvFrames, ...lateFrames].flatMap((f) => {
  const event = JSON.parse(f);
  if (event.type === "turn.result") return [event.payload];
  if (event.type === "visit.state") return event.payload.turns;
  return [];
});
const wrongDose = captionsSeen.filter((c) => c.sourceText.includes("(test: mismatch)") && c.translation !== null);
await check(
  captionsSeen.some((c) => c.sourceText.includes("(test: mismatch)")) && wrongDose.length === 0,
  "the blocked turn reached /screen without its translation",
);
const unclearSeen = captionsSeen.filter((c) => c.status === "unclear");
await check(
  unclearSeen.length >= 2 && unclearSeen.every((c) => c.translation === null && c.criticalValues.length === 0),
  "the unclear turns reached /screen without a translation",
);
await check(!tvFrames.some((f) => f.includes("unclearStreak")), "/screen never received the unclear streak");

await browser.close();
