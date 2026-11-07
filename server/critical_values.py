"""Deterministic critical value checks: numbers, doses, units, frequencies, and medications.

CDR-002 requires `criticalValues[].matched` to be computed by code, never by the model.
The translation prompt asks for numbers as digits, so numbers are compared by value.

@implements CDR-002: Turn result schema
@contract TurnResult
@see openspec/tdr/cdr/cdr-002-turn-result-schema.md
"""

import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz

from contracts import CriticalValue

DIGIT_MAP = str.maketrans("੦੧੨੩੪੫੬੭੮੯०१२३४५६७८९௦௧௨௩௪௫௬௭௮௯", "012345678901234567890123456789")

# Unit synonyms per language. English forms are accepted in every language because
# translations often keep "mg" or "ml" as written.
UNITS: dict[str, dict[str, tuple[str, ...]]] = {
    "en": {
        "mg": ("mg", "milligram", "milligrams"),
        "mcg": ("mcg", "microgram", "micrograms"),
        "g": ("g", "gram", "grams"),
        "ml": ("ml", "millilitre", "millilitres", "milliliter", "milliliters"),
        "spray": ("spray", "sprays", "puff", "puffs"),
        "tablet": ("tablet", "tablets", "pill", "pills"),
        "minute": ("minute", "minutes", "min"),
        "hour": ("hour", "hours"),
        "day": ("day", "days"),
        "week": ("week", "weeks"),
        "month": ("month", "months"),
        "year": ("year", "years"),
    },
    "fr": {
        "mg": ("milligramme", "milligrammes"),
        "mcg": ("microgramme", "microgrammes"),
        "g": ("gramme", "grammes"),
        "ml": ("millilitre", "millilitres"),
        "spray": ("jet", "jets", "vaporisation", "vaporisations"),
        "tablet": ("comprimé", "comprimés", "pilule", "pilules"),
        "minute": ("minute", "minutes"),
        "hour": ("heure", "heures", "h"),
        "day": ("jour", "jours"),
        "week": ("semaine", "semaines"),
        "month": ("mois",),
        "year": ("an", "ans", "année", "années"),
    },
    "pa": {
        "mg": ("ਮਿਲੀਗ੍ਰਾਮ",),
        "g": ("ਗ੍ਰਾਮ",),
        "ml": ("ਮਿਲੀਲੀਟਰ",),
        "spray": ("ਸਪਰੇਅ",),
        "tablet": ("ਗੋਲੀ", "ਗੋਲੀਆਂ"),
        # Oblique plurals ("after two weeks": ਦੋ ਹਫ਼ਤਿਆਂ ਬਾਅਦ) as well as direct forms.
        "minute": ("ਮਿੰਟ", "ਮਿੰਟਾਂ"),
        "hour": ("ਘੰਟਾ", "ਘੰਟੇ", "ਘੰਟਿਆਂ"),
        "day": ("ਦਿਨ", "ਦਿਨਾਂ"),
        "week": ("ਹਫ਼ਤਾ", "ਹਫ਼ਤੇ", "ਹਫ਼ਤਿਆਂ", "ਹਫਤਾ", "ਹਫਤੇ", "ਹਫਤਿਆਂ"),
        "month": ("ਮਹੀਨਾ", "ਮਹੀਨੇ", "ਮਹੀਨਿਆਂ"),
        "year": ("ਸਾਲ", "ਸਾਲਾਂ"),
    },
    # Stems, not whole words: Tamil adds case endings to the unit itself (மாதம், மாதங்களில், மாதத்தில்).
    # The longest stem wins, so மாத்திரை (tablet) is never read as மாத (month).
    "ta": {
        "mg": ("மில்லிகிராம", "மி.கி"),
        "g": ("கிராம",),
        "ml": ("மில்லிலிட்டர", "மில்லி லிட்டர", "மி.லி"),
        "spray": ("ஸ்ப்ரே", "ஸ்பிரே"),
        "tablet": ("மாத்திரை",),
        "minute": ("நிமிட", "நிமிஷ"),
        "hour": ("மணி",),
        "day": ("நாள", "நாட்க", "தினங்க"),
        "week": ("வார",),
        "month": ("மாத",),
        # வயது is age ("54 வயது", 54 years old).
        "year": ("வருட", "ஆண்டு", "வயத"),
    },
}
# Languages whose unit forms above are stems that take endings.
STEM_LANGUAGES = {"ta"}

