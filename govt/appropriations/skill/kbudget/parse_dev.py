"""Structural parsers for the Development book's arithmetic-checkable tables.

First pass implements the two templates with the cleanest embedded identities:

  DEV_VOTE_SUMMARY_I  per-vote head-level table
     columns: approved_2025_26 | gross | aia | net | proj_2027_28 | proj_2028_29
     identities: gross - aia = net ;  sum(head net) = TOTAL FOR VOTE net

  DEV_FM_TABLE_I    front-matter summary of development expenditure
     columns: approved | gross | aia | net | comp_grants | comp_loans |
              comp_local | ext_grants | ext_loans
     identities: gross - aia = net ; comp_grants+comp_loans+comp_local = aia ;
                 sum(vote net) = Total Voted Expenditure net

Design notes
------------
* Wrapped rows: a long title (or vote name on a TOTAL line) pushes the numbers to
  the following physical line. Rows are accumulated until their numeric run appears.
* Arithmetic-guided repair: `pdftotext -table` occasionally emits one spurious
  extra column (a stray leading dash). When a row yields expected+1 tokens we try
  the two candidate windows and keep the one the accounting identity endorses -
  a self-validating disambiguation, never a blind guess. Anything not resolvable
  this way is emitted with values=None for the review queue.
"""
from __future__ import annotations

import re
from typing import Callable, Optional

from .textutil import norm_ws, trailing_money_run, to_int

SUMMARY_COLS = ["approved_2025_26", "gross", "aia", "net", "proj_2027_28", "proj_2028_29"]
FM1_COLS = ["approved_2025_26", "gross", "aia", "net",
            "comp_grants", "comp_loans", "comp_local", "ext_grants", "ext_loans"]

_VOTE_RE = re.compile(r"VOTE\s+[A-Z]?(\d{4})\b")


def _gross_aia_net(r: dict) -> bool:
    return r["gross"] - r["aia"] == r["net"]


# ---------------------------------------------------------------------------
# Row building
# ---------------------------------------------------------------------------

def _row_from_nums(nums: list[str], cols: list[str]) -> Optional[dict]:
    if len(nums) != len(cols):
        return None
    vals = {}
    for c, tok in zip(cols, nums):
        v = to_int(tok)
        if v is None:
            return None
        vals[c] = v
    return vals


def _row_repair(nums: list[str], cols: list[str],
                identity: Optional[Callable[[dict], bool]] = None) -> Optional[dict]:
    """Build a row from `nums`. Exact length -> build directly (validation is a
    separate downstream step). Length == len(cols)+1 -> pick the len(cols)-window
    that satisfies `identity`. Otherwise None (goes to review)."""
    n = len(cols)
    if len(nums) == n:
        return _row_from_nums(nums, cols)
    if len(nums) == n + 1 and identity is not None:
        for window in (nums[1:], nums[:-1]):
            r = _row_from_nums(window, cols)
            if r is not None and identity(r):
                return r
    return None


# ---------------------------------------------------------------------------
# Vote header
# ---------------------------------------------------------------------------

def _vote_from_text(text: str) -> tuple[Optional[str], Optional[str]]:
    for line in text.splitlines():
        nl = norm_ws(line)
        up = nl.upper()
        m = _VOTE_RE.search(up)
        if m and "TOTAL FOR VOTE" not in up:
            vote = m.group(1)
            title = re.sub(r".*?VOTE\s+[A-Z]?%s\b" % vote, "", nl, flags=re.I).strip()
            title = re.split(r"\b(I{1,3}\.|DEVELOPMENT|RECURRENT)\b", title)[0].strip(" .")
            return vote, (title or None)
    return None, None


def _code_and_title(nl: str, min_d: int, max_d: int | None = None) -> Optional[tuple[str, str]]:
    """Return (code, remainder) if the line starts with a code of `min_d`..`max_d`
    digits followed by whitespace then an alphabetic title. This excludes year
    headers such as '2025/2026 ...' (slash, not space). Head/project codes are
    normally 10 digits but a few are 11 (e.g. mission '10530101500 Goma - DRC'),
    so the summary parser allows a small range rather than an exact width."""
    max_d = min_d if max_d is None else max_d
    m = re.match(rf"^(\d{{{min_d},{max_d}}})\s+(.*)$", nl)
    if not m:
        return None
    code, rest = m.group(1), m.group(2)
    if not re.search(r"[A-Za-z]", rest):
        return None
    return code, rest


