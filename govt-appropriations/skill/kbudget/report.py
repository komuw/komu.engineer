"""Deliverable writers.

CSV is the canonical, analysis-ready output (one file per book). Markdown is
DERIVED from the CSV so the two can never drift. Every data cell carries
provenance (book id + source page) and a `verified` flag.

A single schema maps, per column:
    internal_key  -> the key used inside the parser / validators
    csv_col       -> the analysis-friendly CSV header (descriptive, snake_case)
    md_header     -> the human header shown in Markdown (mirrors the PDF, with years)
"""
from __future__ import annotations

import csv
from pathlib import Path

# ---------------------------------------------------------------------------
# Column schemas
# ---------------------------------------------------------------------------

# DEV_VOTE_SUMMARY_I  (per-vote head-level table)
SUMMARY_SCHEMA = [
    ("approved_2025_26", "approved_estimates_2025_2026",    "Approved Estimates 2025/2026"),
    ("gross",            "gross_expenditure_2026_2027",     "Gross Expenditure 2026/2027"),
    ("aia",              "appropriations_in_aid_2026_2027", "Appropriations in Aid 2026/2027"),
    ("net",              "net_expenditure_2026_2027",       "Net Expenditure 2026/2027"),
    ("proj_2027_28",     "projected_estimates_2027_2028",   "Projected Estimates 2027/2028"),
    ("proj_2028_29",     "projected_estimates_2028_2029",   "Projected Estimates 2028/2029"),
]

# DEV_FM_TABLE_I  (front-matter summary of development expenditure & source of finance)
FM1_SCHEMA = [
    ("approved_2025_26", "approved_estimates_2025_2026",         "Net Approved 2025/2026"),
    ("gross",            "gross_estimates_2026_2027",            "Gross Estimates 2026/2027"),
    ("aia",              "appropriations_in_aid_2026_2027",      "Appropriations in Aid 2026/2027"),
    ("net",              "net_estimates_2026_2027",              "Net Estimates 2026/2027"),
    ("comp_grants",      "aia_composition_grants_2026_2027",     "AiA Composition: Grants"),
    ("comp_loans",       "aia_composition_loans_2026_2027",      "AiA Composition: Loans"),
    ("comp_local",       "aia_composition_local_2026_2027",      "AiA Composition: Local"),
    ("ext_grants",       "external_revenue_grants_2026_2027",    "External Revenue: Grants"),
    ("ext_loans",        "external_revenue_loans_2026_2027",     "External Revenue: Loans"),
]

SUMMARY_MONEY_COLS = [c for _, c, _ in SUMMARY_SCHEMA]
SUMMARY_COLUMNS = ["book", "vote", "vote_title", "row_type", "head_code", "head_title",
                   *SUMMARY_MONEY_COLS, "page", "verified"]
SUMMARY_MD_HEADERS = {c: m for _, c, m in SUMMARY_SCHEMA}

FM1_MONEY_COLS = [c for _, c, _ in FM1_SCHEMA]
FM1_COLUMNS = ["book", "row_type", "vote", "title", *FM1_MONEY_COLS, "verified"]


# ---------------------------------------------------------------------------
# Row builders (produce dicts keyed by CSV column name)
# ---------------------------------------------------------------------------

def summary_rows(book_id: str, votes: dict) -> list[dict]:
    rows = []
    for vote, rec in votes.items():
        title = rec.get("vote_title") or ""
        for h in rec["heads"]:
            v = h.get("values") or {}
            row = {"book": book_id, "vote": vote, "vote_title": title,
                   "row_type": "head", "head_code": h["code"], "head_title": h["title"],
                   "page": h.get("page", ""), "verified": ""}
            for k, c, _ in SUMMARY_SCHEMA:
                row[c] = v.get(k, "")
            rows.append(row)
        t = rec.get("total")
        if t:
            row = {"book": book_id, "vote": vote, "vote_title": title,
                   "row_type": "vote_total", "head_code": "", "head_title": "TOTAL FOR VOTE",
                   "page": rec.get("total_page", ""), "verified": ""}
            for k, c, _ in SUMMARY_SCHEMA:
                row[c] = t.get(k, "")
            rows.append(row)
    return rows