# Number words in each target language. Unlike English words, these are read as numbers only when
# _native_number allows it, because several double as articles or other words ("ਇੱਕ", "une", "neuf",
# "ஒரு", "ஆறு"). A run of words is added up, largest first: "vingt-deux" is 22, "ஐம்பத்து நான்கு" is 54.
NATIVE_WORDS: dict[str, dict[str, int]] = {
    "pa": {
        "ਇੱਕ": 1, "ਇਕ": 1, "ਦੋ": 2, "ਤਿੰਨ": 3, "ਚਾਰ": 4, "ਪੰਜ": 5,
        "ਛੇ": 6, "ਸੱਤ": 7, "ਅੱਠ": 8, "ਨੌਂ": 9, "ਨੌ": 9, "ਦਸ": 10,
        # 11 to 99 are each their own word (ਪਚਵੰਜਾ is 55); an unlisted spelling only costs a retry.
        "ਗਿਆਰਾਂ": 11, "ਬਾਰਾਂ": 12, "ਤੇਰਾਂ": 13, "ਚੌਦਾਂ": 14, "ਪੰਦਰਾਂ": 15, "ਸੋਲਾਂ": 16, "ਸਤਾਰਾਂ": 17,
        "ਅਠਾਰਾਂ": 18, "ਉੱਨੀ": 19, "ਵੀਹ": 20, "ਇੱਕੀ": 21, "ਬਾਈ": 22, "ਤੇਈ": 23, "ਚੌਵੀ": 24, "ਪੱਚੀ": 25,
        "ਛੱਬੀ": 26, "ਸਤਾਈ": 27, "ਅਠਾਈ": 28, "ਉਣੱਤੀ": 29, "ਤੀਹ": 30, "ਇਕੱਤੀ": 31, "ਬੱਤੀ": 32, "ਤੇਤੀ": 33,
        "ਚੌਂਤੀ": 34, "ਪੈਂਤੀ": 35, "ਛੱਤੀ": 36, "ਸੈਂਤੀ": 37, "ਅਠੱਤੀ": 38, "ਉਣਤਾਲੀ": 39, "ਚਾਲੀ": 40,
        "ਇਕਤਾਲੀ": 41, "ਬਿਆਲੀ": 42, "ਤਰਤਾਲੀ": 43, "ਚੁਤਾਲੀ": 44, "ਪੰਤਾਲੀ": 45, "ਛਿਆਲੀ": 46, "ਸੰਤਾਲੀ": 47,
        "ਅਠਤਾਲੀ": 48, "ਉਣੰਜਾ": 49, "ਪੰਜਾਹ": 50, "ਇਕਵੰਜਾ": 51, "ਬਵੰਜਾ": 52, "ਤਰਵੰਜਾ": 53, "ਚੁਰੰਜਾ": 54,
        "ਪਚਵੰਜਾ": 55, "ਛਪੰਜਾ": 56, "ਸਤਵੰਜਾ": 57, "ਅਠਵੰਜਾ": 58, "ਉਣਾਹਠ": 59, "ਸੱਠ": 60, "ਇਕਾਹਠ": 61,
        "ਬਾਹਠ": 62, "ਤਰੇਹਠ": 63, "ਚੌਂਹਠ": 64, "ਪੈਂਹਠ": 65, "ਛਿਆਹਠ": 66, "ਸਤਾਹਠ": 67, "ਅਠਾਹਠ": 68,
        "ਉਣੱਤਰ": 69, "ਸੱਤਰ": 70, "ਇਕੱਤਰ": 71, "ਬਹੱਤਰ": 72, "ਤਿਹੱਤਰ": 73, "ਚੌਹੱਤਰ": 74, "ਪਚੱਤਰ": 75,
        "ਛਿਹੱਤਰ": 76, "ਸਤੱਤਰ": 77, "ਅਠੱਤਰ": 78, "ਉਣਾਸੀ": 79, "ਅੱਸੀ": 80, "ਇਕਾਸੀ": 81, "ਬਿਆਸੀ": 82,
        "ਤਿਰਾਸੀ": 83, "ਚੁਰਾਸੀ": 84, "ਪਚਾਸੀ": 85, "ਛਿਆਸੀ": 86, "ਸਤਾਸੀ": 87, "ਅਠਾਸੀ": 88, "ਉਣਾਨਵੇਂ": 89,
        "ਨੱਬੇ": 90, "ਇਕਾਨਵੇਂ": 91, "ਬਾਨਵੇਂ": 92, "ਤਰਾਨਵੇਂ": 93, "ਚੁਰਾਨਵੇਂ": 94, "ਪਚਾਨਵੇਂ": 95,
        "ਛਿਆਨਵੇਂ": 96, "ਸਤਾਨਵੇਂ": 97, "ਅਠਾਨਵੇਂ": 98, "ਨੜਿੰਨਵੇਂ": 99, "ਸੌ": 100, "ਹਜ਼ਾਰ": 1000, "ਹਜਾਰ": 1000,
    },
    "fr": {
        "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6,
        "sept": 7, "huit": 8, "neuf": 9, "dix": 10, "onze": 11, "douze": 12, "treize": 13, "quatorze": 14,
        "quinze": 15, "seize": 16, "vingt": 20, "trente": 30, "quarante": 40, "cinquante": 50, "soixante": 60,
        "cent": 100, "cents": 100, "mille": 1000,
    },
    # Standalone forms, then the joining forms used before a smaller number (இருபது 20, இருபத்து ஐந்து 25).
    "ta": {
        "ஒன்று": 1, "ஒரு": 1, "ஓர்": 1, "இரண்டு": 2, "இரு": 2, "மூன்று": 3, "நான்கு": 4, "நாலு": 4,
        "ஐந்து": 5, "அஞ்சு": 5, "ஆறு": 6, "ஏழு": 7, "எட்டு": 8, "ஒன்பது": 9, "பத்து": 10,
        "பதினொன்று": 11, "பதினோரு": 11, "பன்னிரண்டு": 12, "பன்னிரெண்டு": 12, "பதின்மூன்று": 13,
        "பதினான்கு": 14, "பதினைந்து": 15, "பதினாறு": 16, "பதினேழு": 17, "பதினெட்டு": 18, "பத்தொன்பது": 19,
        "இருபது": 20, "முப்பது": 30, "நாற்பது": 40, "ஐம்பது": 50, "அறுபது": 60, "எழுபது": 70,
        "எண்பது": 80, "தொண்ணூறு": 90,
        "இருபத்து": 20, "இருபத்தி": 20, "முப்பத்து": 30, "முப்பத்தி": 30, "நாற்பத்து": 40, "நாற்பத்தி": 40,
        "ஐம்பத்து": 50, "ஐம்பத்தி": 50, "அறுபத்து": 60, "அறுபத்தி": 60, "எழுபத்து": 70, "எழுபத்தி": 70,
        "எண்பத்து": 80, "எண்பத்தி": 80, "தொண்ணூற்று": 90,
        "நூறு": 100, "நூற்று": 100, "இருநூறு": 200, "இருநூற்று": 200, "முந்நூறு": 300, "முன்னூறு": 300,
        "முந்நூற்று": 300, "முன்னூற்று": 300, "நானூறு": 400, "நானூற்று": 400, "ஐநூறு": 500, "ஐந்நூறு": 500,
        "ஐநூற்று": 500, "ஐந்நூற்று": 500, "அறுநூறு": 600, "அறுநூற்று": 600, "எழுநூறு": 700, "எழுநூற்று": 700,
        "எண்ணூறு": 800, "எண்ணூற்று": 800, "தொள்ளாயிரம்": 900, "ஆயிரம்": 1000,
    },
}  # fmt: skip
DOSE_UNITS = {"mg", "mcg", "g", "ml", "spray", "tablet"}

