// Hands-free end-to-end check (continuous-listening task 4.1), against a freshly started stack with
// TRANSLATOR=fake and a web app built with NEXT_PUBLIC_SPEECH_TEST_HOOKS=on.
// "fake": a fake recogniser stands in for Azure. Each utterance goes to the side whose language it was
// heard in, nothing is taken from the room while the interpreter speaks or a dose waits for read-back,
// short replies wait for the physician (by button or key), and holding a speaker overrides listening.
// "tamil": Tamil is listened for as ta-IN and its turns are recorded as ta-LK.
// "azure": the real recogniser hears a recording through Chrome's fake microphone (needs the Azure key);
// pass a WAV with an English sentence, a pause, and a Punjabi sentence.
// Usage: CHROMIUM_PATH=... node e2e/hands-free.mjs fake|tamil [baseUrl]
//        CHROMIUM_PATH=... node e2e/hands-free.mjs azure <wav> [baseUrl]
import { chromium } from "playwright-core";
import { chooseLanguage, giveConsent } from "./consent-steps.mjs";

const mode = process.argv[2];
const wav = mode === "azure" ? process.argv[3] : null;
const base = process.argv[mode === "azure" ? 4 : 3] ?? "http://localhost:3000";
if (!["fake", "tamil", "azure"].includes(mode) || (mode === "azure" && !wav)) {
  console.error("Usage: node e2e/hands-free.mjs fake|tamil [baseUrl], or azure <wav> [baseUrl]");
  process.exit(2);
}
const DOSE = "Use the nitroglycerin spray: 0.4 milligrams, one spray under your tongue.";

const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH ?? "/opt/pw-browsers/chromium",
  args: [
    "--autoplay-policy=no-user-gesture-required",
    "--use-fake-ui-for-media-stream",
    "--use-fake-device-for-media-stream",
    ...(wav ? [`--use-file-for-fake-audio-capture=${wav}`] : []),
  ],
});
const fail = async (message) => {
  console.error(`FAIL: ${message}`);
  await browser.close();
  process.exit(1);
};
const check = async (condition, message) => (condition ? console.log(`ok: ${message}`) : fail(message));

const control = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
await control.context().grantPermissions(["microphone"], { origin: new URL(base).origin });
const submits = [];
control.on("websocket", (ws) => {
  if (new URL(ws.url()).pathname !== "/ws/visit") return;
  ws.on("framesent", (f) => {
    const command = JSON.parse(String(f.payload));
    if (command.type === "turn.submit") submits.push(command.payload);
  });
});
if (mode !== "azure") {
  // The fake recogniser: the test says what was heard, and in which recognition locale.
  await control.addInitScript(() => {
    window.__fakeListening = (recognition, deliver) => {
      window.__listeningFor = recognition;
      window.__muted = false;
      window.__hear = (text, locale) => deliver({ text, recognition: locale, confidence: 0.9, endOfSpeechAt: Date.now() });
      return { setMuted: (muted) => (window.__muted = muted), stop: async () => (window.__hear = null) };
    };
  });
}

const waitFor = async (condition, message, timeout = 30000) => {
  for (let waited = 0; !(await condition()); waited += 100) {
    if (waited > timeout) await fail(message);
    await control.waitForTimeout(100);
  }
};
const state = () => control.getAttribute('[data-testid="listening"]', "data-state");
const hear = (text, locale) => control.evaluate(([t, l]) => window.__hear(t, l), [text, locale]);
const muted = () => control.evaluate(() => window.__muted);
const last = () => submits.at(-1);

await control.goto(`${base}/control`);
await control.waitForSelector('[data-testid="connection"]:text("open")', { timeout: 30000 });

if (mode === "tamil") await chooseLanguage(control, "ta-LK");
await giveConsent(control);
await control.check('[data-testid="hands-free"]');
await control.waitForSelector('[data-testid="listening"][data-state="listening"]', { timeout: 15000 });
await check(true, "hands-free is listening");

