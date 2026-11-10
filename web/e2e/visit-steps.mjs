// Shared steps for the demo-night-mvp group 3 end-to-end checks (explain-back, review, record view, summary,
// and tamper). Each script runs against a freshly started fake-model stack (TRANSLATOR=fake) and a web build
// made with NEXT_PUBLIC_SPEECH_TEST_HOOKS=on, so the review screen's re-speak uses a fake recogniser.
import { readFileSync } from "node:fs";
import { chromium } from "playwright-core";

export const visitChannel = (ws) => new URL(ws.url()).pathname === "/ws/visit";

/** The browser, and fail and check helpers that close it on the first failure. */
export async function start() {
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH ?? "/opt/pw-browsers/chromium",
    args: ["--autoplay-policy=no-user-gesture-required"],
  });
  const fail = async (message) => {
    console.error(`FAIL: ${message}`);
    await browser.close();
    process.exit(1);
  };
  const check = async (condition, message) => (condition ? console.log(`ok: ${message}`) : fail(message));
  return { browser, fail, check };
}

/** A page on a route, with every visit-channel frame it receives recorded, waiting until connected. */
export async function open(browser, base, route, viewport) {
  const page = await browser.newPage({ viewport });
  const frames = [];
  page.on("websocket", (ws) => visitChannel(ws) && ws.on("framereceived", (f) => frames.push(String(f.payload))));
  await page.goto(`${base}${route}`);
  const connected =
    route === "/control" || route === "/record"
      ? '[data-testid="connection"]:text("open")'
      : '[data-testid="connection"][data-state="open"]';
  await page.waitForSelector(connected, { timeout: 15000 });
  return { page, frames };
}

/** A raw connection in a role: send commands, and wait for the next event of a type. */
export async function socket(base, serverPort, role) {
  const ws = new WebSocket(`ws://${new URL(base).hostname}:${serverPort}/ws/visit?role=${role}`);
  const queue = [];
  const waiters = [];
  ws.onmessage = (m) => {
    const event = JSON.parse(m.data);
    const i = waiters.findIndex((w) => w.type === event.type);
    if (i >= 0) waiters.splice(i, 1)[0].resolve(event);
    else queue.push(event);
  };
  await new Promise((resolve, reject) => ((ws.onopen = resolve), (ws.onerror = reject)));
  const next = (type, ms = 15000) => {
    const i = queue.findIndex((e) => e.type === type);
    if (i >= 0) return Promise.resolve(queue.splice(i, 1)[0]);
    return new Promise((resolve, reject) => {
      const waiter = { type, resolve };
      waiters.push(waiter);
      setTimeout(() => {
        const at = waiters.indexOf(waiter);
        if (at >= 0) waiters.splice(at, 1);
        reject(new Error(`no ${type} within ${ms} ms`));
      }, ms);
    });
  };
  /** Whether an event of this type arrives within ms (it is consumed if so). */
  const arrives = (type, ms = 1500) =>
    next(type, ms).then(
      () => true,
      () => false,
    );
  const send = (type, payload) => ws.send(JSON.stringify({ type, payload }));
  const state = (await next("visit.state")).payload;
  return { ws, next, arrives, send, state, queue };
}

/** Say a typed turn on /control. */
export async function say(control, speaker, text) {
  await control.selectOption('[data-testid="typed-speaker"]', speaker);
  await control.fill('[data-testid="typed-text"]', text);
  await control.click('[data-testid="typed-send"]');
}

/** How many turns the controller has logged, and a wait for more. */
export const turnCount = (control) =>
  control.evaluate(() => {
    const turns = [...document.querySelectorAll('[data-testid="turn"]')];
    return turns.length;
  });

export async function waitForTurns(control, count) {
  await control.waitForFunction((n) => document.querySelectorAll('[data-testid="turn"]').length >= n, count, {
    timeout: 20000,
  });
}

/** Say a physician dose and confirm its read-back, waiting until the controller has it settled. */
export async function sayConfirmed(control, text) {
  const before = await turnCount(control);
  await say(control, "physician", text);
  await control.waitForSelector('[data-testid="readback"]', { timeout: 20000 });
  await control.click('[data-testid="readback-confirm"]');
  await control.waitForSelector('[data-testid="readback"]', { state: "detached", timeout: 15000 });
  await waitForTurns(control, before + 1);
}

/** Say a turn that settles without read-back, waiting until the controller logs it. */
export async function saySettled(control, speaker, text) {
  const before = await turnCount(control);
  await say(control, speaker, text);
  await waitForTurns(control, before + 1);
}

/** Replace push-to-talk recognition on a page: each capture returns the next queued text. */
export async function fakeRecogniser(page) {
  await page.evaluate(() => {
    window.__heard = [];
    window.__fakeCapture = () => ({
      stop: async () => ({ text: window.__heard.shift() ?? "", confidence: 0.9, endOfSpeechAt: Date.now() }),
    });
  });
}

/**
 * Serve every server voice request with a silent clip, recording the speech ids asked for, in order. Ids that
 * `long` picks get a six-second clip, so a test can see them playing; the rest a short one.
 */
export async function fakeVoice(page, long = () => false) {
  const short = readFileSync(new URL("./silence.mp3", import.meta.url));
  const longer = readFileSync(new URL("./silence-long.mp3", import.meta.url));
  const asked = [];
  await page.route("**/api/speech/**", async (route) => {
    const url = new URL(route.request().url());
    const id = decodeURIComponent(url.pathname.split("/").pop());
    asked.push({ id, language: url.searchParams.get("language") });
    await route.fulfill({ status: 200, contentType: "audio/mpeg", body: long(id) ? longer : short });
  });
  return asked;
}

/** Screenshots of pages at their widths, in light and dark. */
export async function capture(shots, name, pages) {
  if (!shots) return;
  for (const scheme of ["light", "dark"]) {
    for (const { page, which, widths, height, fullPage = true } of pages) {
      const original = page.viewportSize();
      await page.emulateMedia({ colorScheme: scheme });
      for (const width of widths) {
        await page.setViewportSize({ width, height: width < 600 ? 844 : height });
        await page.waitForTimeout(700);
        await page.screenshot({ path: `${shots}/${name}-${which}-${width}-${scheme}.png`, fullPage });
      }
      await page.setViewportSize(original);
    }
  }
  for (const { page } of pages) await page.emulateMedia({ colorScheme: "light" });
}
