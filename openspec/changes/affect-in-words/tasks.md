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
  Done 2026-11-16: the four table tests and the certainty steadiness test are removed, and the speak gate tests in `test_voice.py`, `test_trust_channel.py`, `test_unclear_turns.py`, and `test_consent.py` now expect text and language only. The suite passes with `uv run pytest` from `server/` (545 passed at the group 1 commit, before later groups added tests; the final count is in task 8.9; `python3 -m pytest` has no pytest outside the project environment).

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

- [x] 3.1 Verify no new wire field exists: a contract test asserts `TurnResult`, `TurnCaption`, and a trust update have the same field sets as before, and `npm run check:contracts` passes
  Done 2026-11-16: `test_affect_in_words_adds_no_wire_field_idr_006` in `server/tests/test_contracts.py` pins the field sets of `TurnResult`, `TurnCaption`, and `TrustUpdate` as they were before this change; `npm run check:contracts` passes and leaves `web/lib/generated/contract-fixtures.ts` unchanged.
- [x] 3.2 Verify in `server/tests/test_trust_channel.py` that for a worried patient turn the controller still receives manner and emotion as a label, and the shared screen and patient device projections carry no `manner` or `emotion` field or label, with the phrase present only inside `translation`
  Done 2026-11-16: `test_worried_patient_label_reaches_the_controller_only_and_the_phrase_only_the_translation_idr_006`: the controller's `turn.analysis` and `trust.update` carry emotion worried and manner plain; every event the screen and the review device receive up to the turn's `record.integrity` has no manner or emotion value, and "sounding worried" appears once, only at `.translation`.
- [x] 3.3 Verify the speak gate speaks the settled translation text, including the frame phrase, in the physician's language only; a channel test shows the speak-by-id text for a worried patient turn contains the phrase and is refused for any non-final turn as before
  Done 2026-11-16: `test_speak_gate_speaks_the_worried_patient_relay_with_its_phrase_and_refuses_non_final_turns_idr_006`: the speak gate hands the voice the settled translation, phrase included, in `en-CA` only, and returns 404 for unclear, escalated, and blocked worried turns.

## 4. End to end

TDRs: MDD-006, IDR-006, CDR-008, EDR-002

- [x] 4.1 Update `web/e2e/screen-manner.mjs`: keep the physician manner-label checks; change the patient section so a worried patient turn shows no manner or emotion label on `/screen`, and the caption's translation carries exactly one affect phrase inside its opening frame; a plain patient turn shows none; verify `node e2e/screen-manner.mjs` passes on a fresh fake-model stack
  Done 2026-11-16: the physician label checks are kept; a worried patient caption has no manner or emotion on the wire or on `/screen`, its translation carries exactly one affect phrase, at the start of its opening frame, shown on `/screen` as spoken, with no emotion word outside the translation; a plain patient caption has none. `node e2e/screen-manner.mjs` passes on a fresh fake-model stack (server :8620, web build :3620).