if (mode === "tamil") {
  await waitFor(() => control.evaluate(() => Boolean(window.__hear)), "listening started");
  const locales = await control.evaluate(() => window.__listeningFor);
  await check(locales.join() === "en-CA,ta-IN", `listens for English and Tamil as ta-IN (${locales})`);
  await hear("எனக்கு மூன்று நாட்களாக தலைவலி இருக்கிறது.", "ta-IN");
  await waitFor(() => submits.length === 1, "the Tamil turn is submitted");
  await check(last().speaker === "patient" && last().language === "ta-LK", "Tamil heard as ta-IN is the patient's turn in ta-LK");
} else if (mode === "fake") {
  await waitFor(() => control.evaluate(() => Boolean(window.__hear)), "listening started");
  const locales = await control.evaluate(() => window.__listeningFor);
  await check(locales.join() === "en-CA,pa-IN", `listens for English and Punjabi (${locales})`);

  // A physician sentence goes straight through, and its translation is spoken.
  await hear("How have you been feeling since your last visit?", "en-CA");
  await waitFor(() => submits.length === 1, "the physician turn is submitted");
  await check(last().speaker === "physician" && last().language === "en-CA", "English is the physician's turn");
  await waitFor(async () => (await state()) === "voice", "listening pauses while the interpreter speaks", 20000);
  await check(await muted(), "the microphone is muted while the interpreter speaks");
  await hear("ਤੁਸੀਂ ਆਪਣੀ ਪਿਛਲੀ ਮੁਲਾਕਾਤ ਤੋਂ ਬਾਅਦ ਕਿਵੇਂ ਮਹਿਸੂਸ ਕਰ ਰਹੇ ਹੋ?", "pa-IN"); // the voice's own echo
  await waitFor(async () => (await state()) === "listening", "listening resumes after the voice", 30000);
  await check(!(await muted()), "the microphone is unmuted after the voice");
  await check(submits.length === 1, "the interpreter's own voice was not taken as a patient turn");
  await check(
    (await control.locator('[data-testid="listening"]').innerText()).includes("last heard physician"),
    "the controller shows who was heard last",
  );

  // A patient sentence in Punjabi.
  await hear("ਮੈਨੂੰ ਤਿੰਨ ਦਿਨਾਂ ਤੋਂ ਸਿਰ ਦਰਦ ਹੈ।", "pa-IN");
  await waitFor(() => submits.length === 2, "the patient turn is submitted");
  await check(last().speaker === "patient" && last().language === "pa-IN", "Punjabi is the patient's turn");
  await waitFor(async () => (await state()) === "listening", "listening resumes after the patient's relay", 30000);

  // A one-word reply heard as English waits; the physician says it was the patient's.
  await hear("We.", "en-CA");
  await control.waitForSelector('[data-testid="held-reply"]', { timeout: 5000 });
  await check((await control.innerText('[data-testid="held-text"]')) === "We.", "the short reply is held, showing what was heard");
  await control.waitForTimeout(500);
  await check(submits.length === 2, "a held reply is not sent until the physician chooses");
  await control.click('[data-testid="held-patient"]');
  await waitFor(() => submits.length === 3, "the held reply is sent once chosen");
  await check(last().speaker === "patient" && last().language === "pa-IN", "the chosen speaker and language are used");
  await check(!(await control.locator('[data-testid="held-reply"]').count()), "the held reply is cleared");
  await waitFor(async () => (await state()) === "listening", "listening resumes", 30000);

  // The same by key, with the hands-free checkbox still focused.
  await control.focus('[data-testid="hands-free"]');
  await hear("ਹਾਂ ਜੀ।", "pa-IN");
  await control.waitForSelector('[data-testid="held-reply"]', { timeout: 5000 });
  await control.keyboard.press("2");
  await waitFor(() => submits.length === 4, "pressing 2 sends the held reply");
  await check(last().speaker === "patient" && last().text === "ਹਾਂ ਜੀ।", "key 2 says the held reply was the patient's");
  await waitFor(async () => (await state()) === "listening", "listening resumes", 30000);

  // A dose waits for read-back, and nothing is taken from the room meanwhile.
  await hear(DOSE, "en-CA");
  await control.waitForSelector('[data-testid="readback"]', { timeout: 15000 });
  await waitFor(async () => (await state()) === "readback", "listening pauses for the read-back");
  await check(await muted(), "the microphone is muted during read-back");
  const before = submits.length;
  await hear("ਠੀਕ ਹੈ ਡਾਕਟਰ ਸਾਹਿਬ, ਮੈਂ ਸਮਝ ਗਿਆ।", "pa-IN");
  await control.waitForTimeout(500);
  await check(submits.length === before, "nothing is submitted while a dose waits for read-back");
  await control.click('[data-testid="readback-confirm"]');
  await waitFor(async () => (await state()) === "listening", "listening resumes after read-back and its relay", 30000);

  // Holding a speaker overrides hands-free.
  await control.keyboard.down("1");
  await waitFor(async () => (await state()) === "pushToTalk", "holding 1 pauses hands-free");
  await check(await muted(), "the hands-free microphone is muted while a speaker is held");
  await control.keyboard.up("1");
  await waitFor(async () => (await state()) === "listening", "releasing 1 resumes hands-free", 15000);
} else {
  // The real recogniser through the fake microphone: one English and one Punjabi turn, each on its side.
  await waitFor(() => submits.some((s) => s.language === "en-CA"), "an English turn is heard", 45000);
  await waitFor(() => submits.some((s) => s.language === "pa-IN"), "a Punjabi turn is heard", 45000);
  const english = submits.find((s) => s.language === "en-CA");
  const punjabi = submits.find((s) => s.language === "pa-IN");
  console.log(`info: heard ${JSON.stringify(english.text)} and ${JSON.stringify(punjabi.text)}`);
  await check(english.speaker === "physician" && punjabi.speaker === "patient", "Azure's identification routes each side");
}

await check(!(await control.locator("body").innerText()).includes("Hands-free stopped"), "hands-free never stopped");
await browser.close();
