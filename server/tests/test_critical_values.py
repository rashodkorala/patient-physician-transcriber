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


def test_punjabi_oblique_plural_units():
    # "after two weeks" puts the unit in the oblique plural; each form must still count as its unit.
    for text, unit in [
        ("2 ਹਫ਼ਤਿਆਂ ਬਾਅਦ", "week"),
        ("3 ਦਿਨਾਂ ਲਈ", "day"),
        ("6 ਮਹੀਨਿਆਂ ਤੱਕ", "month"),
        ("2 ਸਾਲਾਂ ਤੋਂ", "year"),
        ("4 ਘੰਟਿਆਂ ਬਾਅਦ", "hour"),
    ]:
        assert [(q.value, q.unit) for q in quantities(text, "pa-IN")] == [(float(text[0]), unit)], text


def test_native_number_word_before_a_unit_is_matched():
    # Sonnet's own translation, which was blocked twice although it is correct (2026-10-25).
    source = "I know this is worrying. We will start a low dose and check again in two weeks."
    translation = "ਮੈਂ ਜਾਣਦਾ ਹਾਂ ਕਿ ਇਹ ਚਿੰਤਾ ਵਾਲੀ ਗੱਲ ਹੈ। ਅਸੀਂ ਘੱਟ ਮਾਤਰਾ ਨਾਲ ਸ਼ੁਰੂ ਕਰਾਂਗੇ ਅਤੇ ਦੋ ਹਫ਼ਤਿਆਂ ਬਾਅਦ ਦੁਬਾਰਾ ਜਾਂਚ ਕਰਾਂਗੇ।"
    back = "I know this is a matter of worry. We will start with a low dose and check again after two weeks."
    values = check(source, "en-CA", translation, "pa-IN", back, [])
    assert values and all(v.matched for v in values), values
    assert values[0].translated == "ਦੋ ਹਫ਼ਤਿਆਂ"
    assert [(q.value, q.unit) for q in quantities("Prenez un comprimé.", "fr-CA")] == [(1.0, "tablet")]


def test_native_article_is_not_an_extra_number():
    # "ਇੱਕ" and "une" are also "a"; read as numbers they would invent a value the source never had.
    assert check("Can I ask you something?", "en-CA", "ਕੀ ਮੈਂ ਤੁਹਾਨੂੰ ਇੱਕ ਗੱਲ ਪੁੱਛ ਸਕਦਾ ਹਾਂ?", "pa-IN", "", []) == []
    assert check("I have a question.", "en-CA", "J'ai une question.", "fr-CA", "", []) == []
    assert quantities("un médicament neuf", "fr-CA") == []


def test_tamil_units_take_case_endings_tdm_004():
    # Tamil adds the case ending to the unit itself; each form must still count as its unit.
    for text, value, unit in [
        ("500 மில்லிகிராம் மருந்தை", 500, "mg"),
        ("30 நிமிடங்கள் நடக்க", 30, "minute"),
        ("3 மாதங்களில்", 3, "month"),
        ("3 மாதத்துக்குப் பிறகு", 3, "month"),
        ("2 வாரங்களுக்கு", 2, "week"),
        ("5 நாட்கள்", 5, "day"),
        ("54 வயது", 54, "year"),
        ("௫௦௦ மி.கி", 500, "mg"),
    ]:
        assert [(q.value, q.unit) for q in quantities(text, "ta-LK")] == [(float(value), unit)], text
    # மாத்திரை (tablet) starts like மாத (month); the longer stem wins.
    assert [(q.value, q.unit) for q in quantities("1 மாத்திரை", "ta-LK")] == [(1.0, "tablet")]