- [x] 4.2 Check `web/e2e/week2.mjs`, `web/e2e/patient-voice.mjs`, `web/e2e/trust-view.mjs`, and `web/e2e/week1.mjs` for any assertion that depends on a per-emotion voice or on the old patient caption text, and adjust; verify each passes on the fake-model stack, with ports checked first and only own processes stopped
  Done 2026-11-16: `week1.mjs`, `week2.mjs`, and `patient-voice.mjs` needed no change (their patient turns are calm, or their checks do not read the patient caption's text); `trust-view.mjs`'s check that `/screen` and `/patient` show no "worried" now allows the phrase inside a translation and also checks for no `data-emotion` attribute. All four pass on a fresh fake-model stack, with ports 8620 and 3620 checked free first and only this run's own processes stopped.
- [x] 4.3 Check that the controller still shows the patient's emotion label in `web/e2e/trust-view.mjs` and that `/screen` and `/patient` still carry no emotion label there; verify the script passes
  Done 2026-11-16: `trust-view.mjs` still checks that the controller's trust view reads the patient as worried and "sounds worried", and now that `/screen` shows the phrase only inside a translation and neither `/screen` nor `/patient` shows an emotion label or attribute; it passes.

## 5. Known gaps and documents

TDRs: MDD-006

- [x] 5.1 Write `docs/known-gaps.md`, one sentence per line: (a) affect is inferred from the words only, not the audio, so neutral words in a worried voice read as plain, which is why the wording is hedged; (b) the product uses hosted APIs (Claude, ElevenLabs, Azure) rather than its own models hosted on AWS and trained on real consultation data; (c) the voice is not expressive; and the privacy note that the frame phrase is spoken in the room; verify the file exists and links from `README.md`'s document list
  Done 2026-11-16: `docs/known-gaps.md` records the words-only reading, the hosted APIs, the voice that is not expressive, the phrase spoken and shown in the room, and the pending native-speaker review, one sentence per line; `README.md` links it from its document list and its trust section now says the voice is constant and affect travels as one hedged phrase.
- [x] 5.2 Update any document that describes the voice as carrying tone, such as `docs/voice-test.md` and `docs/demo-script.md`; verify a search for "tone" and "emotion" in `docs/` shows no claim that the voice conveys affect
  Done 2026-11-16: `docs/demo-script.md` and the Tamil and Sinhala test scripts now say no emotion label is shown and the patient's translation may open with the phrase; `docs/voice-test.md` keeps its dated run but notes the delivery table no longer exists and the tags did not carry. A search for "tone" and "emotion" in `docs/` finds no claim that the voice conveys affect.
- [ ] 5.3 On sync or archive, update the `manner-in-relay` main spec's Purpose to the wording in this change's delta; verify `openspec validate affect-in-words` and `openspec validate manner-in-relay --specs` pass

## 6. Annotations and traceability

TDRs: MDD-006, IDR-006

- [x] 6.1 Annotate the changed code with `@implements IDR-006: Affect phrase in the reporting frame, and one constant voice delivery` and update the superseded `@implements IDR-005` voice-delivery notes; verify `python3 scripts/check_tdr.py` passes with no annotation pointing to a non-accepted record
  Done 2026-11-16: `server/voice.py`, `server/main.py`, `server/graph/turn_graph.py`, and `server/fake_model.py` carry `@implements IDR-006` (and the first three `@implements MDD-006`); the `@implements IDR-005` and `MDD-005` notes in `server/voice.py` are replaced, since the voice no longer follows manner or emotion. `python3 scripts/check_tdr.py` prints OK.
- [x] 6.2 Fill `implementation_refs` and `test_refs` in MDD-006 and IDR-006 before archiving; verify the lists name real files and tests
  Done 2026-11-16: `implementation_refs` and `test_refs` are filled in MDD-006 and IDR-006, and every listed file and test was checked to exist; the two removed voice-delivery tests in the test refs of IDR-005 and MDD-005 are replaced by the IDR-006 constant-delivery test.

## 7. End of project (deferred, run only when the project lead asks)

TDRs: MDD-006

- [ ] 7.1 Native speakers review how the affect phrase reads in the physician's language and in the reporting frames used for each patient language pair; verify a reviewer's sign-off is recorded in `docs/known-gaps.md`

## 8. Review fixes

TDRs: MDD-006, IDR-006, ADR-004, ADR-006, ADR-011, CDR-002, CDR-007, EDR-002

- [x] 8.1 Tell the tone check who spoke and who the relay is for, allow the affect phrase only on a patient or companion turn relayed to the physician, and add a deterministic frame check that fails a physician relay carrying a phrase without flagging a physician who says "sounding"; verify a scripted physician relay with "sounding worried" (reported or not) retries and escalates even with a lenient tone check, and a physician saying "sounding better" stays final
  Done 2026-11-16: the tone-check input now carries `speaker` and `listener`; `frame_problem` in `server/graph/turn_graph.py` fails a reported phrase where none is allowed, on a calm turn, or not found exactly once, and, where no phrase is allowed, a back-translation with more "sounding" than the original. `test_affect_phrase_on_a_physician_relay_is_never_final_idr_006` (both cases) and `test_physician_who_says_sounding_is_not_mistaken_for_an_affect_phrase_idr_006` pass.
- [x] 8.2 Keep the affect phrase out of the clinical note and the patient summary: the translate call reports the phrase, the turn result keeps it as a private server-only attribute, the frozen sources take it out of each turn's and correction's translation, and the note and summary prompts say to leave how a speaker sounded out; verify with a unit test of the sources and a channel test with a worried patient turn among the note and summary sources
  Done 2026-11-16: `test_the_affect_phrase_is_left_out_of_every_source_idr_006`, `test_without_affect_phrase_idr_006`, and `test_the_affect_phrase_never_reaches_the_note_or_the_summary_idr_006` pass; neither prompt nor any note or summary sentence contains "sounding", and the chain keeps the spoken text. Spec scenarios, `design.md`, and `docs/known-gaps.md` are updated. ADR-011 and CDR-007 govern these files but do not list `affect-in-words` in `related_changes`; the project lead needs to add it or say otherwise.
- [x] 8.3 Make the manner-adverb rule physician-only, say a patient or companion frame carries at most the one affect phrase and no adverb, and make the tone check agree; verify the prompt-text tests
  Done 2026-11-16: `test_prompts_define_the_affect_phrase_rule_idr_006` and `test_prompts_define_manner_the_frame_rule_and_the_tone_check_allowance_idr_005` check the new wording, including "(the patient's caption label carries those)".
- [x] 8.4 Tell the translate call who the listener is, so a patient or companion turn in the physician's language, relayed to the patient, carries no phrase, and have the fake model follow the same rule; verify with a turn graph test and a channel test of that path, and a spec scenario
  Done 2026-11-16: `server/main.py` passes the listener to the pipeline; `test_patient_turn_relayed_to_the_patient_carries_no_phrase_idr_006` (including a forced phrase that escalates) and `test_patient_turn_in_the_physicians_language_is_relayed_to_the_patient_without_a_phrase_idr_006` pass.
- [x] 8.5 Reword the tone check so a listed phrase is acceptable in itself but still fails when it makes the statement more or less certain or serious; verify a mocked tone check fails "sounding confused" before a plainly stated dose, passes it on an unsure statement, and still passes "sounding worried" alone
  Done 2026-11-16: `test_listed_phrase_that_undermines_a_stated_dose_fails_the_tone_check_idr_006` passes, alongside the earlier group 2 tests.
- [x] 8.6 Tell the tone check that the same meaning in any language, or a close paraphrase such as "sounding anxious", counts as the frame phrase, and record in `docs/known-gaps.md` that this is unverified with a live model; verify the prompt-text test and a mocked paraphrase test
  Done 2026-11-16: `test_close_paraphrase_counts_as_the_frame_phrase_idr_006` passes and the known-gaps note is written.
- [x] 8.7 Make `web/e2e/trust-view.mjs` check the phrase sits inside a caption's translation element and nowhere else on `/screen`; verify the script passes on a fresh fake-model stack
  Done 2026-11-16: it passes on the fake-model stack (server :8620, web :3620).
- [x] 8.8 Add the new files and tests to `implementation_refs` and `test_refs` of MDD-006 and IDR-006; verify every listed file and test exists
  Done 2026-11-16: checked by script; IDR-005 and MDD-005 prose is unchanged.
- [x] 8.9 Re-run every check; verify the full server suite, ruff, web lint, typecheck, `npm run check:contracts`, `npm test`, every e2e script run before, `python3 scripts/check_tdr.py`, and `openspec validate affect-in-words` pass
  Done 2026-11-16: 573 server tests passed, and every other check and the 21 e2e runs passed.
