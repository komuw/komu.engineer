"""Arithmetic validation - the fidelity engine.

Every check returns a record {name, ok, detail, ...}. A failing check never
mutates data; it simply marks a cell/row/vote for the manual-review queue.
"""
from __future__ import annotations

from typing import Optional

from .parse_dev import SUMMARY_COLS


def check(name: str, ok: bool, detail: str = "", **extra) -> dict:
    r = {"name": name, "ok": bool(ok), "detail": detail}
    r.update(extra)
    return r


# ---------------------------------------------------------------------------
# DEV_VOTE_SUMMARY
# ---------------------------------------------------------------------------

def validate_vote_summary(vote: str, rec: dict) -> list[dict]:
    checks: list[dict] = []
    heads = [h for h in rec["heads"] if h.get("values")]

    for h in heads:
        v = h["values"]
        ok = v["gross"] - v["aia"] == v["net"]
        checks.append(check(
            "gross-aia=net",
            ok,
            f"{v['gross']:,} - {v['aia']:,} = {v['gross']-v['aia']:,} vs net {v['net']:,}",
            scope=f"vote {vote} head {h['code']}", page=h.get("page")))

    t = rec.get("total")
    if t:
        # Every column must reconcile to the printed vote total. Checking all six
        # (not just gross/net) closes the gap where a row that is nil in gross/net
        # but non-zero in approved/projected could be dropped undetected.
        for key in SUMMARY_COLS:
            s = sum(h["values"][key] for h in heads)
            checks.append(check(f"sum(head {key})=total {key}", s == t[key],
                                f"{s:,} vs {t[key]:,}", scope=f"vote {vote}"))
    else:
        checks.append(check("total present", False,
                            "no TOTAL FOR VOTE row parsed", scope=f"vote {vote}"))

    for p in rec.get("problems", []):
        checks.append(check("parse", False, p, scope=f"vote {vote}"))
    return checks


# ---------------------------------------------------------------------------
# DEV_FM_TABLE_I
# ---------------------------------------------------------------------------

def validate_fm_table_i(fm1: dict) -> list[dict]:
    checks: list[dict] = []
    rows = [r for r in fm1["rows"] if r.get("values")]

    for r in rows:
        v = r["values"]
        checks.append(check("gross-aia=net", v["gross"] - v["aia"] == v["net"],
                            f"{v['gross']:,} - {v['aia']:,} vs net {v['net']:,}",
                            scope=f"fm1 vote {r['vote']}"))
        comp = v["comp_grants"] + v["comp_loans"] + v["comp_local"]
        checks.append(check("comp(grants+loans+local)=aia", comp == v["aia"],
                            f"{comp:,} vs aia {v['aia']:,}",
                            scope=f"fm1 vote {r['vote']}"))

    t = fm1.get("total")
    if t:
        for col in ("approved_2025_26", "gross", "aia", "net"):
            s = sum(r["values"][col] for r in rows)
            checks.append(check(f"sum(vote {col})=total {col}", s == t[col],
                                f"{s:,} vs {t[col]:,}", scope="fm1 total"))
    else:
        checks.append(check("total present", False,
                            "no Total Voted Expenditure row parsed", scope="fm1 total"))

    for p in fm1.get("problems", []):
        checks.append(check("parse", False, p, scope="fm1"))
    return checks


# ---------------------------------------------------------------------------
# Cross-template reconciliation: front-matter Table I vs per-vote summaries
# ---------------------------------------------------------------------------

def cross_check_fm1_vs_summary(fm1: dict, votes: dict) -> list[dict]:
    checks: list[dict] = []
    fm1_by_vote = {r["vote"]: r["values"] for r in fm1["rows"] if r.get("values")}
    for vote, rec in votes.items():
        t = rec.get("total")
        fv = fm1_by_vote.get(vote)
        if t and fv:
            checks.append(check("fm1.net == summary.total.net",
                                fv["net"] == t["net"],
                                f"fm1 {fv['net']:,} vs summary {t['net']:,}",
                                scope=f"vote {vote}"))
    return checks


def summarize(checks: list[dict]) -> dict:
    n = len(checks)
    n_ok = sum(1 for c in checks if c["ok"])
    return {"n": n, "n_ok": n_ok, "n_fail": n - n_ok,
            "pass_rate": (n_ok / n) if n else 1.0}
