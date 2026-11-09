// Shared e2e steps for consent (CDR-005, demo-night-mvp task 3.2). The server refuses every turn, the
// introduction, and name replies until consent is given, and fixes the languages while it is given, so every
// script that speaks gives consent first, and one that changes the language withdraws it first.

/** Give consent on the patient's behalf from /control, unless this visit already has it. */
export async function giveConsent(control) {
  const consent = control.locator('[data-testid="consent"]');
  await consent.waitFor({ timeout: 15000 });
  if ((await consent.getAttribute("data-state")) === "given") return;
  await control.click('[data-testid="consent-give"]');
  await control.waitForSelector('[data-testid="consent"][data-state="given"]', { timeout: 15000 });
}

/** Choose the patient's language on /control, withdrawing consent first if it is given. */
export async function chooseLanguage(control, language) {
  const consent = control.locator('[data-testid="consent"]');
  await consent.waitFor({ timeout: 15000 });
  if ((await consent.getAttribute("data-state")) === "given") {
    await control.click('[data-testid="consent-withdraw"]');
    await control.waitForSelector('[data-testid="consent"][data-state="withdrawn"]', { timeout: 15000 });
  }
  await control.selectOption('[data-testid="patient-language"]', language);
  await control.waitForFunction(
    (lang) => document.querySelector('[data-testid="consent-notice"] p')?.getAttribute("lang") === lang,
    language,
    { timeout: 15000 },
  );
}

/** Give consent over a raw controller socket ({ next, send }), using the notice in its first visit.state. */
export async function giveConsentOnSocket({ next, send }, state) {
  if (state.consent) return;
  const { version, language } = state.consentNotice;
  send("consent.give", { noticeVersion: version, language });
  await next("consent.changed");
}