def fm1_rows(book_id: str, fm1: dict) -> list[dict]:
    rows = []
    for r in fm1["rows"]:
        v = r.get("values") or {}
        row = {"book": book_id, "row_type": "vote", "vote": r["vote"], "title": r["title"],
               "verified": ""}
        for k, c, _ in FM1_SCHEMA:
            row[c] = v.get(k, "")
        rows.append(row)
    t = fm1.get("total")
    if t:
        row = {"book": book_id, "row_type": "total", "vote": "", "title": "TOTAL VOTED EXPENDITURE",
               "verified": ""}
        for k, c, _ in FM1_SCHEMA:
            row[c] = t.get(k, "")
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})


# ---------------------------------------------------------------------------
# Markdown, DERIVED from the canonical CSV
# ---------------------------------------------------------------------------

def _fmt_money(cell: str) -> str:
    """Render a CSV money cell for display. Empty -> '' ; nil (0) -> '-' to mirror
    the PDF convention ; otherwise thousands-separated."""
    s = (cell or "").strip()
    if s == "":
        return ""
    try:
        n = int(s)
    except ValueError:
        return s
    return "-" if n == 0 else f"{n:,}"


def write_summary_markdown_from_csv(md_dir: Path, book_id: str, csv_path: Path) -> None:
    md_dir.mkdir(parents=True, exist_ok=True)
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # group by vote, preserving first-seen order
    order: list[str] = []
    by_vote: dict[str, list[dict]] = {}
    for r in rows:
        v = r["vote"]
        if v not in by_vote:
            by_vote[v] = []
            order.append(v)
        by_vote[v].append(r)

    headers = [SUMMARY_MD_HEADERS[c] for c in SUMMARY_MONEY_COLS]
    for vote in order:
        vrows = by_vote[vote]
        title = vrows[0]["vote_title"]
        n_review = sum(1 for r in vrows if r.get("verified") == "review")
        out = [f"# Vote {vote} - {title}".rstrip(), "",
               "## I. Development Expenditure Summary 2026/2027 and "
               "Projected Expenditure Estimates for 2027/2028 - 2028/2029", "",
               "| Head/Project code | Head / Project | " + " | ".join(headers) + " |",
               "|" + "---|" * (2 + len(headers))]
        for r in vrows:
            cells = [_fmt_money(r[c]) for c in SUMMARY_MONEY_COLS]
            if r["row_type"] == "vote_total":
                out.append("| | **TOTAL FOR VOTE** | "
                           + " | ".join(f"**{c}**" for c in cells) + " |")
            else:
                out.append(f"| {r['head_code']} | {r['head_title']} | "
                           + " | ".join(cells) + " |")
        out += ["", "_Nil values are shown as `-`. Figures in KShs._",
                f"_Verification: {'all rows verified' if n_review == 0 else str(n_review)+' row(s) in review'} "
                f"(cross-engine + arithmetic). Source: {book_id}._", ""]
        (md_dir / f"vote-{vote}.md").write_text("\n".join(out), encoding="utf-8")


# ---------------------------------------------------------------------------
# Validation report + review queue
# ---------------------------------------------------------------------------

def write_validation_report(path: Path, book_id: str, sections: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = [f"# Validation report - {book_id}", ""]
    for name, info in sections.items():
        out.append(f"## {name}")
        s = info["summary"]
        out.append(f"- checks: {s['n']}  passed: {s['n_ok']}  failed: {s['n_fail']}  "
                   f"pass-rate: {s['pass_rate']*100:.2f}%")
        fails = [c for c in info["checks"] if not c["ok"]]
        if fails:
            out += ["", "| check | scope | detail |", "|---|---|---|"]
            for c in fails[:500]:
                out.append(f"| {c['name']} | {c.get('scope','')} | {c.get('detail','')} |")
        out.append("")
    path.write_text("\n".join(out), encoding="utf-8")


def write_review_queue(path: Path, book_id: str, all_checks: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fails = [c for c in all_checks if not c["ok"]]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["book", "check", "scope", "page", "detail"])
        for c in fails:
            w.writerow([book_id, c["name"], c.get("scope", ""),
                        c.get("page", ""), c.get("detail", "")])