EN_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

# Pieces of Tamil frequency phrases: "per day", a count, and "times" (முறை, தடவை, or வேளை, a dose time).
_TA_DAY = "ஒரு நாளைக்கு|நாளொன்றுக்கு|நாள் ஒன்றுக்கு|தினமும்|தினசரி|ஒவ்வொரு நாளும்|நாள்தோறும்"
_TA_COUNT = "ஒரு|இரண்டு|இரு|மூன்று|நான்கு|நாலு|\\d+"
_TA_TIMES = "(?:முறை|தடவை|வேளை)"

# Frequencies normalised to (times, period).
FREQUENCIES: dict[str, list[tuple[str, tuple[int, str]]]] = {
    "en": [
        (
            r"\bonce (?:a|per|each) day\b|\bonce daily\b|\b(?:one|1) times? (?:a|per) day\b|\bevery day\b|\bdaily\b",
            (1, "day"),
        ),
        (r"\btwice (?:a|per|each) day\b|\btwice daily\b|\b(?:two|2) times (?:a|per) day\b", (2, "day")),
        (r"\b(?:three|3) times (?:a|per) day\b", (3, "day")),
        (r"\b(?:four|4) times (?:a|per) day\b", (4, "day")),
        (r"\bonce (?:a|per) week\b|\bweekly\b", (1, "week")),
    ],
    "fr": [
        (r"\b(?:une|1) fois par jour\b|\btous les jours\b|\bchaque jour\b|\bquotidiennement\b", (1, "day")),
        (r"\bdeux fois par jour\b|\b2 fois par jour\b", (2, "day")),
        (r"\btrois fois par jour\b|\b3 fois par jour\b", (3, "day")),
        (r"\bquatre fois par jour\b|\b4 fois par jour\b", (4, "day")),
        (r"\b(?:une|1) fois par semaine\b", (1, "week")),
    ],
    "pa": [
        (r"ਦਿਨ ਵਿੱਚ ਇੱਕ ਵਾਰ|ਦਿਨ ਵਿਚ ਇਕ ਵਾਰ|ਦਿਨ ਵਿੱਚ 1 ਵਾਰ|ਰੋਜ਼ਾਨਾ ਇੱਕ ਵਾਰ|ਰੋਜ਼ਾਨਾ 1 ਵਾਰ|ਰੋਜ਼ ਇੱਕ ਵਾਰ|ਹਰ ਰੋਜ਼|ਰੋਜ਼ਾਨਾ", (1, "day")),
        (r"ਦਿਨ ਵਿੱਚ ਦੋ ਵਾਰ|ਦਿਨ ਵਿਚ ਦੋ ਵਾਰ|ਰੋਜ਼ਾਨਾ ਦੋ ਵਾਰ|ਦਿਨ ਵਿੱਚ 2 ਵਾਰ|ਰੋਜ਼ਾਨਾ 2 ਵਾਰ", (2, "day")),
        (r"ਦਿਨ ਵਿੱਚ ਤਿੰਨ ਵਾਰ|ਦਿਨ ਵਿਚ ਤਿੰਨ ਵਾਰ|ਦਿਨ ਵਿੱਚ 3 ਵਾਰ", (3, "day")),
        (r"ਹਫ਼ਤੇ ਵਿੱਚ ਇੱਕ ਵਾਰ|ਹਫਤੇ ਵਿੱਚ ਇੱਕ ਵਾਰ|ਹਫ਼ਤੇ ਵਿੱਚ 1 ਵਾਰ|ਹਫਤੇ ਵਿੱਚ 1 ਵਾਰ", (1, "week")),
    ],
    # A count of times needs "per day" before it, since "இரண்டு முறை" alone may be twice a week; a count of
    # dose times (வேளை) is always per day. "Daily" alone is once a day only when no count follows it.
    "ta": [
        (rf"(?:{_TA_DAY})\s*(?:ஒரு|1)\s*{_TA_TIMES}|(?:{_TA_DAY})(?!\s*(?:{_TA_COUNT})\s*{_TA_TIMES})", (1, "day")),
        (rf"(?:{_TA_DAY})\s*(?:இரண்டு|இரு|2)\s*{_TA_TIMES}|(?:இரண்டு|2)\s*வேளை", (2, "day")),
        (rf"(?:{_TA_DAY})\s*(?:மூன்று|3)\s*{_TA_TIMES}|(?:மூன்று|3)\s*வேளை", (3, "day")),
        (rf"(?:{_TA_DAY})\s*(?:நான்கு|நாலு|4)\s*{_TA_TIMES}|(?:நான்கு|நாலு|4)\s*வேளை", (4, "day")),
        (r"(?:வாரத்திற்கு|வாரத்துக்கு|வாரம்)\s*(?:ஒரு|1)\s*(?:முறை|தடவை)|வாரந்தோறும்", (1, "week")),
    ],
}


