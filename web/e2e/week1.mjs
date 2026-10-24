// Week 1 end-to-end check (tasks 1.1 and 1.5): run against `scripts/dev.sh --prod`
// with TRANSLATOR=fake. A typed patient turn on /control must appear on /screen with
// original and translation, and /screen must never receive controller-only data.
// Usage: node e2e/week1.mjs [baseUrl]
import { chromium } from "playwright-core";

const base = process.argv[2] ?? "http://localhost:3000";
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH ?? "/opt/pw-browsers/chromium" });
const fail = async (message) => {
  console.error(`FAIL: ${message}`);
  await browser.close();
  process.exit(1);
};

const screen = await browser.newPage();
const screenFrames = [];
screen.on("websocket", (ws) => ws.on("framereceived", (f) => screenFrames.push(String(f.payload))));
await screen.goto(`${base}/screen`);
await screen.waitForSelector('[data-testid="connection"][data-state="open"]', { timeout: 15000 });
console.log("ok: /screen connected to the WebSocket");

const control = await browser.newPage();
await control.goto(`${base}/control`);
await control.waitForSelector('[data-testid="connection"]:text("open")', { timeout: 15000 });
console.log("ok: /control connected");

const line = "ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਡਾਕਟਰ ਜੀ।";
await control.fill('[data-testid="typed-text"]', line);
await control.click('[data-testid="typed-send"]');

const caption = screen.locator('[data-testid="caption"]').last();
await caption.waitFor({ timeout: 15000 });
const text = await caption.innerText();
if (!text.includes(line)) await fail(`original missing from caption: ${text}`);
if (!text.includes(`[en-CA] ${line}`)) await fail(`translation missing from caption: ${text}`);
console.log("ok: typed patient turn shown on /screen with original and translation");

const leaked = screenFrames.filter((f) => /"turn\.analysis"|"emotion"|"backTranslation"|"certainty"/.test(f));
if (leaked.length) await fail(`/screen received private data: ${leaked[0].slice(0, 200)}`);
console.log(`ok: /screen received ${screenFrames.length} frames, none private`);

await browser.close();
