# Tasks

## 0. Human decision review gate

TDRs: MDD-006, IDR-006

- [x] 0.1 Project lead reviews MDD-006 and IDR-006 and sets each to accepted or rejected, and decides whether IDR-005, ADR-010, and MDD-005 are amended by a review note or superseded; verify `python3 scripts/check_tdr.py` no longer lists MDD-006 or IDR-006 as awaiting review
  Done 2026-11-16: rashodkorala accepted both in session and decided IDR-005, ADR-010, and MDD-005 are amended by reference, not superseded; recorded by an agent at his request.
- [x] 0.2 Project lead adds `affect-in-words` to `related_changes` of MDD-004, MDD-005, ADR-004, ADR-006, ADR-010, CDR-002, CDR-008, IDR-005, and EDR-002, or drafts replacements; verify each record lists the change
  Done 2026-11-16: added at rashodkorala's request, with amendment notes in MDD-005, IDR-005, and ADR-010.
- [x] 0.3 Project lead answers the design's Open Questions (phrase visible in the caption text, interpreter lines, certainty steadiness, emotion or manner as the source); verify the answers are recorded in the Review Notes of MDD-006 or IDR-006
  Done 2026-11-16: rashodkorala's four answers are recorded in the Review Notes of both records and in the design's Resolved decisions.

## 1. Constant voice

TDRs: MDD-006, IDR-006, ADR-010, EDR-002

- [x] 1.1 Replace the per-manner, per-emotion, and certainty deliveries in `server/voice.py` with one fixed delivery for turn relays and interpreter lines (removing `LINE_DELIVERY`) and use it in the speak gate in `server/main.py`; verify `server/tests/test_voice.py` has a test named for IDR-006 that every speaker, manner, emotion, and certainty gets the identical delivery, and that an interpreter line (introduction, name question, signal line) gets that identical delivery too
  Done 2026-11-16: `server/voice.py` has one `DELIVERY` (`[calm]`, 0.55); the tables, `delivery_for`, `delivery_for_turn`, the steadiness, and `LINE_DELIVERY` are gone, and `Voice.stream` no longer takes a delivery, so the speak gate in `server/main.py` returns only text and language. `test_every_turn_and_interpreter_line_gets_the_one_constant_delivery_idr_006` drives every manner, emotion, and certainty for each speaker, an introduction, a name question, and a signal line through the speak gate into the ElevenLabs adapter, and checks every vendor call has the same tag and stability.
- [x] 1.2 Remove the tests and assertions that required a delivery per manner and per emotion (`test_every_manner_has_a_delivery_and_physician_turns_follow_it_idr_005`, `test_patient_and_companion_turns_convey_the_speakers_emotion_idr_005`, `test_patient_turn_is_spoken_conveying_the_patients_emotion_idr_005`, and `test_every_emotion_and_certainty_has_a_delivery`) or rewrite them to the constant behaviour; verify the full server suite passes with `python3 -m pytest server/tests`
  Done 2026-11-16: the four table tests and the certainty steadiness test are removed, and the speak gate tests in `test_voice.py`, `test_trust_channel.py`, `test_unclear_turns.py`, and `test_consent.py` now expect text and language only. The suite passes with `uv run pytest` from `server/` (545 passed; `python3 -m pytest` has no pytest outside the project environment).

## 2. Affect phrase in the frame

TDRs: MDD-006, IDR-006, ADR-004, ADR-006, CDR-002, EDR-002

- [x] 2.1 Add the affect-phrase rule for patient and companion turns to the translate prompt in `server/graph/turn_graph.py`: one hedged phrase in the opening frame when the emotion is clearly not calm, none for calm, never on a physician turn; verify `test_prompts_define_the_affect_phrase_rule_idr_006` in `server/tests/test_turn_graph.py` checks the prompt text
  Done 2026-11-16: the translate prompt names the emotion in the frame for patient and companion turns only, with the suggested phrase per emotion, none for calm or a physician turn, one at most, frame only, and reads emotion from the words alone with calm as the default; `test_prompts_define_the_affect_phrase_rule_idr_006` checks the text. The manner rule's "(the voice carries those)" now reads "(the caption label carries those)", since the voice no longer carries manner.
- [x] 2.2 Teach the fake model in `server/fake_model.py` to write the phrase from the emotion it reads, in the frame only; verify graph tests with the mocked model cover a worried patient turn with exactly one phrase in the frame, a calm patient turn with none, a companion turn with the companion named and one phrase, and a physician turn with none
  Done 2026-11-16: the fake model opens a non-calm patient or companion relay with "<Speaker> says, <phrase>, " (and reads embarrassed from the words); tests for a worried patient (one phrase, frame only, named or not), a calm patient (none), a companion (named, one phrase), and a worried physician (none) pass.
