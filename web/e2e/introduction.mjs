// mediator-voice end-to-end check (task 2.5): run against a freshly started stack with TRANSLATOR=fake,
// since the introduction is only offered before a visit's first turn. Starts the introduction on
// /control, answers with typed replies (the same path as push-to-talk), rejects one misheard name,
// confirms both names, and checks what /screen shows: the interpreter's lines, never a proposed name.
// Usage: node e2e/introduction.mjs [baseUrl] [screenshotDir]
import { chromium } from "playwright-core";
import { giveConsent } from "./consent-steps.mjs";

// Only the visit channel; in dev mode pages also hold the Next.js hot-reload socket.
const visitChannel = (ws) => new URL(ws.url()).pathname === "/ws/visit";

const base = process.argv[2] ?? "http://localhost:3000";
const shots = process.argv[3];
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
if (!(await control.locator('[data-testid="intro-start"]').count())) {
  await fail("no Start introduction button: run against a freshly started server");
}

const say = async (speaker, text) => {
  await control.selectOption('[data-testid="typed-speaker"]', speaker);
  await control.fill('[data-testid="typed-text"]', text);
  await control.click('[data-testid="typed-send"]');
};
const linesOn = (purpose) => tv.locator(`[data-testid="interpreter-line"][data-purpose="${purpose}"]`);
const waitForLines = (purpose, count) =>
  tv.waitForFunction(
    ([p, n]) => document.querySelectorAll(`[data-testid="interpreter-line"][data-purpose="${p}"]`).length >= n,
    [purpose, count],
    { timeout: 15000 },
  );

// CDR-005: the introduction waits for consent, so Start introduction is off until the patient agrees.
await check(await control.isDisabled('[data-testid="intro-start"]'), "Start introduction waits for consent");
await giveConsent(control);
await control.click('[data-testid="intro-start"]');
await waitForLines("introduction", 1);
const intro = await linesOn("introduction").innerText();
await check(intro.includes("I'm the interpreter") && intro.includes("ਦੁਭਾਸ਼ੀਆ"), "/screen shows the introduction in English and Punjabi");
await waitForLines("ask_physician_name", 1);
await check(true, "the interpreter asks the physician first");

// A misheard name is rejected, so the interpreter asks again.
await say("physician", "I'm Dr. Tomas");
await control.waitForSelector('[data-testid="intro-proposed"]', { timeout: 15000 });
await check((await control.locator('[data-testid="intro-proposed"]').innerText()).includes("Dr. Tomas"), "/control shows the name it heard");
await control.click('[data-testid="intro-reject"]');
// The screen shows only the latest question, so count the questions it was sent.
const asks = () => tvFrames.filter((f) => f.includes('"ask_physician_name"')).length;
for (let i = 0; asks() < 2 && i < 50; i++) await tv.waitForTimeout(100);
await check(asks() === 2, "rejecting the name asks again");
await check((await linesOn("ask_physician_name").count()) === 1, "/screen shows the repeated question once");

await say("physician", "I'm Dr. Thomas");
await control.waitForSelector('[data-testid="intro-proposed"]:has-text("Dr. Thomas")', { timeout: 15000 });
await shot(control, "control-intro-proposed");
await control.click('[data-testid="intro-confirm"]');
await waitForLines("ask_patient_name", 1);
// /control and /screen are separate connections, so wait rather than read once.
await control
  .waitForFunction(() => document.querySelector('[data-testid="name-physician"]').value === "Dr. Thomas", null, {
    timeout: 5000,
  })
  .catch(() => fail("the confirmed name fills the physician name field"));
await check(true, "the confirmed name fills the physician name field");
const askPatient = await linesOn("ask_patient_name").innerText();
await check(askPatient.includes("Dr. Thomas") && askPatient.includes("ਤੁਹਾਡੇ ਡਾਕਟਰ"), "the patient is asked in Punjabi, naming Dr. Thomas");
await shot(tv, "screen-intro");

await say("patient", "Harpreet");
await control.waitForSelector('[data-testid="intro-proposed"]:has-text("Harpreet")', { timeout: 15000 });
await control.click('[data-testid="intro-confirm"]');
await waitForLines("welcome", 1);
await check((await linesOn("welcome").innerText()).includes("Harpreet"), "the welcome greets Harpreet");
await control.waitForSelector('[data-testid="introduction"][data-state="done"]', { timeout: 15000 });
await check(true, "/control shows the introduction as done");

// The first turn replaces the introduction with captions.
await say("physician", "How are you feeling today?");
await tv.waitForSelector('[data-testid="caption"]', { timeout: 15000 });
await check((await tv.locator('[data-testid="interpreter-line"]').count()) === 0, "captions replace the introduction on /screen");

const leaked = tvFrames.filter((f) => /"visit\.name_proposed"/.test(f));
await check(leaked.length === 0, "/screen never receives a proposed name");

await browser.close();
