# Tasks

## 0. Human decision review gate

TDRs: IDR-004

- [x] 0.1 Project lead reviews IDR-004 and sets it to accepted or rejected; verify `python3 scripts/check_tdr.py` shows no pending records for this change (2026-11-06: accepted by rashodkorala)
- [ ] 0.2 Decide whether the speaker correction reuses an existing discard path or needs a CDR-001 amendment; verify the decision is recorded in IDR-004 Review Notes or a CDR-001 amendment

## 1. Shared speaking signal

TDRs: ADR-005

- [ ] 1.1 Implement only after the main checkout's current work is committed, and confirm the base and file owners with the supervising session; verify the branch history shows this change on top of that commit
- [ ] 1.2 Add `isSpeaking()` and `onSpeaking()` to `web/lib/speech.ts` as in design.md, covering the server voice and the Azure fallback (ended by the player's audio end, not by synthesis completing); verify with a unit test of the state changes for back-to-back items, a failed item, and a fetch gap

## 2. Feasibility

TDRs: ADR-005, IDR-004

- [ ] 2.1 Confirm Azure continuous language identification supports `en-CA` with each of `pa-IN`, `fr-CA`, `ta-LK`, and `si-LK`; verify by a short live run per pair on the laptop, logged in `docs/speech-test.md`

## 3. Continuous capture

TDRs: ADR-005, IDR-001, IDR-004, CDR-001

- [ ] 3.1 Add the continuous capture with two-language identification, silence segmentation, pause and resume, and token refresh to `web/lib/speech.ts`; verify the web typecheck and lint pass
- [ ] 3.2 Pause listening on the shared speaking signal and resume after a short tail; verify with a unit test of the pause rule
- [ ] 3.3 Add the hands-free toggle, language-to-speaker mapping, last-speaker indicator, read-back pause, and push-to-talk override to `web/components/Controller.tsx`; verify with a unit test of the mapping
- [ ] 3.4 Add the one-action speaker correction; verify a corrected turn is resubmitted with the other speaker and the original is discarded

## 4. Verification

TDRs: EDR-002, IDR-004

- [ ] 4.1 Add a hands-free run to `web/e2e/` with a fake recogniser feeding alternating languages; verify speakers and languages are correct and no spoken translation is resubmitted
- [ ] 4.2 Run a ten-turn hands-free visit on the laptop with the Punjabi and Tamil speakers; verify mislabels and echo turns are counted in `docs/speech-test.md` and latency is comparable with push-to-talk
