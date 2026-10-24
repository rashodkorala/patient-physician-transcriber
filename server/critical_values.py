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

DIGIT_MAP = str.maketrans("੦੧੨੩੪੫੬੭੮੯०१२३४५६७८९", "01234567890123456789")

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
        "minute": ("ਮਿੰਟ", "ਮਿੰਟਾਂ"),
        "hour": ("ਘੰਟਾ", "ਘੰਟੇ"),
        "day": ("ਦਿਨ",),
        "week": ("ਹਫ਼ਤਾ", "ਹਫ਼ਤੇ", "ਹਫਤਾ", "ਹਫਤੇ"),
        "month": ("ਮਹੀਨਾ", "ਮਹੀਨੇ"),
        "year": ("ਸਾਲ",),
    },
}
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

# Frequencies normalised to (times, period).
FREQUENCIES: dict[str, list[tuple[str, tuple[int, str]]]] = {
    "en": [
        (r"\bonce (?:a|per|each) day\b|\bonce daily\b|\bone time (?:a|per) day\b|\bevery day\b|\bdaily\b", (1, "day")),
        (r"\btwice (?:a|per|each) day\b|\btwice daily\b|\b(?:two|2) times (?:a|per) day\b", (2, "day")),
        (r"\b(?:three|3) times (?:a|per) day\b", (3, "day")),
        (r"\b(?:four|4) times (?:a|per) day\b", (4, "day")),
        (r"\bonce (?:a|per) week\b|\bweekly\b", (1, "week")),
    ],
    "fr": [
        (r"\bune fois par jour\b|\btous les jours\b|\bchaque jour\b|\bquotidiennement\b", (1, "day")),
        (r"\bdeux fois par jour\b|\b2 fois par jour\b", (2, "day")),
        (r"\btrois fois par jour\b|\b3 fois par jour\b", (3, "day")),
        (r"\bquatre fois par jour\b|\b4 fois par jour\b", (4, "day")),
        (r"\bune fois par semaine\b", (1, "week")),
    ],
    "pa": [
        (r"ਦਿਨ ਵਿੱਚ ਇੱਕ ਵਾਰ|ਦਿਨ ਵਿਚ ਇਕ ਵਾਰ|ਰੋਜ਼ਾਨਾ ਇੱਕ ਵਾਰ|ਰੋਜ਼ ਇੱਕ ਵਾਰ|ਹਰ ਰੋਜ਼|ਰੋਜ਼ਾਨਾ", (1, "day")),
        (r"ਦਿਨ ਵਿੱਚ ਦੋ ਵਾਰ|ਦਿਨ ਵਿਚ ਦੋ ਵਾਰ|ਰੋਜ਼ਾਨਾ ਦੋ ਵਾਰ|ਦਿਨ ਵਿੱਚ 2 ਵਾਰ", (2, "day")),
        (r"ਦਿਨ ਵਿੱਚ ਤਿੰਨ ਵਾਰ|ਦਿਨ ਵਿਚ ਤਿੰਨ ਵਾਰ|ਦਿਨ ਵਿੱਚ 3 ਵਾਰ", (3, "day")),
        (r"ਹਫ਼ਤੇ ਵਿੱਚ ਇੱਕ ਵਾਰ|ਹਫਤੇ ਵਿੱਚ ਇੱਕ ਵਾਰ", (1, "week")),
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


def _words_to_digits(text: str) -> str:
    """Rewrite English number words ("five hundred", "twenty-one") as digits."""
    return _words_to_digits_mapped(text)[0]


def _words_to_digits_mapped(text: str) -> tuple[str, list[tuple[int, int]]]:
    """As _words_to_digits, with the span in `text` each character of the result came from."""
    out: list[str] = []
    spans: list[tuple[int, int]] = []
    last = 0
    for m in _NUMBER_PHRASE.finditer(text):
        digits = str(_phrase_value(m.group(0)))
        out += [text[last : m.start()], digits]
        spans += [(i, i + 1) for i in range(last, m.start())]
        spans += [m.span()] * len(digits)  # every digit stands for the whole phrase
        last = m.end()
    out.append(text[last:])
    spans += [(i, i + 1) for i in range(last, len(text))]
    return "".join(out), spans


def quantities(text: str, language: str) -> list[Quantity]:
    """Numbers in `text`, each with the unit that follows it, if any."""
    # English number words and unit words from every language are accepted in any text:
    # translations and speech recognition often mix languages for numbers and units.
    written = unicodedata.normalize("NFC", text)
    prepared, spans = _words_to_digits_mapped(_prepare(text))
    decimal_comma = lang_key(language) == "fr"
    unit_forms: dict[str, tuple[str, ...]] = {}
    for table in UNITS.values():
        for key, forms in table.items():
            unit_forms[key] = tuple({*unit_forms.get(key, ()), *forms})
    alternation = "|".join(
        sorted((re.escape(f) for forms in unit_forms.values() for f in forms), key=len, reverse=True)
    )
    pattern = re.compile(rf"(?<![\w.,])(\d+(?:[.,]\d+)?)(?:\s*({alternation})(?!\w))?", re.IGNORECASE)
    found: list[Quantity] = []
    for m in pattern.finditer(prepared):
        raw_number = m.group(1)
        if "," in raw_number:
            whole, frac = raw_number.split(",")
            raw_number = f"{whole}.{frac}" if decimal_comma or len(frac) != 3 else f"{whole}{frac}"
        unit = None
        if m.group(2):
            word = m.group(2).lower()
            unit = next(k for k, forms in unit_forms.items() if word in (f.lower() for f in forms))
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
    remaining = quantities(translation, target_language)

    for q in quantities(source_text, source_language):
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