def lang_key(language: str) -> str:
    return language.split("-")[0]


@dataclass(frozen=True)
class Quantity:
    value: float
    unit: str | None
    raw: str


def _prepare(text: str) -> str:
    return unicodedata.normalize("NFC", text).translate(DIGIT_MAP)


_NUMBER_WORD = "|".join([*EN_WORDS, "hundred", "thousand"])
_NUMBER_PHRASE = re.compile(
    rf"\b(?:a\s+(?=hundred|thousand))?(?:{_NUMBER_WORD})(?:[\s-]+(?:and\s+)?(?:{_NUMBER_WORD}))*\b",
    re.IGNORECASE,
)


def _phrase_value(phrase: str) -> int:
    words = re.findall(r"[a-z]+", phrase.lower())
    digits = [w for w in words if w != "and"]
    if len(digits) > 1 and all(EN_WORDS.get(w, 99) < 10 for w in digits):
        # Digits said one by one, as in "nine one one" for 911.
        return int("".join(str(EN_WORDS[w]) for w in digits))
    total, current = 0, 0
    for word in words:
        if word in EN_WORDS:
            current += EN_WORDS[word]
        elif word == "hundred":
            current = (current or 1) * 100
        elif word == "thousand":
            total += (current or 1) * 1000
            current = 0
    return total + current


