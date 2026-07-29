"""Development Table III parser - DEV_VOTE_ESTIMATES (per-project source of funding).

Per vote, for every head -> project the book lists economic items with SIX columns:

    approved 2025/26 | estimate 2026/27 | GRANTS(AiA, Revenue) | LOANS(AiA, Revenue)

then a GROSS EXPENDITURE line, an optional 'Appropriations in Aid' financing
block (5xxxxxx items), a project NET EXPENDITURE, and finally the head repeated
with its own NET EXPENDITURE.

Fidelity notes (why validation is column-scoped):
  * `-table` drops *trailing* nil cells, so a row may show <6 tokens; we right-pad
    with nil, which is correct because only trailing empties are dropped.
  * The two amount columns (approved, estimate) are clean and self-checking:
    GROSS-AiA=NET and head NET = sum(project NETs), and both cross-check to the
    already-validated Table I. These gate the `verified` flag.
  * The four external-funding columns are captured as-is; a row additionally
    passes `ext_ok` when sum(items)=GROSS across all six columns.
"""
from __future__ import annotations

import re
from typing import Optional

from .textutil import norm_ws, trailing_money_run, to_int

COLS6 = ["approved_2025_26", "est_2026_27",
         "grants_aia", "grants_revenue", "loans_aia", "loans_revenue"]
AMOUNT = ["approved_2025_26", "est_2026_27"]

_CODE_LONG = re.compile(r"^(\d{10,11})\s+(.*)$")
_CODE_ITEM = re.compile(r"^(\d{7})\s+(.*)$")


def _vals6(nums: list[str]) -> Optional[dict]:
    nums = list(nums)
    if len(nums) > 6:
        nums = nums[-6:]
    nums = nums + ["-"] * (6 - len(nums))     # right-pad dropped trailing nils
    out = {}
    for c, t in zip(COLS6, nums):
        v = to_int(t)
        if v is None:
            return None
        out[c] = v
    return out


def _sum(dicts: list[dict], cols=COLS6) -> dict:
    return {c: sum(d[c] for d in dicts if d) for c in cols}


def _eq(a: Optional[dict], b: Optional[dict], cols=AMOUNT) -> bool:
    return a is not None and b is not None and all(a[c] == b[c] for c in cols)


def parse_estimates(vote: str, pages: list[tuple[int, str]]) -> dict:
    projects: list[dict] = []   # one row per project (gross/net/aia + financing split)
    items: list[dict] = []      # economic + financing item detail
    problems: list[str] = []
    head_nets: dict[str, dict] = {}     # head_code -> reported head NET (for cross-check)

    cur_head = [None, None]
    cur_proj = [None, None]
    exp_items: list[dict] = []
    fin_items: list[dict] = []
    gross = aia = None
    seen_gross = False
    in_aia = False
    proj_nets: list[dict] = []          # project NETs of current head
    pending: Optional[dict] = None

    def flush():
        nonlocal pending
        if pending is None:
            return
        p, pending = pending, None
        vals = _vals6(p["nums"]) if p["nums"] else None
        rec = {"head_code": cur_head[0], "head_title": cur_head[1],
               "project_code": cur_proj[0], "project_title": cur_proj[1],
               "item_code": p["code"], "item_title": norm_ws(p["title"]),
               "kind": p["kind"], "values": vals, "page": p["page"]}
        items.append(rec)
        if vals is None:
            problems.append(f"item {p['code']} bad cols")
        elif p["kind"] == "financing":
            fin_items.append(vals)
        else:
            exp_items.append(vals)

    def close_project(net: Optional[dict], page: int):
        nonlocal exp_items, fin_items, gross, aia, seen_gross, in_aia
        gross_ok = _eq(_sum(exp_items), gross)
        net_expected = ({c: gross[c] - (aia[c] if aia else 0) for c in AMOUNT}
                        if gross is not None else None)
        net_ok = (net is not None and net_expected is not None
                  and all(net_expected[c] == net[c] for c in AMOUNT))
        ext_ok = _eq(_sum(exp_items), gross, cols=COLS6)
        ok = bool(gross_ok and net_ok)
        projects.append({"head_code": cur_head[0], "head_title": cur_head[1],
                         "project_code": cur_proj[0], "project_title": cur_proj[1],
                         "gross": gross, "aia": aia, "net": net,
                         "amount_ok": ok, "ext_ok": bool(ext_ok), "page": page})
        if not gross_ok:
            problems.append(f"project {cur_proj[0]}: sum(items)!=gross (amount cols)")
        if not net_ok:
            problems.append(f"project {cur_proj[0]}: gross-aia!=net (amount cols)")
        if net is not None:
            proj_nets.append(net)
        exp_items, fin_items, gross, aia, seen_gross, in_aia = [], [], None, None, False, False

    for page_num, text in pages:
        flush()
        for raw in text.splitlines():
            nl = norm_ws(raw)
            if not nl:
                continue
            up = nl.upper()

            if up.startswith("GROSS EXPENDITURE"):
                flush()
                _, nums = trailing_money_run(nl)
                gross = _vals6(nums)
                seen_gross = True
                continue
            if up.startswith("APPROPRIATIONS IN AID"):
                flush()
                _, nums = trailing_money_run(nl)
                aia = _vals6(nums) if nums else {c: 0 for c in COLS6}
                in_aia = True
                continue
            if up.startswith("NET EXPENDITURE"):
                flush()
                _, nums = trailing_money_run(nl)
                net = _vals6(nums)
                if seen_gross:
                    close_project(net, page_num)
                else:                       # head-level NET
                    if cur_head[0] is not None:
                        head_nets[cur_head[0]] = net
                    ok = _eq(_sum(proj_nets), net)
                    if not ok:
                        problems.append(f"head {cur_head[0]}: sum(project nets)!=head net")
                    proj_nets.clear()
                continue

            m = _CODE_LONG.match(nl)
            if m and re.search(r"[A-Za-z]", m.group(2)):
                flush()
                code, title = m.group(1), norm_ws(m.group(2))
                if code.endswith("00"):
                    if code != cur_head[0]:
                        cur_head = [code, title]
                        proj_nets.clear()
                    # else: closing re-declaration before head NET -> keep state
                else:
                    cur_proj = [code, title]
                    exp_items, fin_items, gross, aia, seen_gross, in_aia = [], [], None, None, False, False
                continue

            m = _CODE_ITEM.match(nl)
            if m and re.search(r"[A-Za-z]", m.group(2)):
                flush()
                label, nums = trailing_money_run(nl)
                code = m.group(1)
                if len(nums) >= 6:
                    extra, vals = nums[:-6], nums[-6:]
                    title = norm_ws((label + " " + " ".join(extra))[len(code):])
                elif nums and len(nums) >= 2:      # trailing nils dropped; still complete
                    vals, title = nums, norm_ws(label[len(code):])
                else:
                    vals, title = [], norm_ws(m.group(2))
                pending = {"code": code, "title": title,
                           "kind": "financing" if in_aia else "exp",
                           "nums": vals, "page": page_num}
                continue

            if pending is not None:
                label, nums = trailing_money_run(nl)
                if not pending["nums"] and len(nums) >= 2:
                    pending["nums"] = nums
                    if label:
                        pending["title"] = norm_ws(pending["title"] + " " + label)
                elif not nums and label:
                    pending["title"] = norm_ws(pending["title"] + " " + label)

    flush()
    return {"vote": vote, "projects": projects, "items": items,
            "head_nets": head_nets, "problems": problems}
