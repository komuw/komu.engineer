"""Recurrent Table II parser - the item-level (economic) detail.

Per vote the table is a 3-level hierarchy:

    HEAD              (10/11-digit code ending in '00', title only)
      SUB-HEAD        (10/11-digit code, title only)
        item          (7-digit economic code + 4 figures)      <- expenditure
        ...
        Gross Expenditure ................ KShs.  <4 figures>   (= sum of items)
        Appropriations in Aid                                    (section header)
        aia-item      (7-digit code + 4 figures)                <- appropriations in aid
        Net Expenditure .. Sub-Head ...... KShs.  <4 figures>   (= gross - sum aia)
      Net Expenditure Head ............... KShs.  <4 figures>   (= sum sub-head nets)
    TOTAL NET EXPENDITURE FOR VOTE ....... KShs.  <4 figures>   (= sum head nets)

Columns are 4: approved 2025/26, estimates 2026/27, and two projections. The
embedded identities (sum of items = gross; gross - aia = net; sub-head nets sum
to head net; head nets sum to the vote total) are what validate the extraction.
"""
from __future__ import annotations

import re
from typing import Optional

from .textutil import norm_ws, trailing_money_run, to_int

COLS4 = ["approved_2025_26", "est_2026_27", "est_2027_28", "est_2028_29"]

_CODE_LONG = re.compile(r"^(\d{10,11})\s+(.*)$")   # head / sub-head
_CODE_ITEM = re.compile(r"^(\d{7})\s+(.*)$")        # economic item


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
    return {c: sum(d[c] for d in dicts) for c in COLS4}


def _eq(a: Optional[dict], b: Optional[dict]) -> bool:
    return a is not None and b is not None and all(a[c] == b[c] for c in COLS4)