# Unit words from every language, by unit key, NFC-normalised like the text they are matched against.
# Stems (STEM_LANGUAGES) are kept apart: they match a word that starts with them.
UNIT_FORMS: dict[str, tuple[str, ...]] = {}
UNIT_STEMS: list[tuple[str, str]] = []
for _lang, _table in UNITS.items():
    for _key, _forms in _table.items():
        _forms = tuple(unicodedata.normalize("NFC", f) for f in _forms)
        if _lang in STEM_LANGUAGES:
            UNIT_STEMS += [(f, _key) for f in _forms]
        else:
            UNIT_FORMS[_key] = tuple({*UNIT_FORMS.get(_key, ()), *_forms})
UNIT_STEMS.sort(key=lambda stem_key: len(stem_key[0]), reverse=True)
_UNIT_ALTERNATION = "|".join(
    sorted((re.escape(f) for forms in UNIT_FORMS.values() for f in forms), key=len, reverse=True)
)


def _unit_key(word: str) -> str | None:
    """The unit a word names in any language ("ਹਫ਼ਤਿਆਂ" -> "week", "மாதங்களில்" -> "month"), or None."""
    word = unicodedata.normalize("NFC", word).casefold()
    exact = next((k for k, forms in UNIT_FORMS.items() if word in (f.casefold() for f in forms)), None)
    return exact or next((k for stem, k in UNIT_STEMS if word.startswith(stem)), None)


# A run of native number words between word boundaries, with the word after it. Gurmukhi and Tamil
# vowel signs are not \w, so boundaries are whitespace, punctuation, or the ends of the text.
_BOUNDARY = r"\s,.;:!?()।\"'«»“”-"
# Any unit stem, with whatever ending follows it (STEM_LANGUAGES).
_UNIT_STEM = "|".join(re.escape(stem) for stem, _ in UNIT_STEMS)
_UNIT = rf"(?:{_UNIT_STEM})[^\d{_BOUNDARY}]*|(?:{_UNIT_ALTERNATION})(?!\w)"


def _native_pattern(words: dict[str, int]) -> re.Pattern[str]:
    alternation = "|".join(sorted(map(re.escape, words), key=len, reverse=True))
    word = rf"(?<![^{_BOUNDARY}])(?:{alternation})(?![^{_BOUNDARY}])"
    return re.compile(rf"({word}(?:[\s-]+{word})*)(?:\s+([^{_BOUNDARY}]+))?", re.IGNORECASE)


_NATIVE_PATTERNS = {lang: _native_pattern(words) for lang, words in NATIVE_WORDS.items()}


# Words that multiply what comes before them ("ਪੰਜ ਸੌ", "cinq cents", "இரண்டு ஆயிரம்") instead of adding.
MULTIPLIERS = {100, 1000}


