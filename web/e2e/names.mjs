// mediator-voice end-to-end check (tasks 1.3 and 1.4): run against the dev stack with TRANSLATOR=fake.
// Sets both names on /control, saves the physician name as this device's default, checks the default
// is applied by a reloaded controller when the visit has no physician name, that typing a digit in a
// name field never starts push-to-talk, and that /screen shows the names on captions.
// Usage: node e2e/names.mjs [baseUrl] [screenshotDir]
import { chromium } from "playwright-core";

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

// One context, so a reloaded controller sees the same saved default, as on a clinic laptop.
const context = await browser.newContext({ viewport: { width: 1280, height: 1000 } });
const openControl = async () => {
  const page = await context.newPage();
  await page.goto(`${base}/control`);
  await page.waitForSelector('[data-testid="connection"]:text("open")', { timeout: 15000 });
  return page;
};
const setName = async (page, role, name) => {
  await page.fill(`[data-testid="name-${role}"]`, name);
  await page.press(`[data-testid="name-${role}"]`, "Enter");
};

const tv = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
await tv.goto(`${base}/screen`);
await tv.waitForSelector('[data-testid="connection"][data-state="open"]', { timeout: 15000 });

let control = await openControl();
// Start from a visit with no names, so the check also passes against a server that has run it before.
await setName(control, "physician", "");
await setName(control, "patient", "");
await control.waitForFunction(() => !document.querySelector('[data-testid="name-physician"]').value);
await check(await control.isDisabled('[data-testid="name-default"]'), "default cannot be saved without a name");

// 1.3: names reach the visit; the physician name is saved as the default.
await setName(control, "physician", "Dr. Thomas");
await setName(control, "patient", "Harpreet");
await control.check('[data-testid="name-default"]');
await check(
  (await control.evaluate(() => localStorage.getItem("interpreter.defaultPhysicianName"))) === "Dr. Thomas",
  "physician name saved as this device's default",
);

// A digit typed in a name field is text, not the push-to-talk key.
await control.focus('[data-testid="name-patient"]');
await control.keyboard.down("2");
await control.keyboard.up("2");
await check(!(await control.locator("text=Listening").count()), "typing 2 in a name field does not start push-to-talk");
await setName(control, "patient", "Harpreet");
await shot(control, "control-names");

// Clear the physician name for this visit, then reload: the saved default fills it again without asking.
await setName(control, "physician", "");
await control.waitForFunction(() => document.querySelector('[data-testid="name-physician"]').value === "");
await check(!(await control.isChecked('[data-testid="name-default"]')), "an empty name is not shown as the default");
await check(
  (await control.locator('[data-testid="name-default-note"]').innerText()) === "Saved default: Dr. Thomas",
  "editing the name for one visit keeps the saved default",
);
await control.close();
control = await openControl();
await control.waitForFunction(
  () => document.querySelector('[data-testid="name-physician"]').value === "Dr. Thomas",
  null,
  { timeout: 15000 },
);
await check(true, "reloaded controller applies the saved default to a visit with no physician name");
await check(await control.isChecked('[data-testid="name-default"]'), "default checkbox shows the saved default");

// 1.4: names on /screen captions.
const say = async (speaker, text) => {
  await control.selectOption('[data-testid="typed-speaker"]', speaker);
  await control.fill('[data-testid="typed-text"]', text);
  await control.click('[data-testid="typed-send"]');
};
// Wait for a new last caption, so an older turn on a reused visit never passes the check.
const lastTurnId = () =>
  tv.evaluate(() => [...document.querySelectorAll('[data-testid="caption"]')].at(-1)?.dataset.turnId ?? null);
const sayAndReadName = async (speaker, text) => {
  const before = await lastTurnId();
  await say(speaker, text);
  await tv.waitForFunction(
    (id) => ([...document.querySelectorAll('[data-testid="caption"]')].at(-1)?.dataset.turnId ?? null) !== id,
    before,
    { timeout: 15000 },
  );
  return tv.locator('[data-testid="caption"]').last().locator('[data-testid="speaker-name"]').innerText();
};
await check(
  (await sayAndReadName("physician", "Hello, how are you feeling today?")) === "Dr. Thomas",
  "physician caption on /screen names Dr. Thomas",
);
await check((await sayAndReadName("patient", "ਮੈਂ ਠੀਕ ਹਾਂ")) === "Harpreet", "patient caption on /screen names Harpreet");
await shot(tv, "screen-names");

// Leave the device as it was found.
await control.uncheck('[data-testid="name-default"]');
await browser.close();