def test_tamil_relays_from_the_live_run_are_matched_tdm_004():
    # Correct Sonnet relays that were blocked on 6 November 2026 because Tamil units and numbers were unread.
    cases = [
        (
            "Take metformin, 500 milligrams, twice a day with meals.", "en-CA",
            "டாக்டர் பட்டேல் சொல்வது என்னவென்றால், நீங்கள் மெட்ஃபோர்மின் 500 மில்லிகிராம் மருந்தை தினமும் இரண்டு முறை உணவுடன் எடுத்துக்கொள்ள வேண்டும்.",
            "ta-LK", "Dr. Patel is saying that you should take metformin, 500 milligrams, twice a day with meals.",
            ["metformin"], {"metformin": ["மெட்ஃபோர்மின்"]},
        ),
        (
            "Try to walk for 30 minutes every day.", "en-CA",
            "டாக்டர் பட்டேல் சொல்கிறார், நீங்கள் ஒவ்வொரு நாளும் 30 நிமிடங்கள் நடக்க முயற்சி செய்ய வேண்டும்.",
            "ta-LK", "Dr. Patel is saying you should try to walk for 30 minutes every day.", [], {},
        ),
        (
            "எனக்கு ஐம்பத்து நான்கு வயது. என் அம்மாவுக்கு சர்க்கரை வியாதி இருந்தது.", "ta-LK",
            "Meena Rajaratnam is saying that they are 54 years old, and that their mother had diabetes (sugar disease).",
            "en-CA", "மீனா ராஜரத்னம் சொல்வது என்னவென்றால், அவருக்கு 54 வயது, மேலும் அவருடைய அம்மாவுக்கு சர்க்கரை வியாதி இருந்தது.",
            [], {},
        ),
    ]  # fmt: skip
    for source, src, translation, tgt, back, meds, forms in cases:
        values = check(source, src, translation, tgt, back, meds, forms)
        assert values and all(v.matched for v in values), (source, values)
    assert check(*cases[0][:5], [])[1].translated == "தினமும் இரண்டு முறை"


def test_tamil_changed_frequency_and_dose_are_unmatched_tdm_004():
    source = "Take metformin, 500 milligrams, twice a day with meals."
    wrong_dose = "மெட்ஃபோர்மின் 5000 மில்லிகிராம் தினமும் இரண்டு முறை உணவுடன் எடுக்கவும்."
    wrong_freq = "மெட்ஃபோர்மின் 500 மில்லிகிராம் தினமும் உணவுடன் எடுக்கவும்."
    assert not all(v.matched for v in check(source, "en-CA", wrong_dose, "ta-LK", "", []))
    assert not all(v.matched for v in check(source, "en-CA", wrong_freq, "ta-LK", "", []))


def test_tamil_frequency_phrases_are_not_quantities_tdm_004():
    # "ஒரு நாளைக்கு" is "per day", not one day; "ஒரு" alone is also "a".
    assert [(q.value, q.unit) for q in quantities("ஒரு நாளைக்கு இரண்டு முறை ஒரு மாத்திரை", "ta-LK")] == [(1.0, "tablet")]
    assert frequencies("ஒரு நாளைக்கு இரண்டு முறை", "ta-LK")[0][0] == (2, "day")
    assert frequencies("தினமும் இரண்டு வேளை", "ta-LK")[0][0] == (2, "day")
    assert [f for f, _ in frequencies("தினமும் நடக்க வேண்டும்", "ta-LK")] == [(1, "day")]
    assert check("Can I ask you something?", "en-CA", "நான் உங்களிடம் ஒரு கேள்வி கேட்கலாமா?", "ta-LK", "", []) == []


def test_native_number_runs_add_largest_first():
    assert _words_to_digits("ஐம்பத்து நான்கு வயது", "ta-LK") == "54 வயது"
    assert _words_to_digits("நூற்று இருபத்து ஐந்து மில்லிகிராம்", "ta-LK") == "125 மில்லிகிராம்"
    assert _words_to_digits("vingt-deux semaines", "fr-CA") == "22 semaines"
    # A range is not one number; it is left as words.
    assert _words_to_digits("இரண்டு மூன்று நாள்", "ta-LK") == "இரண்டு மூன்று நாள்"