def _compose(parts: list[int]) -> int | None:
    """The number a run of words says, or None when it is not one number.

    Parts are added largest first (50 + 4) and multipliers scale what came before (5 x 100). Anything
    else, such as "two or three days" said as "இரண்டு மூன்று நாள்", is left for the model to write as digits.
    """
    total, group, last = 0, 0, None
    for value in parts:
        if value in MULTIPLIERS:
            if group >= value:
                return None
            group = (group or 1) * value
            if value == 1000:
                total, group = total + group, 0
        elif last is not None and value >= last:
            return None
        else:
            group += value
        last = value
    return total + group


def _counts(next_word: str | None, counted: tuple[str, ...], units: set[str] | None = None) -> bool:
    """Whether a number word before `next_word` is a count: before a unit (of `units`, if given) or a
    medication named in this turn ("ਇੱਕ ਐਸਪਰੀਨ", one aspirin)."""
    if next_word is None:
        return False
    unit = _unit_key(next_word)
    if unit is not None and (units is None or unit in units):
        return True
    word = unicodedata.normalize("NFC", next_word).casefold()
    return any(word.startswith(c) for c in counted)


def _native_number(phrase: str, next_word: str | None, language: str, counted: tuple[str, ...] = ()) -> int | None:
    """The value of a run of native number words in `language`, or None when it is not used as a number here.

    `phrase` is one or more keys of NATIVE_WORDS[language] as written in the text; `next_word` is the word
    after it, if any; `counted` holds medication names, as for _counts.
    """
    # Only as a count: a skipped word costs a retry, a wrongly read article could match a real number.
    if not _counts(next_word, counted):
        return None
    return _compose([NATIVE_WORDS[language][w.casefold()] for w in re.split(r"[\s-]+", phrase)])


# "a" or "an" before a dose unit or a medication is a count of one, as "ਇੱਕ", "une", and "ஒரு" are there.
_ENGLISH_ARTICLE = re.compile(r"\b(an?)\s+(\w+)", re.IGNORECASE)


def _counted_forms(medications: list[str], forms: dict[str, list[str]]) -> tuple[str, ...]:
    """The first word of every name a medication goes by, for matching the word after a number."""
    names = [*medications, *(f for fs in forms.values() for f in fs)]
    firsts = {unicodedata.normalize("NFC", n).split()[0].casefold() for n in names if n.strip()}
    return tuple(f for f in firsts if len(f) >= 3)


def _words_to_digits(text: str, language: str | None = None) -> str:
    """Rewrite number words ("five hundred", "twenty-one", "ਦੋ ਹਫ਼ਤਿਆਂ") as digits."""
    return _words_to_digits_mapped(text, language)[0]


def _words_to_digits_mapped(
    text: str, language: str | None = None, counted: tuple[str, ...] = ()
) -> tuple[str, list[tuple[int, int]]]:
    """As _words_to_digits, with the span in `text` each character of the result came from."""
    replacements = [(m.start(), m.end(), str(_phrase_value(m.group(0)))) for m in _NUMBER_PHRASE.finditer(text)]
    key = lang_key(language) if language else None
    found: list[tuple[int, int, int | None]] = []
    if key in _NATIVE_PATTERNS:
        found += [
            (m.start(1), m.end(1), _native_number(m.group(1), m.group(2), key, counted))
            for m in _NATIVE_PATTERNS[key].finditer(text)
        ]
    if key == "en":
        found += [
            (m.start(1), m.end(1), 1 if _counts(m.group(2), counted, DOSE_UNITS) else None)
            for m in _ENGLISH_ARTICLE.finditer(text)
        ]
    for start, end, value in found:
        if value is not None and not any(s < end and start < e for s, e, _ in replacements):
            replacements.append((start, end, str(value)))
    out: list[str] = []
    spans: list[tuple[int, int]] = []
    last = 0
    for start, end, digits in sorted(replacements):
        out += [text[last:start], digits]
        spans += [(i, i + 1) for i in range(last, start)]
        spans += [(start, end)] * len(digits)  # every digit stands for the whole phrase
        last = end
    out.append(text[last:])
    spans += [(i, i + 1) for i in range(last, len(text))]
    return "".join(out), spans


def _mask_frequencies(text: str, language: str) -> str:
    """Blanks out frequency phrases, keeping every other character in place.

    Their numbers are compared by frequencies() as a whole, and "ஒரு நாளைக்கு" (per day) is not a quantity
    of one day.
    """
    for pattern, _ in FREQUENCIES.get(lang_key(language), []):
        text = re.sub(pattern, lambda m: " " * len(m.group(0)), text, flags=re.IGNORECASE)
    return text


