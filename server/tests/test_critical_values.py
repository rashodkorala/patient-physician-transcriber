"""Deterministic critical value checks (CDR-002, task 2.6)."""

from critical_values import _words_to_digits, check, frequencies, quantities

DOSE_EN = "Use the nitroglycerin spray: 0.4 milligrams, one spray under your tongue."
DOSE_PA = "ਨਾਈਟ੍ਰੋਗਲਿਸਰੀਨ ਸਪਰੇਅ ਵਰਤੋ: 0.4 ਮਿਲੀਗ੍ਰਾਮ, ਜੀਭ ਹੇਠਾਂ 1 ਸਪਰੇਅ।"


def test_number_words_to_digits():
    assert _words_to_digits("take five hundred milligrams") == "take 500 milligrams"
    assert _words_to_digits("twenty-one days") == "21 days"
    assert _words_to_digits("call nine one one") == "call 911"
    assert _words_to_digits("I have a car and none of it") == "I have a car and none of it"


def test_quantities_across_scripts_and_decimal_commas():
    assert [(q.value, q.unit) for q in quantities(DOSE_EN, "en-CA")] == [(0.4, "mg"), (1.0, "spray")]
    assert [(q.value, q.unit) for q in quantities(DOSE_PA, "pa-IN")] == [(0.4, "mg"), (1.0, "spray")]
    assert [(q.value, q.unit) for q in quantities("੫੦੦ ਮਿਲੀਗ੍ਰਾਮ", "pa-IN")] == [(500.0, "mg")]
    assert [(q.value, q.unit) for q in quantities("0,4 milligramme", "fr-CA")] == [(0.4, "mg")]
    assert [q.value for q in quantities("5,000 steps", "en-CA")] == [5000.0]


def test_matching_dose_is_matched_cdr_002():
    values = check(DOSE_EN, "en-CA", DOSE_PA, "pa-IN", DOSE_EN, [])
    assert values and all(v.matched for v in values)
    assert {v.kind for v in values} == {"dose"}


def test_changed_dose_is_unmatched_cdr_002():
    wrong = DOSE_PA.replace("0.4", "4")
    values = check(DOSE_EN, "en-CA", wrong, "pa-IN", DOSE_EN, [])
    assert not all(v.matched for v in values)
    assert any(v.source == "0.4 milligrams" and not v.matched for v in values)


def test_extra_number_in_translation_is_unmatched_cdr_002():
    values = check("Take one tablet.", "en-CA", "ਇੱਕ ਗੋਲੀ ਲਓ, 2 ਵਾਰ।", "pa-IN", "Take one tablet.", [])
    assert any(v.source == "" and not v.matched for v in values)


def test_wrong_unit_is_unmatched_cdr_002():
    values = check("Take 5 mg.", "en-CA", "Prenez 5 ml.", "fr-CA", "Take 5 ml.", [])
    assert not values[0].matched


def test_frequency_matched_and_changed_cdr_002():
    ok = check("Take it twice a day.", "en-CA", "Prenez-le deux fois par jour.", "fr-CA", "Take it twice a day.", [])
    assert [v.kind for v in ok] == ["frequency"] and ok[0].matched
    bad = check("Take it twice a day.", "en-CA", "Prenez-le une fois par jour.", "fr-CA", "Take it twice a day.", [])
    assert not bad[0].matched  # a different frequency never falls back to the back-translation
    assert frequencies("ਦਿਨ ਵਿੱਚ ਦੋ ਵਾਰ ਲਓ", "pa-IN")[0][0] == (2, "day")


def test_frequency_falls_back_to_back_translation_when_unparsed():
    values = check("Take it once a day.", "en-CA", "ਇਹ ਹਰ ਸਵੇਰ ਲਓ।", "pa-IN", "Take it once a day.", [])
    assert values[0].matched


def test_medication_matched_via_glossary_form_or_back_translation():
    forms = {"aspirin": ["ਐਸਪਰੀਨ"]}
    values = check("Take aspirin.", "en-CA", "ਐਸਪਰੀਨ ਲਓ।", "pa-IN", "Take aspirin.", ["aspirin"], forms)
    assert values[0].kind == "medication" and values[0].matched
    missing = check("Take aspirin.", "en-CA", "ਗੋਲੀ ਲਓ।", "pa-IN", "Take a tablet.", ["aspirin"], forms)
    assert not missing[0].matched


def test_values_are_reported_as_written():
    assert [q.raw for q in quantities("Take one spray, then five hundred milligrams.", "en-CA")] == [
        "one spray",
        "five hundred milligrams",
    ]
    assert next(q.raw for q in quantities("੨ ਗੋਲੀਆਂ", "pa-IN")) == "੨ ਗੋਲੀਆਂ"
