"""Program-based book - PART H parser (expenditure by programme & economic class).

PART H repeats, per vote, a block for every programme / sub-programme:

    <vote>  <vote title>
    PART H: Summary of Expenditure by Vote and Economic Classification ...
    <programme code>  <programme title>          (7-digit, NOT ending 00000)
    Current Expenditure                <4 figures>   (= sum of its economic rows)
      2100000 Compensation to Employees <4 figures>
      2200000 Use of Goods and Services <4 figures>
      ...
    Capital Expenditure                <4 figures>   (= sum of its economic rows)
      3100000 Non Financial Assets     <4 figures>
      ...
    Total Expenditure                  <4 figures>   (= Current + Capital)

Columns are 4: baseline 2025/26, estimates 2026/27, and two projections. Economic
classification codes end in '00000'; programme / sub-programme codes do not
(a sub-programme rollup ends in '000', e.g. 0603000 vs sub-programme 0603010).

The whole book is scanned in order, tracking the current PART, vote and programme,
because continuation pages do not always repeat the 'PART H:' banner. Identities
(section = sum of rows; Total = Current + Capital) validate the extraction.
"""
from __future__ import annotations

import re
from typing import Optional

from .textutil import norm_ws, trailing_money_run, to_int

COLS4 = ["baseline_2025_26", "est_2026_27", "est_2027_28", "est_2028_29"]

_ECON = re.compile(r"^([234]\d00000)\s+(.*)$")   # economic classification row
_CODE7 = re.compile(r"^(\d{7})\s+(.*)$")          # any 7-digit code
_VOTEHDR = re.compile(r"^(\d{4})\s+([A-Za-z].*)$")  # vote header line
_PARTHDR = re.compile(r"^PART\s+([A-Z])\s*:")


def _vals(nums: list[str]) -> Optional[dict]:
    if len(nums) != 4:
        return None
    out = {}
    for c, t in zip(COLS4, nums):
        v = to_int(t)
        if v is None:
            return None
        out[c] = v
    return out


def _sum(dicts: list[dict]) -> dict:
    return {c: sum(d["values"][c] for d in dicts if d["values"]) for c in COLS4}


def _eq(a: Optional[dict], b: Optional[dict]) -> bool:
    return a is not None and b is not None and all(a[c] == b[c] for c in COLS4)


def _add(a: Optional[dict], b: Optional[dict]) -> dict:
    a = a or {c: 0 for c in COLS4}
    b = b or {c: 0 for c in COLS4}
    return {c: a[c] + b[c] for c in COLS4}


def parse_part_h(pages: list[str]) -> dict:
    return parse_econ(pages, "PART H")


def parse_part_g(pages: list[str]) -> dict:
    return parse_econ(pages, "PART G")