# ---------------------------------------------------------------------------
# DEV_VOTE_SUMMARY_I
# ---------------------------------------------------------------------------

def parse_summary_page(text: str) -> dict:
    vote, vote_title = _vote_from_text(text)
    heads: list[dict] = []
    total: Optional[dict] = None
    problems: list[str] = []
    pending: Optional[dict] = None

    def finalize(pend):
        nonlocal total
        row = _row_repair(pend["nums"], SUMMARY_COLS, _gross_aia_net)
        if pend["kind"] == "total":
            if row is not None:
                total = row
            else:
                problems.append(
                    f"TOTAL row bad column count ({len(pend['nums'])}): {pend['raw']!r}")
        else:
            heads.append({"code": pend["code"], "title": norm_ws(pend["title"]),
                          "nums": pend["nums"], "values": row})
            if row is None:
                problems.append(
                    f"head {pend['code']} bad column count ({len(pend['nums'])})")

    for raw in text.splitlines():
        nl = norm_ws(raw)
        if not nl:
            continue
        up = nl.upper()
        is_total = "TOTAL FOR VOTE" in up
        ct = None if is_total else _code_and_title(nl, 10, 11)

        if is_total or ct:
            if pending is not None:
                finalize(pending)
            label, nums = trailing_money_run(nl)
            if is_total:
                pending = {"kind": "total", "raw": nl, "nums": nums}
            else:
                code, rest = ct
                title = norm_ws(label[len(code):])
                pending = {"kind": "head", "code": code, "title": title, "nums": nums}
        else:
            if pending is None:
                continue
            label, nums = trailing_money_run(nl)
            if not pending["nums"] and nums:
                pending["nums"] = nums
                if label and pending["kind"] == "head":
                    pending["title"] = norm_ws(pending["title"] + " " + label)
            elif label and not nums and pending["kind"] == "head":
                pending["title"] = norm_ws(pending["title"] + " " + label)

    if pending is not None:
        finalize(pending)

    return {"vote": vote, "vote_title": vote_title,
            "heads": heads, "total": total, "problems": problems}


# ---------------------------------------------------------------------------
# DEV_FM_TABLE_I
# ---------------------------------------------------------------------------

def parse_fm_table_i(pages: list[str]) -> dict:
    rows: list[dict] = []
    total: Optional[dict] = None
    problems: list[str] = []
    pending: Optional[dict] = None

    def finalize(pend):
        nonlocal total
        row = _row_repair(pend["nums"], FM1_COLS, _gross_aia_net)
        if pend["kind"] == "total":
            if row is not None:
                total = row
            else:
                problems.append(f"TOTAL row bad column count ({len(pend['nums'])})")
        else:
            rows.append({"vote": pend["code"], "title": norm_ws(pend["title"]),
                         "nums": pend["nums"], "values": row})
            if row is None:
                problems.append(
                    f"vote {pend['code']} bad column count ({len(pend['nums'])})")

    for text in pages:
        for raw in text.splitlines():
            nl = norm_ws(raw)
            if not nl:
                continue
            up = nl.upper()
            is_total = up.startswith("TOTAL VOTED EXPENDITURE")
            ct = None if is_total else _code_and_title(nl, 4)

            if is_total or ct:
                if pending is not None:
                    finalize(pending)
                label, nums = trailing_money_run(nl)
                if is_total:
                    pending = {"kind": "total", "nums": nums}
                else:
                    code, rest = ct
                    title = norm_ws(label[len(code):])
                    pending = {"kind": "vote", "code": code, "title": title, "nums": nums}
            else:
                if pending is None:
                    continue
                label, nums = trailing_money_run(nl)
                if not pending["nums"] and nums:
                    pending["nums"] = nums
                    if label and pending["kind"] == "vote":
                        pending["title"] = norm_ws(pending["title"] + " " + label)
                elif label and not nums and pending["kind"] == "vote":
                    pending["title"] = norm_ws(pending["title"] + " " + label)

    if pending is not None:
        finalize(pending)

    return {"rows": rows, "total": total, "problems": problems}