_AGE_OF = re.compile(r"\bage of\s*$", re.IGNORECASE)


def quantities(text: str, language: str, counted: tuple[str, ...] = ()) -> list[Quantity]:
    """Numbers in `text`, each with the unit that follows it, if any.

    `counted` holds medication names a number word may count, as in "one aspirin" (_counted_forms).
    """
    # English number words and unit words from every language are accepted in any text:
    # translations and speech recognition often mix languages for numbers and units.
    written = unicodedata.normalize("NFC", text)
    prepared, spans = _words_to_digits_mapped(_mask_frequencies(_prepare(text), language), language, counted)
    decimal_comma = lang_key(language) == "fr"
    pattern = re.compile(rf"(?<![\w.,])(\d+(?:[.,]\d+)?)(?:\s*({_UNIT}))?", re.IGNORECASE)
    found: list[Quantity] = []
    for m in pattern.finditer(prepared):
        raw_number = m.group(1)
        if "," in raw_number:
            whole, frac = raw_number.split(",")
            raw_number = f"{whole}.{frac}" if decimal_comma or len(frac) != 3 else f"{whole}{frac}"
        unit = _unit_key(m.group(2)) if m.group(2) else None
        if unit is None and _AGE_OF.search(prepared, 0, m.start()):
            unit = "year"  # "at the age of 55" says the unit before the number
        # raw is the value as written ("one spray"), so screens can highlight it in the original text.
        raw = written[spans[m.start()][0] : spans[m.end() - 1][1]].strip()
        found.append(Quantity(value=float(raw_number), unit=unit, raw=raw))
    return found


def frequencies(text: str, language: str) -> list[tuple[tuple[int, str], str]]:
    prepared = _prepare(text)
    out = []
    for pattern, norm in FREQUENCIES.get(lang_key(language), []):
        for m in re.finditer(pattern, prepared, flags=re.IGNORECASE):
            out.append((norm, m.group(0)))
    return out


def _kind(q: Quantity) -> str:
    return "dose" if q.unit in DOSE_UNITS else "number"


def check(
    source_text: str,
    source_language: str,
    translation: str,
    target_language: str,
    back_translation: str,
    medications: list[str],
    medication_forms: dict[str, list[str]] | None = None,
) -> list[CriticalValue]:
    """Compare critical values in the source with the translation.

    Every source quantity must appear in the translation with the same value and unit.
    Any number in the translation that is not in the source is also a mismatch.
    """
    values: list[CriticalValue] = []
    counted = _counted_forms(medications, medication_forms or {})
    remaining = quantities(translation, target_language, counted)

    for q in quantities(source_text, source_language, counted):
        match = next(
            (t for t in remaining if abs(t.value - q.value) < 1e-9 and (q.unit is None or t.unit == q.unit)), None
        )
        if match:
            remaining.remove(match)
        values.append(
            CriticalValue(kind=_kind(q), source=q.raw, translated=match.raw if match else "", matched=match is not None)
        )
    for extra in remaining:
        values.append(CriticalValue(kind=_kind(extra), source="", translated=extra.raw, matched=False))

    target_freqs = frequencies(translation, target_language)
    back_freqs = frequencies(back_translation, source_language)
    for norm, raw in frequencies(source_text, source_language):
        in_target = next((r for n, r in target_freqs if n == norm), None)
        if in_target is None and not target_freqs:
            # No frequency phrase recognised in the target: fall back to the back-translation.
            in_target = next((r for n, r in back_freqs if n == norm), None)
        values.append(
            CriticalValue(kind="frequency", source=raw, translated=in_target or "", matched=in_target is not None)
        )

    forms = medication_forms or {}
    said_back = back_translation.casefold()
    said_target = translation.casefold()
    for name in medications:
        candidates = [name, *forms.get(name, [])]
        found = next(
            (
                c
                for c in candidates
                if c.casefold() in said_target or fuzz.partial_ratio(c.casefold(), said_target) >= 85
            ),
            None,
        )
        if found is None and fuzz.partial_ratio(name.casefold(), said_back) >= 85:
            found = name
        values.append(CriticalValue(kind="medication", source=name, translated=found or "", matched=found is not None))
    return values