def parse_econ(pages: list[str], target: str = "PART H") -> dict:
    """Parse PART H (programme x economic class) or PART G (vote x economic class).

    Both share the Current/econ-rows/Capital/econ-rows/Total block structure. In
    PART H a block is opened by a programme header; in PART G there is no programme
    header, so the vote itself is the block (prog_level = 'vote')."""
    programme_mode = (target == "PART H")
    rows: list[dict] = []
    checks: list[dict] = []
    problems: list[str] = []

    part = vote = vtitle = None
    prog_code = prog_title = None
    section: Optional[str] = None
    cur_total = cap_total = None
    cur_rows: list[dict] = []
    cap_rows: list[dict] = []
    block_rows: list[dict] = []
    block_page = None
    pending: Optional[dict] = None

    def prog_level(code: Optional[str]) -> str:
        if not programme_mode:
            return "vote"
        return "programme" if (code and code.endswith("000")) else "subprogramme"

    def flush_pending():
        nonlocal pending
        if pending is None:
            return
        p, pending = pending, None
        rec = {"section": section, "econ_code": p["code"],
               "econ_title": norm_ws(p["title"]), "values": _vals(p["nums"]),
               "page": p["page"]}
        block_rows.append(rec)
        (cur_rows if section == "current" else cap_rows).append(rec)
        if rec["values"] is None:
            problems.append(f"vote {vote} prog {prog_code} econ {p['code']} bad cols")

    def finalize(grand: Optional[dict], page: int):
        nonlocal cur_total, cap_total, cur_rows, cap_rows, block_rows, section
        if prog_code is None:
            cur_total = cap_total = None
            cur_rows, cap_rows, block_rows, section = [], [], [], None
            return
        cur_ok = _eq(_sum(cur_rows), cur_total) if cur_total is not None else (not cur_rows)
        cap_ok = _eq(_sum(cap_rows), cap_total) if cap_total is not None else (not cap_rows)
        tot_ok = _eq(_add(cur_total, cap_total), grand)
        block_ok = bool(cur_ok and cap_ok and tot_ok)
        scope = f"vote {vote} prog {prog_code}"
        checks.append({"name": "programme block reconciles", "ok": block_ok,
                       "scope": scope, "detail": "" if block_ok else "section/total mismatch"})
        for rec in block_rows:
            rows.append({"vote": vote, "vote_title": vtitle or "",
                         "programme_code": prog_code, "programme_title": prog_title or "",
                         "prog_level": prog_level(prog_code), "section": rec["section"],
                         "econ_code": rec["econ_code"], "econ_title": rec["econ_title"],
                         "row_type": "econ", "values": rec["values"], "page": rec["page"],
                         "block_ok": block_ok})
        for lbl, tot in (("current", cur_total), ("capital", cap_total), ("total", grand)):
            if tot is not None:
                rows.append({"vote": vote, "vote_title": vtitle or "",
                             "programme_code": prog_code, "programme_title": prog_title or "",
                             "prog_level": prog_level(prog_code), "section": lbl,
                             "econ_code": "", "econ_title": lbl.title() + " Expenditure",
                             "row_type": lbl if lbl == "total" else lbl + "_total",
                             "values": tot, "page": page, "block_ok": block_ok})
        cur_total = cap_total = None
        cur_rows, cap_rows, block_rows, section = [], [], [], None

    for page_idx, text in enumerate(pages):
        page_num = page_idx + 1
        flush_pending()
        for raw in text.splitlines():
            nl = norm_ws(raw)
            if not nl:
                continue
            up = nl.upper()

            mp = _PARTHDR.match(up)
            if mp:
                part = "PART " + mp.group(1)
                continue
            mv = _VOTEHDR.match(nl)
            if mv and "EXPENDITURE" not in up:
                flush_pending()
                if not programme_mode and (cur_total or cap_total or block_rows):
                    finalize(None, page_num)
                vote, vtitle = mv.group(1), norm_ws(mv.group(2))
                if not programme_mode:              # PART G: the vote is the block
                    prog_code, prog_title = vote, vtitle
                continue
            if part != target:
                continue

            if up.startswith("CURRENT EXPENDITURE"):
                flush_pending()
                _, nums = trailing_money_run(nl)
                cur_total = _vals(nums[-4:]) if len(nums) >= 4 else None
                section = "current"
                continue
            if up.startswith("CAPITAL EXPENDITURE"):
                flush_pending()
                _, nums = trailing_money_run(nl)
                cap_total = _vals(nums[-4:]) if len(nums) >= 4 else None
                section = "capital"
                continue
            if up.startswith("TOTAL EXPENDITURE"):
                flush_pending()
                _, nums = trailing_money_run(nl)
                finalize(_vals(nums[-4:]) if len(nums) >= 4 else None, page_num)
                continue

            m = _ECON.match(nl)
            if m:
                flush_pending()
                label, nums = trailing_money_run(nl)
                code = m.group(1)
                if len(nums) >= 4:
                    title = norm_ws((label + " " + " ".join(nums[:-4]))[len(code):])
                    nums = nums[-4:]
                else:
                    title, nums = norm_ws(m.group(2)), []
                pending = {"code": code, "title": title, "nums": nums, "page": page_num}
                continue

            m = _CODE7.match(nl)
            if programme_mode and m and re.search(r"[A-Za-z]", m.group(2)):
                flush_pending()
                code = m.group(1)
                if code == prog_code:
                    continue                      # repeated header on a continuation page
                if prog_code is not None and (cur_total or cap_total or block_rows):
                    finalize(None, page_num)      # close an unfinished block (rare)
                prog_code, prog_title = code, norm_ws(m.group(2))
                continue

            # continuation (wrapped econ title, or its numbers on the next line)
            if pending is not None:
                label, nums = trailing_money_run(nl)
                if not pending["nums"] and len(nums) >= 4:
                    pending["nums"] = nums[-4:]
                    extra = (label + " " + " ".join(nums[:-4])).strip()
                    if extra:
                        pending["title"] = norm_ws(pending["title"] + " " + extra)
                elif len(nums) < 4 and label:
                    pending["title"] = norm_ws(pending["title"] + " " + label)

    flush_pending()
    return {"rows": rows, "checks": checks, "problems": problems}


