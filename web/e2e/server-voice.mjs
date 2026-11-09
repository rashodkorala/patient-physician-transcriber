// mediator-voice end-to-end check (tasks 3.1, 3.3, and 3.5): run against a freshly started live stack
// with ELEVENLABS_API_KEY set, since the introduction is only offered before a visit's first turn.
// "punjabi": the introduction, the name questions, the welcome, and a physician turn are each fetched
// from /api/speech/{id} as audio and played; prints the caption-to-audio time for the turn.
// "sinhala" (needs TEST_LANGUAGES=on): no server voice for Sinhala, so /api/speech returns 503 and the
// browser's Azure voice speaks the turn instead.
// Usage: CHROMIUM_PATH=... node e2e/server-voice.mjs punjabi|sinhala [baseUrl]
import { chromium } from "playwright-core";
import { chooseLanguage, giveConsent } from "./consent-steps.mjs";

const mode = process.argv[2];
const base = process.argv[3] ?? "http://localhost:3000";
if (!["punjabi", "sinhala"].includes(mode)) {
  console.error("Usage: node e2e/server-voice.mjs punjabi|sinhala [baseUrl]");
  process.exit(2);
}
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

const control = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
// Every server-audio element that starts playing, with the time it started.
await control.addInitScript(() => {
  window.__played = [];
  const play = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function () {
    this.addEventListener("playing", () => window.__played.push(Date.now()), { once: true });
    return play.call(this);
  };
});
const speech = [];
control.on("response", (r) => {
  const url = new URL(r.url());
  if (url.pathname.startsWith("/api/speech/")) {
    speech.push({ id: url.pathname.split("/").pop(), language: url.searchParams.get("language"), status: r.status() });
  }
});
// Text sent to Azure for synthesis; the controller also opens Azure connections early to warm up,
// so an open connection alone does not mean Azure spoke.
const azureSpoke = [];
const results = []; // when each turn.result frame reached the page
control.on("websocket", (ws) => {
  if (ws.url().includes("tts.speech.microsoft.com")) {
    ws.on("framesent", (f) => /path:\s*ssml/i.test(String(f.payload)) && azureSpoke.push(Date.now()));
  }
  if (new URL(ws.url()).pathname === "/ws/visit") {
    ws.on("framereceived", (f) => String(f.payload).includes('"turn.result"') && results.push(Date.now()));
  }
});

await control.goto(`${base}/control`);
await control.waitForSelector('[data-testid="connection"]:text("open")', { timeout: 15000 });

const say = async (speaker, text) => {
  await control.selectOption('[data-testid="typed-speaker"]', speaker);
  await control.fill('[data-testid="typed-text"]', text);
  await control.click('[data-testid="typed-send"]');
};
const waitFor = async (condition, message, timeout = 30000) => {
  for (let waited = 0; !condition(); waited += 200) {
    if (waited > timeout) await fail(message);
    await control.waitForTimeout(200);
  }
};
const played = () => control.evaluate(() => window.__played.length);

if (mode === "punjabi") {
  if (!(await control.locator('[data-testid="intro-start"]').count())) {
    await fail("no Start introduction button: run against a freshly started server");
  }
  await giveConsent(control);
  await control.click('[data-testid="intro-start"]');
  // The introduction in English and Punjabi, then the physician's question, in English only.
  await waitFor(() => speech.length >= 3, "the introduction and first question are fetched as server audio");
  await check(
    speech.slice(0, 3).every((s) => s.status === 200),
    `introduction and question audio come from the server (${speech.map((s) => s.language).join(", ")})`,
  );
  await say("physician", "I'm Dr. Thomas");
  await control.waitForSelector('[data-testid="intro-proposed"]:has-text("Dr. Thomas")', { timeout: 20000 });
  await control.click('[data-testid="intro-confirm"]');
  await say("patient", "Harpreet");
  await control.waitForSelector('[data-testid="intro-proposed"]:has-text("Harpreet")', { timeout: 20000 });
  await control.click('[data-testid="intro-confirm"]');
  await control.waitForSelector('[data-testid="introduction"][data-state="done"]', { timeout: 20000 });
  // Every line asked for so far must play before the turn, so the turn's own audio is the next to start.
  // The welcome's lines are asked for one by one after both names are confirmed: wait for quiet.
  for (let seen = -1; seen !== speech.length; ) {
    seen = speech.length;
    await control.waitForTimeout(3000);
  }
  const lines = speech.filter((r) => r.status === 200).length;
  await waitFor(() => speech.length === lines, "every interpreter line is server audio");
  for (let i = 0; i < 900 && (await played()) < lines; i++) await control.waitForTimeout(100);
  await check((await played()) === lines, `all ${lines} interpreter lines played, in order`);

  await say("physician", "How have you been feeling since your last visit?");
  await waitFor(() => results.length >= 1, "the turn is relayed");
  const captionAt = results[0];
  await waitFor(() => speech.length > lines, "the turn is fetched as server audio");
  await check(speech[lines].status === 200 && speech[lines].language === "pa-IN", "the turn's audio comes from the server in Punjabi");
  for (let i = 0; i < 300 && (await played()) <= lines; i++) await control.waitForTimeout(50);
  const startedAt = await control.evaluate((n) => window.__played[n], lines);
  await check(Boolean(startedAt), "the turn's audio plays");
  console.log(`info: caption to audio ${startedAt - captionAt} ms`);
  await control.waitForTimeout(6000);
  await check(!(await control.locator("body").innerText()).includes("voice failed"), "the turn is not marked as voice failed");
  await check(azureSpoke.length === 0, "Azure never spoke");
} else {
  await chooseLanguage(control, "si-LK");
  await giveConsent(control);
  await say("physician", "How have you been feeling since your last visit?");
  await waitFor(() => speech.length >= 1, "the turn's audio is asked for");
  await check(speech[0].status === 503, "the server has no Sinhala voice (503)");
  await waitFor(() => azureSpoke.length >= 1, "Azure speaks the turn instead", 20000);
  await check(true, "the browser falls back to the Azure Sinhala voice");
  await control.waitForTimeout(3000);
  const notice = await control.locator("body").innerText();
  await check(!notice.includes("voice failed"), "the turn is not marked as voice failed");
}

await browser.close();