def test_punjabi_relays_blocked_on_3_november_are_matched_cdr_002():
    # Correct relays from docs/voice-test.md, blocked because ਪਚਵੰਜਾ and "ਇੱਕ ਐਸਪਰੀਨ" were unread.
    aspirin = {"aspirin": ["ਐਸਪਰੀਨ"]}
    cases = [
        (
            "ਡਾਕਟਰ ਜੀ, ਕੀ ਮੈਨੂੰ ਵੀ ਮੇਰੇ ਪਿਤਾ ਜੀ ਵਾਂਗ ਦਿਲ ਦਾ ਦੌਰਾ ਪਵੇਗਾ? ਮੇਰੇ ਪਿਤਾ ਜੀ ਪਚਵੰਜਾ ਸਾਲ ਦੀ ਉਮਰ ਵਿੱਚ ਦਿਲ ਦੇ ਦੌਰੇ ਨਾਲ ਗੁਜ਼ਰ ਗਏ ਸਨ।", "pa-IN",
            "Gurpreet Singh is asking whether they will also have a heart attack, like their father. Their father passed away from a heart attack at the age of 55.",
            "en-CA", "", [], {},
        ),
        (
            "Also take one aspirin, 81 milligrams, once a day.", "en-CA",
            "ਡਾਕਟਰ ਪਟੇਲ ਕਹਿ ਰਹੇ ਹਨ ਕਿ ਤੁਹਾਨੂੰ ਇਸ ਦੇ ਨਾਲ ਇੱਕ ਐਸਪਰੀਨ, 81 ਮਿਲੀਗ੍ਰਾਮ, ਦਿਨ ਵਿੱਚ ਇੱਕ ਵਾਰ ਲੈਣੀ ਚਾਹੀਦੀ ਹੈ।",
            "pa-IN", "Dr. Patel is saying that you should also take one aspirin, 81 milligrams, once a day.", ["aspirin"], aspirin,
        ),
        (
            "ਹਰ ਰੋਜ਼ ਇੱਕ ਐਸਪਰੀਨ ਲੈਣੀ ਹੈ। ਜੇ ਛਾਤੀ ਵਿੱਚ ਦਰਦ ਹੋਵੇ ਤਾਂ ਬੈਠ ਕੇ ਜੀਭ ਹੇਠਾਂ ਇੱਕ ਸਪਰੇਅ ਕਰਨੀ ਹੈ।", "pa-IN",
            "Gurpreet Singh is saying they have to take 1 aspirin every day. If they have chest pain, they have to sit down and use 1 spray under the tongue.",
            "en-CA", "", ["ਐਸਪਰੀਨ"], {"ਐਸਪਰੀਨ": ["aspirin"]},
        ),
        ("Une aspirine par jour, tous les jours.", "fr-CA",
         "Lucie Tremblay is saying that they take one aspirin a day, every day.", "en-CA", "", ["aspirine"], {}),
    ]  # fmt: skip
    for source, src, translation, tgt, back, meds, forms in cases:
        values = check(source, src, translation, tgt, back, meds, forms)
        assert values and all(v.matched for v in values), (source, values)


def test_a_count_of_one_reads_the_same_in_every_language_cdr_002():
    # "an aspirin" and "a tablet" are counts of one, as "une aspirine" and "ஒரு மாத்திரை" are.
    assert all(
        v.matched
        for v in check(
            "Take an aspirin.", "en-CA", "Prenez une aspirine.", "fr-CA", "", ["aspirin"], {"aspirin": ["aspirine"]}
        )
    )
    assert all(v.matched for v in check("Take a tablet.", "en-CA", "ஒரு மாத்திரை எடுக்கவும்.", "ta-LK", "", []))
    # A changed count is still caught.
    assert not all(
        v.matched
        for v in check(
            "Take one aspirin.", "en-CA", "Prenez deux aspirines.", "fr-CA", "", ["aspirin"], {"aspirin": ["aspirine"]}
        )
    )
    # Articles before other words are not numbers.
    values = check("Take it once a week for a while.", "en-CA", "Prenez-le une fois par semaine.", "fr-CA", "", [])
    assert [v.kind for v in values] == ["frequency"]
    assert quantities("I have a question about a test.", "en-CA") == []  # fmt: skip


def test_hundreds_multiply_cdr_002():
    assert _words_to_digits("ਪੰਜ ਸੌ ਮਿਲੀਗ੍ਰਾਮ", "pa-IN") == "500 ਮਿਲੀਗ੍ਰਾਮ"
    assert _words_to_digits("cinq cents milligrammes", "fr-CA") == "500 milligrammes"
    assert _words_to_digits("soixante-dix jours", "fr-CA") == "70 jours"
    assert _words_to_digits("இரண்டு ஆயிரம் மில்லிகிராம்", "ta-LK") == "2000 மில்லிகிராம்"
    # "quatre-vingts" (4 x 20) is not a pattern the composer reads; it is left as words.
    assert _words_to_digits("quatre-vingts jours", "fr-CA") == "quatre-vingts jours"