# ---------------------------------------------------------------------------
# PART F - summary of expenditure by programmes (programme totals, 4 columns)
# ---------------------------------------------------------------------------
def parse_part_f(pages: list[str]) -> dict:
    rows: list[dict] = []
    checks: list[dict] = []
    problems: list[str] = []
    part = vote = vtitle = None
    prog_rows: list[dict] = []      # programme rows of the current vote
    pending = None

    def prog_level(code: str) -> str:
        return "programme" if code.endswith("000") else "subprogramme"

    def flush():
        nonlocal pending, prog_rows
        if pending is None:
            return
        p, pending = pending, None
        vals = _vals(p["nums"][-4:]) if len(p["nums"]) >= 4 else None
        if p["kind"] == "total":
            rollups = [r for r in prog_rows if r["values"] and r["programme_code"].endswith("000")]
            s = {c: sum(r["values"][c] for r in rollups) for c in COLS4}
            ok = vals is not None and all(s[c] == vals[c] for c in COLS4)
            checks.append({"name": "programme rollups = vote total", "ok": ok,
                           "scope": f"vote {p['vote']}", "detail": ""})
            if not ok:
                problems.append(f"vote {p['vote']}: sum(programme rollups) != vote total")
            rows.append({"vote": p["vote"], "vote_title": vtitle or "", "programme_code": "",
                         "programme_title": "", "prog_level": "vote", "section": "",
                         "row_type": "vote_total", "econ_code": "", "econ_title": "Total Expenditure",
                         "values": vals, "page": p["page"]})
            prog_rows = []
            return
        rec = {"vote": vote, "vote_title": vtitle or "", "programme_code": p["code"],
               "programme_title": norm_ws(p["title"]), "prog_level": prog_level(p["code"]),
               "section": "", "row_type": "programme", "econ_code": "", "econ_title": "",
               "values": vals, "page": p["page"]}
        rows.append(rec)
        if vals is None:
            problems.append(f"vote {vote} programme {p['code']}: bad cols")
        else:
            prog_rows.append(rec)

    for page_idx, text in enumerate(pages):
        page_num = page_idx + 1
        flush()
        for raw in text.splitlines():
            nl = norm_ws(raw)
            if not nl:
                continue
            up = nl.upper()
            mp = _PARTHDR.match(up)
            if mp:
                part = "PART " + mp.group(1)
                continue
            if "TOTAL EXPENDITURE FOR VOTE" in up:
                flush()
                mvt = re.search(r"FOR VOTE\s+(\d{4})", up)
                if mvt:
                    vote = mvt.group(1)
                _, nums = trailing_money_run(nl)
                pending = {"kind": "total", "vote": vote, "nums": nums, "page": page_num}
                continue
            mv = re.match(r"^VOTE\s+(\d{4})\s+([A-Za-z].*)$", nl, re.I)
            if mv:
                flush()
                vote, vtitle = mv.group(1), norm_ws(mv.group(2))
                continue
            if part != "PART F":
                continue
            m = _CODE7.match(nl)
            if m and re.search(r"[A-Za-z]", m.group(2)):
                flush()
                label, nums = trailing_money_run(nl)
                code = m.group(1)
                if len(nums) >= 4:
                    title = norm_ws((label + " " + " ".join(nums[:-4]))[len(code):])
                    nums = nums[-4:]
                else:
                    title, nums = norm_ws(m.group(2)), []
                pending = {"kind": "prog", "code": code, "title": title,
                           "nums": nums, "page": page_num}
                continue
            if pending is not None:
                label, nums = trailing_money_run(nl)
                if not pending["nums"] and len(nums) >= 4:
                    pending["nums"] = nums[-4:]
                    extra = (label + " " + " ".join(nums[:-4])).strip()
                    if extra and pending["kind"] == "prog":
                        pending["title"] = norm_ws(pending.get("title", "") + " " + extra)
                elif len(nums) < 4 and label and pending["kind"] == "prog":
                    pending["title"] = norm_ws(pending.get("title", "") + " " + label)

    flush()
    return {"rows": rows, "checks": checks, "problems": problems}