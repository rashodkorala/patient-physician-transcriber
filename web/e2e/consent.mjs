// Consent end-to-end check (demo-night-mvp task 3.2, CDR-005) and the record-verified badge (CDR-006,
// IDR-003): run against a freshly started fake-model stack, since consent and the language can only be set
// up before the first turn. Checks that nothing can be said before consent (on /control and on the server),
// that the notice shows on /screen in the patient's language and English and is read aloud by its speech id,
// that the controller's consent is recorded on the patient's behalf, and that withdrawal brings the notice back.
// Usage: node e2e/consent.mjs [baseUrl] [serverPort] [screenshotDir]
import { chromium } from "playwright-core";

const visitChannel = (ws) => new URL(ws.url()).pathname === "/ws/visit";

const base = process.argv[2] ?? "http://localhost:3000";
const serverPort = process.argv[3] ?? "8000";
const shots = process.argv[4];
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH ?? "/opt/pw-browsers/chromium" });
const fail = async (message) => {
  console.error(`FAIL: ${message}`);
  await browser.close();
  process.exit(1);
};
const check = async (condition, message) => (condition ? console.log(`ok: ${message}`) : fail(message));

/** A raw connection in a role: send commands, and wait for the next event of a type. */
async function socket(role) {
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
  const next = (type) => {
    const i = queue.findIndex((e) => e.type === type);
    if (i >= 0) return Promise.resolve(queue.splice(i, 1)[0]);
    return new Promise((resolve) => waiters.push({ type, resolve }));
  };
  const send = (type, payload) => ws.send(JSON.stringify({ type, payload }));
  const state = (await next("visit.state")).payload;
  return { ws, next, send, state, queue };
}

const tv = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const tvFrames = [];
tv.on("websocket", (ws) => visitChannel(ws) && ws.on("framereceived", (f) => tvFrames.push(String(f.payload))));
await tv.goto(`${base}/screen`);
await tv.waitForSelector('[data-testid="connection"][data-state="open"]', { timeout: 15000 });

const control = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
const controlFrames = [];
const speechRequests = [];
control.on("websocket", (ws) => visitChannel(ws) && ws.on("framereceived", (f) => controlFrames.push(String(f.payload))));
control.on("request", (r) => r.url().includes("/api/speech/consent-") && speechRequests.push(r.url()));
await control.goto(`${base}/control`);
await control.waitForSelector('[data-testid="connection"]:text("open")', { timeout: 15000 });

const probe = await socket("controller");
if (probe.state.consent || probe.state.turns.length) await fail("this visit already has consent or turns: run against a freshly started server");

/** Screenshots of /control and /screen at the laptop, TV, and phone widths, light and dark. */
const capture = async (name) => {
  if (!shots) return;
  for (const scheme of ["light", "dark"]) {
    for (const [page, widths, height] of [
      [control, [1280, 390], 1000],
      [tv, [1920, 390], 1080],
    ]) {
      await page.emulateMedia({ colorScheme: scheme });
      for (const width of widths) {
        await page.setViewportSize({ width, height: width < 600 ? 844 : height });
        await page.waitForTimeout(800);
        const which = page === control ? "control" : "screen";
        await page.screenshot({ path: `${shots}/${name}-${which}-${width}-${scheme}.png`, fullPage: page === control });
      }
    }
  }
  await control.setViewportSize({ width: 1280, height: 1000 });
  await tv.setViewportSize({ width: 1920, height: 1080 });
};

// ---------- before consent ----------
const tvNotice = tv.locator('[data-testid="consent-notice"]');
await tvNotice.waitFor({ timeout: 10000 });
const noticeText = await tvNotice.innerText();
await check(noticeText.includes("ਦੁਭਾਸ਼ੀਆ") && noticeText.includes("AI interpreter"), "/screen shows the notice in Punjabi and English");
await check((await tv.locator('[data-testid="ready"]').count()) === 0, "/screen does not say ready before consent");
await check((await tv.locator('[data-testid="record-badge"]').count()) === 0, "an empty record shows no badge");
await check(await control.isDisabled('[data-testid="typed-send"]'), "/control cannot send a turn before consent");
await check(await control.isDisabled('[data-testid="intro-start"]'), "/control cannot start the introduction before consent");
await check(await control.isDisabled('[data-testid="hands-free"]'), "/control cannot listen hands-free before consent");
await control.keyboard.down("1");
await control.keyboard.up("1");
await check(
  (await control.locator('[data-testid="notice"]').innerText()).includes("Consent is needed"),
  "holding a speaker before consent says consent is needed",
);

// The server is the gate, whatever a client shows.
probe.send("turn.submit", { speaker: "patient", language: "pa-IN", text: "ਸਤ ਸ੍ਰੀ ਅਕਾਲ", recognitionConfidence: 1 });
const refused = (await probe.next("error")).payload;
await check(refused.command === "turn.submit" && refused.message.startsWith("Consent is needed"), "the server refuses a turn before consent");
probe.send("visit.start_introduction", {});
await check((await probe.next("error")).payload.command === "visit.start_introduction", "the server refuses the introduction before consent");
const phone = await socket("review");
phone.send("consent.withdraw", {});
const phoneRefusal = (await phone.next("command.refused")).payload;
await check(
  phoneRefusal.command === "consent.withdraw" && phoneRefusal.reason === "consent_not_given",
  "a review connection gets command.refused, with no free text",
);

