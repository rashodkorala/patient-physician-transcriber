// TDM-003 and TDM-004 end-to-end check (demo-night-mvp tasks 3.1 and 6.1): run against a freshly started stack
// with TRANSLATOR=fake, once without test mode ("off") and once with TEST_LANGUAGES=on ("on").
// Off: the picker lists the thirteen languages, only Punjabi, French, and Tamil can be chosen, no banner,
// and a Tamil visit relays with Tamil glossary terms on /screen.
// On: the controller shows the banner, Sinhala can be chosen too, and a Sinhala visit relays
// with Sinhala glossary terms on /screen, which never shows the banner.
// Usage: node e2e/test-languages.mjs off|on [baseUrl] [screenshotDir]
import { chromium } from "playwright-core";
import { chooseLanguage, giveConsent } from "./consent-steps.mjs";

const mode = process.argv[2];
const base = process.argv[3] ?? "http://localhost:3000";
const shots = process.argv[4];
if (!["off", "on"].includes(mode)) {
  console.error("Usage: node e2e/test-languages.mjs off|on [baseUrl] [screenshotDir]");
  process.exit(2);
}
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH ?? "/opt/pw-browsers/chromium" });

const fail = async (message) => {
  console.error(`FAIL: ${message}`);
  await browser.close();
  process.exit(1);
};
const check = async (condition, message) => (condition ? console.log(`ok: ${message}`) : fail(message));
const shot = async (page, name) => shots && page.screenshot({ path: `${shots}/${name}.png`, fullPage: true });

const tv = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await tv.goto(`${base}/screen`);
await tv.waitForSelector('[data-testid="connection"][data-state="open"]', { timeout: 15000 });
const control = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
await control.goto(`${base}/control`);
await control.waitForSelector('[data-testid="connection"]:text("open")', { timeout: 15000 });

const options = await control.$$eval('[data-testid="patient-language"] option', (els) =>
  els.map((o) => ({ value: o.value, text: o.textContent, disabled: o.disabled })),
);
const option = (english) => options.find((o) => o.text.includes(`(${english})`));
await check(options.length === 13, "the picker lists the thirteen roadmap languages");
await check(
  !option("Punjabi").disabled && !option("French").disabled && !option("Tamil").disabled,
  "Punjabi, French, and Tamil can be chosen",
);
await check(option("Mandarin").disabled && option("Mandarin").text.includes("coming soon"), "Mandarin shows as coming soon");
await check(option("English").disabled && option("English").text.includes("physician"), "English is marked as the physician's language");
await check((await tv.locator('[data-testid="test-mode-banner"]').count()) === 0, "/screen never shows the test-mode banner");

if (mode === "off") {
  await check(option("Sinhala").disabled && option("Sinhala").text.includes("coming soon"), "Sinhala shows as coming soon");
  // The controller waits for /api/health before deciding; give it time to be wrong if it would be.
  await control.waitForTimeout(1000);
  await check((await control.locator('[data-testid="test-mode-banner"]').count()) === 0, "no test-mode banner on /control");
  await shot(control, "control-languages-off");
  await chooseLanguage(control, "ta-LK");
  await giveConsent(control);
  await tv.waitForFunction(() => document.body.innerText.includes("தமிழ் / English"), null, { timeout: 15000 });
  await check(true, "/screen shows the Tamil visit");
  await control.selectOption('[data-testid="typed-speaker"]', "physician");
  await control.fill('[data-testid="typed-text"]', "Your blood sugar is too high.");
  await control.click('[data-testid="typed-send"]');
  await tv.waitForSelector('[data-testid="caption"]', { timeout: 15000 });
  const caption = await tv.locator('[data-testid="caption"]').last().innerText();
  await check(caption.includes("இரத்தச் சீனி அளவு"), "the Tamil glossary term reaches the caption");
  await shot(tv, "screen-tamil");
} else {
  await control.waitForSelector('[data-testid="test-mode-banner"]', { timeout: 5000 });
  await check(true, "/control shows the test-mode banner");
  const live = await control.$$eval('[data-testid="patient-language"] option', (els) =>
    els.filter((o) => !o.disabled).map((o) => o.value),
  );
  await check(live.includes("si-LK") && live.includes("ta-LK"), "Sinhala and Tamil can be chosen in test mode");
  await chooseLanguage(control, "si-LK");
  await giveConsent(control);
  await tv.waitForFunction(() => document.body.innerText.includes("සිංහල / English"), null, { timeout: 15000 });
  await check(true, "/screen shows the Sinhala visit");
  await control.selectOption('[data-testid="typed-speaker"]', "physician");
  await control.fill('[data-testid="typed-text"]', "Your high blood pressure can be treated.");
  await control.click('[data-testid="typed-send"]');
  await tv.waitForSelector('[data-testid="caption"]', { timeout: 15000 });
  const caption = await tv.locator('[data-testid="caption"]').last().innerText();
  await check(caption.includes("අධික රුධිර පීඩනය"), "the Sinhala glossary term reaches the caption");
  await check((await tv.locator('[data-testid="test-mode-banner"]').count()) === 0, "/screen still shows no banner");
  await shot(control, "control-languages-on");
  await shot(tv, "screen-sinhala");
}

await browser.close();
