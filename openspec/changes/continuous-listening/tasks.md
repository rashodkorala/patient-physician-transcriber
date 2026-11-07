# Tasks

## 0. Human decision review gate

TDRs: IDR-004

- [ ] 0.1 Project lead reviews IDR-004 and sets it to accepted or rejected; verify `python3 scripts/check_tdr.py` shows no pending records for this change
- [ ] 0.2 Decide whether the speaker correction reuses an existing discard path or needs a CDR-001 amendment; verify the decision is recorded in IDR-004 Review Notes or a CDR-001 amendment

## 1. Feasibility

TDRs: ADR-005, IDR-004

- [ ] 1.1 Confirm Azure continuous language identification supports `en-CA` with each of `pa-IN`, `fr-CA`, `ta-LK`, and `si-LK`; verify by a short live run per pair on the laptop, logged in `docs/speech-test.md`

## 2. Continuous capture

TDRs: ADR-005, IDR-001, IDR-004, CDR-001

- [ ] 2.1 Add the continuous capture with two-language identification, silence segmentation, pause and resume, and token refresh to `web/lib/speech.ts`; verify the web typecheck and lint pass
- [ ] 2.2 Pause listening while the voice queue plays and resume after it drains; verify with a unit test of the pause rule
- [ ] 2.3 Add the hands-free toggle, language-to-speaker mapping, last-speaker indicator, read-back pause, and push-to-talk override to `web/components/Controller.tsx`; verify with a unit test of the mapping
- [ ] 2.4 Add the one-action speaker correction; verify a corrected turn is resubmitted with the other speaker and the original is discarded

## 3. Verification

TDRs: EDR-002, IDR-004

- [ ] 3.1 Add a hands-free run to `web/e2e/` with a fake recogniser feeding alternating languages; verify speakers and languages are correct and no spoken translation is resubmitted
- [ ] 3.2 Run a ten-turn hands-free visit on the laptop with the Punjabi and Tamil speakers; verify mislabels and echo turns are counted in `docs/speech-test.md` and latency is comparable with push-to-talk
