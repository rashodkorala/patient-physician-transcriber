// CDR-005 and CDR-004: patient consent stops the in-progress consent notice.
// Run against an isolated demo stack: node e2e/consent-playback.mjs [baseUrl]
import assert from "node:assert/strict";
import { chromium } from "playwright-core";
import { fakeVoice } from "./visit-steps.mjs";

const base = process.argv[2] ?? "http://localhost:3000";
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH ?? "/opt/pw-browsers/chromium" });

try {
  const control = await browser.newPage();
  const patient = await browser.newPage();
  const screen = await browser.newPage();
  await fakeVoice(control, () => true);
  await screen.goto(`${base}/screen`);
  await control.goto(`${base}/control`);
  await patient.goto(`${base}/patient`);

  await control.getByTestId("consent").waitFor();
  if (await control.getByTestId("consent").getAttribute("data-state") === "given") {
    await control.getByTestId("consent-withdraw").click();
  }
  const agree = patient.getByTestId("review-consent-give");
  await agree.waitFor();
  await control.getByTestId("consent-read").click();
  await screen.getByTestId("speaking").waitFor();
  await agree.click();
  await agree.waitFor({ state: "hidden" });
  await screen.getByTestId("speaking").waitFor({ state: "hidden", timeout: 1500 });
  assert.equal(await control.getByTestId("notice").count(), 0);

  // The physician can still deliberately replay the notice after consent.
  await control.getByTestId("consent-read").click();
  await screen.getByTestId("speaking").waitFor();
  console.log("PASS: patient consent stops the current explanation and manual replay is still available");
} finally {
  await browser.close();
}
