// Demo beats end-to-end check (demo-night-mvp tasks 3.3, 5.1, and 5.2): run against the fake-model stack.
// Drives docs/demo-script.md beats 4 (off-the-record pause), 5 (presenter mismatch, blocked dose, then
// read-back), and 6 (mark high risk, then the simulated interpreter call) on /control and checks what
// /control and /screen show. /screen must show every notice in both languages and never receive injection
// state, private fields, or the wrong dose. Beat 8 (transcript review) needs the review screen (task 3.5).
// Usage: node e2e/demo-beats.mjs [baseUrl] [screenshotDir]
import { chromium } from "playwright-core";

const visitChannel = (ws) => new URL(ws.url()).pathname === "/ws/visit";

const base = process.argv[2] ?? "http://localhost:3000";
const shots = process.argv[3];
const DOSE = "Use the nitroglycerin spray: 0.4 milligrams, one spray under your tongue when the chest pain starts.";
const ANGIOGRAM =
  "I'd like to refer you for a test called an angiogram, which looks at the blood vessels of your heart.";
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH ?? "/opt/pw-browsers/chromium" });

const fail = async (message) => {
  console.error(`FAIL: ${message}`);
  await browser.close();
  process.exit(1);
};
const check = async (condition, message) => (condition ? console.log(`ok: ${message}`) : fail(message));

const tv = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const tvFrames = [];
tv.on("websocket", (ws) => visitChannel(ws) && ws.on("framereceived", (f) => tvFrames.push(String(f.payload))));
await tv.goto(`${base}/screen`);
await tv.waitForSelector('[data-testid="connection"][data-state="open"]', { timeout: 15000 });

const control = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
await control.goto(`${base}/control`);
await control.waitForSelector('[data-testid="connection"]:text("open")', { timeout: 15000 });

/** Screenshots of both pages at the widths and colour schemes the TV and laptop use, and a phone. */
// A timed phase (the simulated call) passes before every combination is captured, so it gets one of each page.
const capture = async (name, timed = false) => {
  if (!shots) return;
  for (const scheme of timed ? ["dark"] : ["light", "dark"]) {
    for (const [page, widths, height] of [
      [control, timed ? [1280] : [1280, 390], 1000],
      [tv, timed ? [1920] : [1920, 390], 1080],
    ]) {
      await page.emulateMedia({ colorScheme: scheme });
      for (const width of widths) {
        await page.setViewportSize({ width, height: width < 600 ? 844 : height });
        // Let the layout settle and the screen's smooth scroll to the newest row finish before capturing.
        await page.waitForTimeout(800);
        const which = page === control ? "control" : "screen";
        await page.screenshot({ path: `${shots}/${name}-${which}-${width}-${scheme}.png`, fullPage: page === control });
      }
    }
  }
  await control.setViewportSize({ width: 1280, height: 1000 });
  await tv.setViewportSize({ width: 1920, height: 1080 });
};

const say = async (speaker, text) => {
  await control.selectOption('[data-testid="typed-speaker"]', speaker);
  await control.fill('[data-testid="typed-text"]', text);
  await control.click('[data-testid="typed-send"]');
};
const lastTurnId = () =>
  tv.evaluate(() => [...document.querySelectorAll('[data-testid="caption"]')].at(-1)?.dataset.turnId ?? null);
const waitForCaption = async (before) => {
  await tv.waitForFunction(
    (id) => ([...document.querySelectorAll('[data-testid="caption"]')].at(-1)?.dataset.turnId ?? null) !== id,
    before,
    { timeout: 15000 },
  );
  return tv.locator('[data-testid="caption"]').last();
};
const both = (text, ...parts) => parts.every((p) => text.includes(p));
// The injected dose, 4 mg, and not the 4 inside the correct 0.4 mg.
const WRONG_DOSE = /(?<![\d.])4 ਮਿਲੀਗ੍ਰਾਮ/;

// A spoken turn first, so the pause is seen hiding real captions.
let n = await lastTurnId();
await say("patient", "ਮੇਰੀਆਂ ਗੱਲਾਂ ਕੌਣ ਦੇਖੇਗਾ?");
await waitForCaption(n);

// ---------- Beat 4: off-the-record pause (task 3.3) ----------
await control.click('[data-testid="pause"]');
await tv.waitForSelector('[data-testid="paused"]', { timeout: 10000 });
const pausedText = await tv.locator('[data-testid="paused"]').innerText();
await check(both(pausedText, "ਰੋਕਿਆ ਗਿਆ ਹੈ", "Paused. Nothing is being recorded."), "TV shows the paused notice in Punjabi and English");
await check((await tv.locator('[data-testid="caption"]').count()) === 0, "TV shows no captions while paused");
await control.waitForSelector('[data-testid="paused"]', { timeout: 5000 });
await check(await control.locator('[data-testid="typed-send"]').isDisabled(), "controller cannot send a turn while paused");
await capture("beat4-paused");
await control.click('[data-testid="resume"]');
await tv.waitForSelector('[data-testid="paused"]', { state: "detached", timeout: 10000 });
// The paused notice and the captions swap in separate renders, so wait for the caption rather than counting at once.
await tv.waitForSelector('[data-testid="caption"]', { timeout: 10000 }).catch(() => null);
await check((await tv.locator('[data-testid="caption"]').count()) === 1, "captions return when the visit resumes");

// ---------- Beat 5: presenter mismatch, blocked, then repeated (tasks 5.1 and 5.2) ----------
await control.click('[data-testid="presenter"] summary');
await control.click('[data-testid="injection-arm"]');
await control.waitForSelector('[data-testid="injection-state"]:text("mismatch armed")', { timeout: 5000 });
await check(true, 'controller shows the mismatch "armed"');
await capture("beat5-armed");