def parse_table_ii(vote: str, pages: list[tuple[int, str]]) -> dict:
    items: list[dict] = []
    problems: list[str] = []
    subhead_ok: dict[str, bool] = {}
    head_ok: dict[str, bool] = {}
    total: Optional[dict] = None
    total_ok = False

    cur_head = [None, None]     # code, title
    cur_sub = [None, None]
    in_aia = False
    sub_exp: list[dict] = []
    sub_aia: list[dict] = []
    sub_gross: Optional[dict] = None
    head_subnets: list[dict] = []
    vote_headnets: list[dict] = []
    pending: Optional[dict] = None
    # head attribution is resolved via sub-heads, because a mission's HEAD line may
    # appear either before its sub-head (normal) or after it (single-sub-head
    # missions, e.g. '10530101500 Goma - DRC'). Sub-heads seen since the last head
    # close are mapped to the head when 'Net Expenditure Head' is reached.
    pending_subheads: list[str] = []
    subhead_to_head: dict[str, str] = {}
    head_title_map: dict[str, str] = {}

    def flush():
        nonlocal pending, total
        if pending is None:
            return
        p, pending = pending, None
        if p["kind"] == "item":
            vals = _vals(p["nums"])
            items.append({"head_code": None, "head_title": None,
                          "subhead_code": cur_sub[0], "subhead_title": cur_sub[1],
                          "item_code": p["code"], "item_title": norm_ws(p["title"]),
                          "kind": p["item_kind"], "values": vals, "page": p["page"]})
            if vals is None:
                problems.append(f"item {p['code']} bad cols ({len(p['nums'])})")
            elif p["item_kind"] == "aia":
                sub_aia.append(vals)
            else:
                sub_exp.append(vals)
        elif p["kind"] == "total":
            total = _vals(p["nums"])
            if total is None:
                problems.append(f"vote total bad cols ({len(p['nums'])})")

    for page_num, text in pages:
        flush()  # items/totals do not wrap across page boundaries
        for raw in text.splitlines():
            nl = norm_ws(raw)
            if not nl:
                continue
            up = nl.upper()

            # --- structural / subtotal lines ---
            if "TOTAL NET EXPENDITURE FOR VOTE" in up:
                flush()
                _, nums = trailing_money_run(nl)
                pending = {"kind": "total", "nums": nums}
                continue
            if "GROSS EXPENDITURE" in up:
                flush()
                _, nums = trailing_money_run(nl)
                sub_gross = _vals(nums)
                continue
            if "APPROPRIATIONS IN AID" in up and not _CODE_ITEM.match(nl):
                flush()
                in_aia = True
                continue
            if "NET EXPENDITURE" in up and "SUB-HEAD" in up:
                flush()
                _, nums = trailing_money_run(nl)
                net = _vals(nums)
                gross_ok = _eq(_sum(sub_exp), sub_gross)
                net_expected = ({c: sub_gross[c] - _sum(sub_aia)[c] for c in COLS4}
                                if sub_gross is not None else None)
                net_ok = _eq(net_expected, net)
                if cur_sub[0] is not None:
                    subhead_ok[cur_sub[0]] = bool(gross_ok and net_ok)
                if not gross_ok:
                    problems.append(f"subhead {cur_sub[0]}: sum(items) != gross")
                if not net_ok:
                    problems.append(f"subhead {cur_sub[0]}: gross-aia != net")
                if net is not None:
                    head_subnets.append(net)
                sub_exp, sub_aia, sub_gross, in_aia = [], [], None, False
                continue
            if "NET EXPENDITURE" in up and "HEAD" in up:
                flush()
                _, nums = trailing_money_run(nl)
                hnet = _vals(nums)
                ok = _eq(_sum(head_subnets), hnet)
                if cur_head[0] is not None:
                    head_ok[cur_head[0]] = bool(ok)
                    head_title_map[cur_head[0]] = cur_head[1]
                    for sh in pending_subheads:
                        subhead_to_head[sh] = cur_head[0]
                if not ok:
                    problems.append(f"head {cur_head[0]}: sum(subhead nets) != head net")
                if hnet is not None:
                    vote_headnets.append(hnet)
                head_subnets = []
                pending_subheads = []
                continue

            # --- code lines ---
            m = _CODE_LONG.match(nl)
            if m and re.search(r"[A-Za-z]", m.group(2)):
                flush()
                code, title = m.group(1), norm_ws(m.group(2))
                if code.endswith("00"):
                    cur_head = [code, title]
                    cur_sub = [None, None]
                else:
                    cur_sub = [code, title]
                    pending_subheads.append(code)
                continue
            m = _CODE_ITEM.match(nl)
            if m and re.search(r"[A-Za-z]", m.group(2)):
                flush()
                label, nums = trailing_money_run(nl)
                code = m.group(1)
                if len(nums) >= 4:                       # complete item line
                    extra, vals = nums[:-4], nums[-4:]
                    title = norm_ws((label + " " + " ".join(extra))[len(code):])
                else:                                    # title only; values wrap to next line
                    vals, title = [], norm_ws(m.group(2))
                if cur_sub[0] is None:                    # items directly under a head
                    cur_sub = list(cur_head)
                pending = {"kind": "item", "code": code, "title": title,
                           "item_kind": "aia" if in_aia else "exp",
                           "nums": vals, "page": page_num}
                continue

            # --- continuation (wrapped title, or numbers on the next line) ---
            if pending is not None:
                label, nums = trailing_money_run(nl)
                if not pending["nums"] and len(nums) >= 4:
                    pending["nums"] = nums[-4:]
                    extra = (label + " " + " ".join(nums[:-4])).strip()
                    if extra:
                        pending["title"] = norm_ws(pending.get("title", "") + " " + extra)
                elif len(nums) < 4 and label:
                    pending["title"] = norm_ws(pending.get("title", "") + " " + label)

    flush()
    total_ok = _eq(_sum(vote_headnets), total)

    # resolve each item's head from its sub-head (order-independent attribution)
    for it in items:
        sh = it["subhead_code"]
        hc = subhead_to_head.get(sh, sh)
        it["head_code"] = hc
        it["head_title"] = head_title_map.get(hc, it["subhead_title"])

    return {"vote": vote, "items": items, "subhead_ok": subhead_ok,
            "head_ok": head_ok, "total": total, "total_ok": total_ok,
            "problems": problems}


# ---------------------------------------------------------------------------
# REC_FM - recurrent front-matter "Summary of Recurrent Expenditure" (6 columns)
# ---------------------------------------------------------------------------
FM_COLS = ["gross_approved_2025_26", "aia_2025_26", "net_approved_2025_26",
           "gross_est_2026_27", "aia_2026_27", "net_est_2026_27"]


def _fmvals(nums: list[str]):
    nums = list(nums)
    if len(nums) < 6:
        return None
    nums = nums[-6:]
    out = {}
    for c, t in zip(FM_COLS, nums):
        v = to_int(t)
        if v is None:
            return None
        out[c] = v
    return out


