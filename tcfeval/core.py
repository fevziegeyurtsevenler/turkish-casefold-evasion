"""Turkish case-folding & confusable evasion of naive prompt-injection filters — and the fix.

The bug: filters that do `text.lower()` and then substring/keyword-match ASCII triggers are
broken for Turkish. Python's locale-independent `str.lower()` maps the Turkish dotted capital
'İ' (U+0130) to 'i' + COMBINING DOT ABOVE (U+0307), not plain 'i'. So:

    "İGNORE ALL PREVIOUS INSTRUCTIONS".lower()  ->  "i̇gnore all previous instructions"

and a substring test for "ignore all previous instructions" FAILS — the injection sails through.
The dotless 'ı' (U+0131) and Unicode confusables (Cyrillic/Greek/fullwidth lookalikes) do the same.

The fix is one line: Unicode-normalize (NFKC), fold confusables, and strip combining marks BEFORE
matching. This module provides both the evasion generators (to test filters) and `normalize()`
(the defense).
"""
from __future__ import annotations

import unicodedata

# ---- confusable → ASCII map (a compact, high-value subset) -----------------------------
_CONFUSABLES = {
    # Turkish special forms of I
    "İ": "I", "ı": "i",
    # Cyrillic lookalikes
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P",
    "С": "C", "Т": "T", "Х": "X", "а": "a", "е": "e", "о": "o", "р": "p", "с": "c",
    "х": "x", "у": "y", "і": "i", "ѕ": "s",
    # Greek lookalikes
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M",
    "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X", "ο": "o", "ν": "v",
    # fullwidth
    "ａ": "a", "ｉ": "i", "ｇ": "g", "ｎ": "n", "ｏ": "o", "ｒ": "r", "ｅ": "e",
}
_COMBINING_DOT = "̇"


def normalize(text: str) -> str:
    """Defense: fold text to a canonical form suitable for keyword/regex matching.
    NFKC, map confusables to ASCII, drop combining marks, then casefold()."""
    if not text:
        return ""
    # map confusables first (before NFKC, since some are canonical on their own)
    text = "".join(_CONFUSABLES.get(ch, ch) for ch in text)
    text = unicodedata.normalize("NFKC", text)
    # remove combining marks (e.g. the dot-above that lower() injects for İ)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.casefold()


def naive_lower(text: str) -> str:
    """The BROKEN normalization most filters use."""
    return (text or "").lower()


# ---- evasion generators (to test a filter) ---------------------------------------------
def evade_dotless(text: str) -> str:
    """Swap Latin i/I with Turkish dotless ı / dotted İ — reads the same to an LLM,
    breaks ASCII `.lower()` matching."""
    return text.replace("I", "İ").replace("i", "ı")


def evade_confusable(text: str) -> str:
    """Replace a few ASCII letters with Cyrillic/Greek lookalikes."""
    rev = {"a": "а", "e": "е", "o": "о", "c": "с", "p": "р", "x": "х", "i": "і",
           "A": "А", "E": "Е", "O": "О", "C": "С", "P": "Р", "H": "Н", "K": "К"}
    return "".join(rev.get(ch, ch) for ch in text)


def evade_combining(text: str) -> str:
    """Insert a combining dot above each 'i' — visually near-identical, ASCII-breaking."""
    return text.replace("i", "i" + _COMBINING_DOT)


EVASIONS = {
    "dotless-i": evade_dotless,
    "confusable": evade_confusable,
    "combining-mark": evade_combining,
}


# ---- filters (to demonstrate the bypass) -----------------------------------------------
def naive_keyword_filter(text: str, triggers) -> bool:
    """Typical broken filter: lower() + substring. Returns True if it flags the text."""
    low = naive_lower(text)
    return any(t.lower() in low for t in triggers)


def hardened_keyword_filter(text: str, triggers) -> bool:
    """Same filter with the one-line fix: normalize() before matching."""
    norm = normalize(text)
    return any(normalize(t) in norm for t in triggers)