- [x] 2.3 Tell the tone check the frame may carry one hedged affect phrase for a patient turn; verify a mocked-model test passes a relay that adds only "sounding worried" and a second test fails a relay whose phrase makes the statement more certain, and neither turn is escalated for the phrase alone
  Done 2026-11-16: the tone-check prompt accepts one hedged affect phrase in a patient or companion frame. With a mocked tone check that follows that rule, a relay adding only "sounding worried" is final at the first attempt, and one whose frame says "sounding sure it is nothing serious" escalates as `tone_failure`, while the same turn with only the hedged phrase does not.
- [x] 2.4 Verify the critical value check is unchanged: a mocked-model test has a worried patient state a medication dose, the relay keeps the exact value, the check passes as before, and the same relay with the value changed is still blocked
  Done 2026-11-16: `test_worried_patient_dose_keeps_its_value_and_the_check_still_blocks_a_change_idr_006`: the worried patient's 0.4 milligrams is kept and matched with the phrase before it in the frame, and the same relay with the value changed on both attempts is blocked; `critical_values.py` is unchanged.

## 3. Privacy

TDRs: MDD-006, IDR-006, CDR-008, CDR-002, ADR-007

- [ ] 3.1 Verify no new wire field exists: a contract test asserts `TurnResult`, `TurnCaption`, and a trust update have the same field sets as before, and `npm run check:contracts` passes
- [ ] 3.2 Verify in `server/tests/test_trust_channel.py` that for a worried patient turn the controller still receives manner and emotion as a label, and the shared screen and patient device projections carry no `manner` or `emotion` field or label, with the phrase present only inside `translation`
- [ ] 3.3 Verify the speak gate speaks the settled translation text, including the frame phrase, in the physician's language only; a channel test shows the speak-by-id text for a worried patient turn contains the phrase and is refused for any non-final turn as before

## 4. End to end

TDRs: MDD-006, IDR-006, CDR-008, EDR-002

- [ ] 4.1 Update `web/e2e/screen-manner.mjs`: keep the physician manner-label checks; change the patient section so a worried patient turn shows no manner or emotion label on `/screen`, and the caption's translation carries exactly one affect phrase inside its opening frame; a plain patient turn shows none; verify `node e2e/screen-manner.mjs` passes on a fresh fake-model stack
- [ ] 4.2 Check `web/e2e/week2.mjs`, `web/e2e/patient-voice.mjs`, `web/e2e/trust-view.mjs`, and `web/e2e/week1.mjs` for any assertion that depends on a per-emotion voice or on the old patient caption text, and adjust; verify each passes on the fake-model stack, with ports checked first and only own processes stopped
- [ ] 4.3 Check that the controller still shows the patient's emotion label in `web/e2e/trust-view.mjs` and that `/screen` and `/patient` still carry no emotion label there; verify the script passes

## 5. Known gaps and documents

TDRs: MDD-006

- [ ] 5.1 Write `docs/known-gaps.md`, one sentence per line: (a) affect is inferred from the words only, not the audio, so neutral words in a worried voice read as plain, which is why the wording is hedged; (b) the product uses hosted APIs (Claude, ElevenLabs, Azure) rather than its own models hosted on AWS and trained on real consultation data; (c) the voice is not expressive; and the privacy note that the frame phrase is spoken in the room; verify the file exists and links from `README.md`'s document list
- [ ] 5.2 Update any document that describes the voice as carrying tone, such as `docs/voice-test.md` and `docs/demo-script.md`; verify a search for "tone" and "emotion" in `docs/` shows no claim that the voice conveys affect
- [ ] 5.3 On sync or archive, update the `manner-in-relay` main spec's Purpose to the wording in this change's delta; verify `openspec validate affect-in-words` and `openspec validate manner-in-relay --specs` pass

## 6. Annotations and traceability

TDRs: MDD-006, IDR-006

- [ ] 6.1 Annotate the changed code with `@implements IDR-006: Affect phrase in the reporting frame, and one constant voice delivery` and update the superseded `@implements IDR-005` voice-delivery notes; verify `python3 scripts/check_tdr.py` passes with no annotation pointing to a non-accepted record
- [ ] 6.2 Fill `implementation_refs` and `test_refs` in MDD-006 and IDR-006 before archiving; verify the lists name real files and tests

## 7. End of project (deferred, run only when the project lead asks)

TDRs: MDD-006

- [ ] 7.1 Native speakers review how the affect phrase reads in the physician's language and in the reporting frames used for each patient language pair; verify a reviewer's sign-off is recorded in `docs/known-gaps.md`