def parse_fm(pages: list[str]) -> dict:
    """Whole-government recurrent summary: 87 vote rows + Consolidated Fund Services
    items, with nested totals (voted, CFS, grand). gross - aia = net per row, and
    votes + CFS = grand total."""
    rows: list[dict] = []
    checks: list[dict] = []
    problems: list[str] = []
    totals: dict = {}          # 'voted' | 'cfs' | 'grand'
    pending = None

    def flush():
        nonlocal pending
        if pending is None:
            return
        p, pending = pending, None
        vals = _fmvals(p["nums"])
        if p["kind"] in ("voted", "cfs_total", "grand"):
            totals[{"voted": "voted", "cfs_total": "cfs", "grand": "grand"}[p["kind"]]] = vals
            rows.append({"row_type": p["kind"], "code": "", "title": p["title"],
                         "values": vals, "page": p["page"]})
            return
        rows.append({"row_type": p["kind"], "code": p["code"], "title": norm_ws(p["title"]),
                     "values": vals, "page": p["page"]})
        if vals is None:
            problems.append(f"{p['kind']} {p['code']}: bad column count")
            return
        ok = (vals["gross_approved_2025_26"] - vals["aia_2025_26"] == vals["net_approved_2025_26"]
              and vals["gross_est_2026_27"] - vals["aia_2026_27"] == vals["net_est_2026_27"])
        checks.append({"name": "gross - aia = net", "ok": ok,
                       "scope": f"{p['kind']} {p['code']}", "detail": ""})
        if not ok:
            problems.append(f"{p['kind']} {p['code']}: gross-aia!=net")

    def _start(kind, code, title, nums, page):
        nonlocal pending
        if len(nums) >= 6:
            title = norm_ws((title + " " + " ".join(nums[:-6])).strip())
            nums = nums[-6:]
        else:
            nums = []
        pending = {"kind": kind, "code": code, "title": title, "nums": nums, "page": page}

    for page_idx, text in enumerate(pages):
        flush()
        for raw in text.splitlines():
            nl = norm_ws(raw)
            if not nl:
                continue
            up = nl.upper()
            if "TOTAL VOTED" in up:
                flush(); _, nums = trailing_money_run(nl)
                _start("voted", "", "TOTAL VOTED EXPENDITURE", nums, page_idx + 1); continue
            if "TOTAL CONSOLIDATED FUND" in up:
                flush(); _, nums = trailing_money_run(nl)
                _start("cfs_total", "", "TOTAL CONSOLIDATED FUND SERVICES", nums, page_idx + 1); continue
            if "GRAND TOTAL" in up:
                flush(); _, nums = trailing_money_run(nl)
                _start("grand", "", "GRAND TOTAL", nums, page_idx + 1); continue
            m = re.match(r"^(\d{4})\s+([A-Za-z].*)$", nl)
            if m:
                flush(); label, nums = trailing_money_run(nl)
                _start("vote", m.group(1), m.group(2), nums, page_idx + 1); continue
            m = re.match(r"^\((\w{1,4})\)\s+([A-Za-z].*)$", nl)      # CFS item "(i) Public Debt ..."
            if m:
                flush(); label, nums = trailing_money_run(nl)
                _start("cfs", m.group(1), m.group(2), nums, page_idx + 1); continue
            if pending is not None:
                label, nums = trailing_money_run(nl)
                if not pending["nums"] and len(nums) >= 6:
                    pending["nums"] = nums[-6:]
                elif len(nums) < 6 and label:
                    pending["title"] = norm_ws(pending.get("title", "") + " " + label)

    flush()

    def _sumrows(rt):
        return {c: sum(r["values"][c] for r in rows if r["row_type"] == rt and r["values"])
                for c in FM_COLS}
    if totals.get("voted"):
        s = _sumrows("vote")
        checks.append({"name": "votes sum to TOTAL VOTED", "scope": "TOTAL VOTED", "detail": "",
                       "ok": all(s[c] == totals["voted"][c] for c in FM_COLS)})
    if totals.get("cfs"):
        s = _sumrows("cfs")
        checks.append({"name": "CFS items sum to TOTAL CFS", "scope": "TOTAL CFS", "detail": "",
                       "ok": all(s[c] == totals["cfs"][c] for c in FM_COLS)})
    if totals.get("voted") and totals.get("cfs") and totals.get("grand"):
        checks.append({"name": "voted + CFS = grand total", "scope": "GRAND TOTAL", "detail": "",
                       "ok": all(totals["voted"][c] + totals["cfs"][c] == totals["grand"][c]
                                 for c in FM_COLS)})
    return {"rows": rows, "totals": totals, "checks": checks, "problems": problems}
