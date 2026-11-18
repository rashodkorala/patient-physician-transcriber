// IDR-008: run against a fresh fake-model stack with NEXT_PUBLIC_SPEECH_TEST_HOOKS=on.
import assert from "node:assert/strict";
import { chromium } from "playwright-core";
import { chooseLanguage, giveConsent } from "./consent-steps.mjs";

const base = process.argv[2] ?? "http://localhost:3000";
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH ?? "/opt/pw-browsers/chromium" });

try {
  const control = await browser.newPage();
  const screen = await browser.newPage();
  let submissions = 0;
  control.on("websocket", (socket) => {
    if (!socket.url().includes("/ws/visit")) return;
    socket.on("framesent", ({ payload }) => {
      if (JSON.parse(String(payload)).type === "turn.submit") submissions += 1;
    });
  });
  await control.addInitScript(() => {
    window.__fakeCapture = () => ({
      stop: async () => ({
        text: "Use the nitroglycerin spray: 4 milligrams, one spray under your tongue.",
        confidence: 0.64,
        endOfSpeechAt: Date.now(),
      }),
    });
  });
  await screen.goto(`${base}/screen`);
  await control.goto(`${base}/control`);
  await control.getByTestId("connection").filter({ hasText: /^open$/ }).waitFor();
  await screen.locator('[data-testid="connection"][data-state="open"]').waitFor();
  await chooseLanguage(control, "fr-CA");
  await giveConsent(control);

  const review = control.getByTestId("speech-review");
  const capture = async () => {
    await control.getByTestId("speak-physician").hover();
    await control.mouse.down();
    await control.getByText("Listening", { exact: true }).waitFor();
    await control.mouse.up();
    await review.waitFor();
  };

  await capture();
  assert.equal(submissions, 0);
  assert.equal(await screen.getByTestId("caption").count(), 0);
  await control.getByTestId("pause").click();
  await review.waitFor({ state: "hidden" });
  assert.equal(submissions, 0);
  await control.getByTestId("resume").click();
  await control.getByTestId("pause").waitFor();

  await capture();
  await review.getByTestId("speech-review-text").fill(
    "Use the nitroglycerin spray: 0.4 milligrams, one spray under your tongue.",
  );
  await review.getByTestId("speech-review-confirm").click();
  const readback = control.getByTestId("readback");
  await readback.waitFor();
  assert.equal(submissions, 1);
  assert.match(await readback.innerText(), /0\.4/);
  assert.equal(await screen.getByTestId("caption").count(), 0);
  await readback.getByTestId("readback-confirm").click();
  await screen.getByTestId("caption").filter({ hasText: "0.4 milligrams" }).waitFor();
  console.log("PASS: private low-confidence review, pause clears it, and the corrected dose still needs read-back");
} finally {
  await browser.close();
}
