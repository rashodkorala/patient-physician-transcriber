// Speaking state end-to-end check (orb-speaking-state task 3.2, CDR-004): run against the fake-model stack.
// A controller socket reports the interpreter's voice; /screen must show the Speaking row while it plays,
// show it to a screen that joins mid-speech, drop it on voice.ended and on controller disconnect,
// and never show it for an id that may not be spoken.
// Usage: node e2e/orb-speaking.mjs [baseUrl] [serverPort]
import { chromium } from "playwright-core";

const base = process.argv[2] ?? "http://localhost:3000";
const serverPort = process.argv[3] ?? "8000";
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH ?? "/opt/pw-browsers/chromium" });
const fail = async (message) => {
  console.error(`FAIL: ${message}`);
  await browser.close();
  process.exit(1);
};

/** A controller connection: send commands, and wait for the next event of a type. */
async function controller() {
  const ws = new WebSocket(`ws://${new URL(base).hostname}:${serverPort}/ws/visit?role=controller`);
  const queue = [];
  const waiters = [];
  ws.onmessage = (m) => {
    const event = JSON.parse(m.data);
    const i = waiters.findIndex((w) => w.type === event.type);
    if (i >= 0) waiters.splice(i, 1)[0].resolve(event);
    else queue.push(event);
  };
  await new Promise((resolve, reject) => ((ws.onopen = resolve), (ws.onerror = reject)));
  const next = (type) => {
    const i = queue.findIndex((e) => e.type === type);
    if (i >= 0) return Promise.resolve(queue.splice(i, 1)[0]);
    return new Promise((resolve) => waiters.push({ type, resolve }));
  };
  const send = (type, payload) => ws.send(JSON.stringify({ type, payload }));
  await next("visit.state");
  return { ws, next, send };
}

const speakingRow = '[data-testid="speaking"] [data-testid="orb"][data-mode="speaking"]';

const screen = await browser.newPage();
await screen.goto(`${base}/screen`);
await screen.waitForSelector('[data-testid="connection"][data-state="open"]', { timeout: 15000 });

const ctl = await controller();
ctl.send("turn.submit", { speaker: "physician", language: "en-CA", text: "Hello.", recognitionConfidence: 0.95 });
const { turnId, targetLanguage } = (await ctl.next("turn.result")).payload;

ctl.send("voice.started", { speechId: "not-a-turn", language: targetLanguage });
if ((await ctl.next("error")).payload.command !== "voice.started") await fail("an unknown id was not refused");
await screen.waitForTimeout(500);
if (await screen.locator('[data-testid="speaking"]').count()) await fail("an unknown id showed as speaking");
console.log("ok: an id that may not be spoken is refused and never shown");

ctl.send("voice.started", { speechId: turnId, language: targetLanguage });
await screen.waitForSelector(speakingRow, { timeout: 5000 });
const shown = await screen.locator('[data-testid="speaking"]').getAttribute("data-language");
if (shown !== targetLanguage) await fail(`speaking row shows ${shown}, expected ${targetLanguage}`);
console.log("ok: /screen shows the interpreter speaking while the voice plays");

const late = await browser.newPage();
await late.goto(`${base}/screen`);
await late.waitForSelector(speakingRow, { timeout: 15000 });
console.log("ok: a screen joining mid-speech shows it straight away");

ctl.send("voice.ended", { speechId: turnId, language: targetLanguage });
await screen.waitForSelector('[data-testid="speaking"]', { state: "detached", timeout: 5000 });
await late.waitForSelector('[data-testid="speaking"]', { state: "detached", timeout: 5000 });
console.log("ok: the speaking row leaves when the voice ends");

ctl.send("voice.started", { speechId: turnId, language: targetLanguage });
await screen.waitForSelector(speakingRow, { timeout: 5000 });
ctl.ws.close();
await screen.waitForSelector('[data-testid="speaking"]', { state: "detached", timeout: 5000 });
console.log("ok: the speaking row leaves when the controller disconnects mid-speech");

await browser.close();