// Read aloud: the controller fetches the notice by its speech id, in Punjabi only.
await control.click('[data-testid="consent-read"]');
for (let i = 0; i < 50 && !speechRequests.length; i++) await control.waitForTimeout(100);
await check(
  speechRequests.some((u) => u.includes("/api/speech/consent-pa-IN-v1?language=pa-IN")),
  "the notice is read aloud as consent-pa-IN-v1 in Punjabi",
);
await capture("consent-needed");

// A new language sets a new notice, read aloud once on its own.
await control.selectOption('[data-testid="patient-language"]', "fr-CA");
await tv.waitForFunction(() => document.querySelector('[data-testid="consent-notice"]')?.innerText.includes("interprète IA"), null, {
  timeout: 10000,
});
await check(true, "/screen shows the French notice once French is chosen");
for (let i = 0; i < 50 && !controlFrames.some((f) => f.includes('"consent-fr-CA-v1"') && f.includes('"consent.speak"')); i++) {
  await control.waitForTimeout(100);
}
await check(controlFrames.some((f) => f.includes('"consent.speak"') && f.includes("consent-fr-CA-v1")), "choosing French reads its notice aloud");
await control.selectOption('[data-testid="patient-language"]', "pa-IN");
await tv.waitForFunction(() => document.querySelector('[data-testid="consent-notice"]')?.innerText.includes("ਦੁਭਾਸ਼ੀਆ"), null, {
  timeout: 10000,
});

// ---------- consent given on the patient's behalf ----------
await control.click('[data-testid="consent-give"]');
await control.waitForSelector('[data-testid="consent"][data-state="given"][data-by="physician_on_behalf"]', { timeout: 10000 });
await check(
  (await control.locator('[data-testid="consent-status"]').innerText()).includes("on the patient’s behalf"),
  "/control records consent as given on the patient's behalf",
);
await tv.waitForSelector('[data-testid="consent-notice"]', { state: "detached", timeout: 10000 });
// With a real voice the notice may still be playing, and the speaking row stands in for "ready" until it ends.
await tv.waitForSelector('[data-testid="ready"], [data-testid="speaking"]', { timeout: 10000 });
await check(true, "/screen drops the notice and is ready once consent is given");
await tv.waitForSelector('[data-testid="record-badge"][data-status="verified"]', { timeout: 10000 });
await control.waitForSelector('[data-testid="record-badge"][data-status="verified"]', { timeout: 10000 });
await check(
  (await tv.locator('[data-testid="record-badge"]').innerText()).toLowerCase().includes("record verified"),
  "the consent entry starts the record, and both screens show it verified",
);
await check(await control.isDisabled('[data-testid="patient-language"]'), "the language is fixed while consent is given");
await check(!(await control.isDisabled('[data-testid="intro-start"]')), "the introduction can start after consent");

await control.selectOption('[data-testid="typed-speaker"]', "patient");
await control.fill('[data-testid="typed-text"]', "ਸਤ ਸ੍ਰੀ ਅਕਾਲ ਡਾਕਟਰ ਜੀ।");
await control.click('[data-testid="typed-send"]');
await tv.waitForSelector('[data-testid="caption"]', { timeout: 15000 });
await check(true, "a turn is relayed after consent");
await tv.waitForTimeout(500);
await check(
  (await tv.locator('[data-testid="record-badge"]').getAttribute("data-status")) === "verified",
  "the record stays verified as the turn is chained",
);
await capture("consent-given");

// ---------- withdrawal ----------
await control.click('[data-testid="consent-withdraw"]');
await control.waitForSelector('[data-testid="consent"][data-state="withdrawn"]', { timeout: 10000 });
await tvNotice.waitFor({ timeout: 10000 });
await check((await tv.locator('[data-testid="caption"]').count()) === 1, "withdrawal keeps the settled turn and shows the notice again");
await check(await control.isDisabled('[data-testid="typed-send"]'), "/control cannot send a turn after withdrawal");
await capture("consent-withdrawn");
await control.click('[data-testid="consent-give"]');
await control.waitForSelector('[data-testid="consent"][data-state="given"]', { timeout: 10000 });
await tv.waitForSelector('[data-testid="consent-notice"]', { state: "detached", timeout: 10000 });
await check(true, "consent can be given again");

// ---------- nothing private on the TV ----------
const tvWire = tvFrames.join("\n");
await check(!tvWire.includes('"consent.speak"'), "/screen never receives consent.speak");
await check(!/"(emotion|certainty|backTranslation|toneTags|confidence|escalations|injection)"/.test(tvWire), "/screen receives no private fields");

probe.ws.close();
phone.ws.close();
await browser.close();
console.log("PASS: consent and the record badge");
