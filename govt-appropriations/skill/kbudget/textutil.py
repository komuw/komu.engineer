"""Text / number utilities shared across the pipeline.

All numeric handling is centralised here so the reconciliation engine and the
structural parsers agree on exactly what counts as a "number".
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Optional

# ---------------------------------------------------------------------------
# Whitespace
# ---------------------------------------------------------------------------

def norm_ws(s: str) -> str:
    """Collapse every run of whitespace to a single space and strip.

    Xpdf `-table` inserts variable padding to align columns, so template
    detection and header matching MUST normalise whitespace first.
    """
    return re.sub(r"\s+", " ", s).strip()


def norm_upper(s: str) -> str:
    return norm_ws(s).upper()


# ---------------------------------------------------------------------------
# Numeric tokens
# ---------------------------------------------------------------------------

# Any maximal run of digits with optional internal commas. Captures money
# ("680,706,667"), codes ("1017100100"), and bare years ("2025"). Used for the
# cross-engine multiset fidelity check - we compare the *bag of digit tokens*
# produced by two independent parsers.
_ANY_NUM = re.compile(r"\d[\d,]*\d|\d")

# A money value or an explicit nil dash, as they appear in the tables. Money is
# always comma-grouped here (values are >= 1,000), so requiring a comma group
# keeps codes/years out of the trailing numeric run of a table row.
_MONEY = re.compile(r"^-$|^\d{1,3}(?:,\d{3})+$")


def number_tokens(text: str) -> list[str]:
    """Every digit token on the page, in reading order (whitespace-normalised)."""
    return _ANY_NUM.findall(norm_ws(text))


def number_multiset(text: str) -> Counter:
    return Counter(number_tokens(text))


def is_money(tok: str) -> bool:
    return bool(_MONEY.match(tok))


def to_int(tok: str) -> Optional[int]:
    """Parse a money/dash token to an int. Dash (nil) -> 0. Non-money -> None."""
    tok = tok.strip()
    if tok in ("-", "\u2013", "\u2014", ""):
        return 0
    if _MONEY.match(tok):
        return int(tok.replace(",", ""))
    # tolerate a bare grouped-less integer just in case
    if re.fullmatch(r"\d+", tok):
        return int(tok)
    return None


def trailing_money_run(line: str) -> tuple[str, list[str]]:
    """Split a table row into (label, [money tokens]).

    Collects the maximal *trailing* run of money-or-dash tokens. Because the run
    is anchored at the end of the line, a stray dash inside a title
    (e.g. "PC's Office - Mombasa") is not captured - it is followed by a word.

    Returns the label (everything before the run) and the list of money tokens
    in left-to-right order.
    """
    toks = norm_ws(line).split(" ")
    i = len(toks)
    while i > 0 and _MONEY.match(toks[i - 1]):
        i -= 1
    label = " ".join(toks[:i]).strip()
    nums = toks[i:]
    return label, nums


# ---------------------------------------------------------------------------
# Codes
# ---------------------------------------------------------------------------

VOTE_RE = re.compile(r"\b(\d{4})\b")            # 4-digit vote number, e.g. 1017
HEAD_CODE_RE = re.compile(r"^(\d{10})\b")        # 10-digit head/project/item code
ECON_CODE_RE = re.compile(r"^(\d{7})\b")         # 7-digit economic-item code


def leading_code(line: str, ndigits: int) -> Optional[str]:
    m = re.match(rf"^(\d{{{ndigits}}})\b", norm_ws(line))
    return m.group(1) if m else None