n = await lastTurnId();
await say("physician", DOSE);
const blocked = await waitForCaption(n);
await check((await blocked.getAttribute("data-status")) === "blocked", "the injected dose is blocked on the TV");
const blockedText = await blocked.innerText();
await check(both(blockedText, "Please repeat", "ਕਿਰਪਾ ਕਰਕੇ ਦੁਬਾਰਾ ਬੋਲੋ"), "TV asks to repeat in both languages");
await check(!blockedText.includes("ਮਿਲੀਗ੍ਰਾਮ"), "TV never shows the wrong translation");
const injectedTurn = control.locator('[data-testid="turn"][data-injected="true"]');
await injectedTurn.waitFor({ timeout: 5000 });
await check((await injectedTurn.getAttribute("data-status")) === "blocked", "controller marks the blocked turn as the presenter mismatch");
await check(WRONG_DOSE.test(await injectedTurn.innerText()), "controller shows the mismatched value");
await check((await control.locator('[data-testid="injection"]').getAttribute("data-state")) === "fired", "controller shows the control fired");
await capture("beat5-blocked");

await say("physician", DOSE);
await control.waitForSelector('[data-testid="readback"]', { timeout: 15000 });
n = await lastTurnId();
await control.click('[data-testid="readback-confirm"]');
const repeated = await waitForCaption(n);
await check((await repeated.getAttribute("data-status")) === "final", "the repeated dose is confirmed and spoken");
await check((await repeated.innerText()).includes("0.4"), "the repeated dose keeps 0.4");
await check((await control.locator('[data-testid="turn"][data-injected="true"]').count()) === 1, "only the injected turn is marked");
const statuses = await tv.$$eval('[data-testid="caption"]', (els) => els.map((e) => e.dataset.status));
await check(statuses.slice(-2).join(",") === "blocked,final", "TV shows the turn as blocked, then repeated");

// ---------- Beat 6: mark high risk, then the simulated interpreter (task 3.3) ----------
await control.click('[data-testid="mark-high-risk"]');
const offer = tv.locator('[data-testid="interpreter-notice"][data-phase="offered"]');
await offer.waitFor({ timeout: 10000 });
await check(
  both(await offer.innerText(), "A human interpreter is offered", "ਮਨੁੱਖੀ ਦੁਭਾਸ਼ੀਆ ਉਪਲਬਧ ਹੈ"),
  "a high-risk mark offers an interpreter on the TV in both languages",
);
await control.waitForSelector('[data-testid="marker"][data-reason="high_risk"]', { timeout: 5000 });
await check(true, "the mark is recorded in the controller's log");
n = await lastTurnId();
await say("physician", ANGIOGRAM);
await waitForCaption(n);
await check(await offer.isVisible(), "the offer stays while the physician explains");
await capture("beat6-offered");

await control.click('[data-testid="interpreter-accept"]');
const connecting = tv.locator('[data-testid="interpreter-notice"][data-phase="connecting"]');
await connecting.waitFor({ timeout: 5000 });
await check(
  both(await connecting.innerText(), "Connecting to a human interpreter", "ਮਨੁੱਖੀ ਦੁਭਾਸ਼ੀਏ ਨਾਲ ਜੋੜਿਆ ਜਾ ਰਿਹਾ ਹੈ"),
  "TV shows the connecting state in both languages",
);
await control.waitForSelector('[data-testid="interpreter"][data-phase="connecting"]', { timeout: 2000 });
await check(true, "controller shows the connecting state");
await capture("beat6-connecting", true);
const simulated = tv.locator('[data-testid="interpreter-notice"][data-phase="simulated"]');
await simulated.waitFor({ timeout: 8000 });
await check(
  both(await simulated.innerText(), "Interpreter would join here (simulated)", "ਦੁਭਾਸ਼ੀਆ ਇੱਥੇ ਸ਼ਾਮਲ ਹੋਵੇਗਾ"),
  "the simulated call closes with its notice in both languages",
);
await control.waitForSelector('[data-testid="interpreter"][data-phase="simulated"]', { timeout: 2000 });
await capture("beat6-simulated", true);
await tv.waitForSelector('[data-testid="interpreter-notice"]', { state: "detached", timeout: 10000 });
n = await lastTurnId();
await say("physician", "Thank you. Let us continue.");
await waitForCaption(n);
await check(true, "the consultation continues after the simulated call");
await check((await control.locator('[data-testid="marker"][data-reason="requested"]').count()) === 1, "the request is recorded in the controller's log");

// ---------- Nothing private reached the TV ----------
const tvWire = tvFrames.join("\n");
await check(!/injection|demo\./i.test(tvWire), "TV received no injection state or label");
await check(!/"(emotion|certainty|backTranslation|toneTags|confidence)"/.test(tvWire), "TV received no private fields");
await check(!WRONG_DOSE.test(tvWire), "TV never received the wrong dose");

// A TV that joins late sees the same: no injection in its snapshot.
const late = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const lateFrames = [];
late.on("websocket", (ws) => visitChannel(ws) && ws.on("framereceived", (f) => lateFrames.push(String(f.payload))));
await late.goto(`${base}/screen`);
await late.waitForSelector('[data-testid="caption"]', { timeout: 15000 });
const lateWire = lateFrames.join("\n");
await check(!/injection|demo\./i.test(lateWire) && !WRONG_DOSE.test(lateWire), "a late TV snapshot carries no injection and no wrong dose");

await browser.close();
console.log("PASS: demo beats 4, 5, and 6");
