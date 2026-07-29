# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pdfplumber>=0.11",
#   "pyyaml>=6",
# ]
# ///
"""kbudget pipeline entrypoint.

Run with uv (self-contained; installs its own deps):
    uv run --script govt-appropriations/skill/run.py run --year-dir govt-appropriations/2026-2027
    uv run --script skill/run.py manifest --year-dir govt-appropriations/2026-2027
    uv run --script skill/run.py run      --year-dir govt-appropriations/2026-2027 --only "Development Book Volume 1"

System prerequisite: Xpdf `pdftotext` on PATH (already installed).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kbudget import manifest as M
from kbudget import extract, classify, reconcile, parse_dev, validate, report


def _out_dir(year_dir: Path) -> Path:
    return Path(year_dir) / "_out"


# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------

def cmd_manifest(args):
    year_dir = Path(args.year_dir)
    data = M.build(year_dir)
    p = M.write(year_dir, data)
    print(f"wrote {p}")
    for b in data["books"]:
        print(f"  {b['pages']:>5} pages  {b['kind']:<13} {b['filename']}")


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def _select_books(data, only, kind):
    for b in data["books"]:
        if only and only.lower() not in b["filename"].lower():
            continue
        if kind and b["kind"] != kind:
            continue
        yield b


def _collect_votes(cache, page_tmpl, summary_tmpl):
    """Group per-vote head-level summary rows across pages for the given template
    id (works for Development Table I and Recurrent Table I - same shape)."""
    votes: dict = {}
    for i, pg in enumerate(cache["pages"]):
        if page_tmpl[i] != summary_tmpl:
            continue
        r = parse_dev.parse_summary_page(pg["xpdf"])
        v = r["vote"] or "UNKNOWN"
        vd = votes.setdefault(v, {"vote_title": r["vote_title"], "heads": [],
                                  "total": None, "total_page": None, "problems": []})
        if r["vote_title"] and not vd["vote_title"]:
            vd["vote_title"] = r["vote_title"]
        for h in r["heads"]:
            h["page"] = i + 1
            vd["heads"].append(h)
        if r["total"]:
            vd["total"] = r["total"]
            vd["total_page"] = i + 1
        vd["problems"] += [f"p{i+1}: {p}" for p in r["problems"]]
    return votes


def _collect_fm1(cache, page_tmpl):
    fm1_pages = [pg["xpdf"] for i, pg in enumerate(cache["pages"])
                 if page_tmpl[i] == classify.FM_TABLE_I]
    return parse_dev.parse_fm_table_i(fm1_pages)


def cmd_run(args):
    year_dir = Path(args.year_dir)
    out = _out_dir(year_dir)
    data = M.load(year_dir)

    problems = M.verify(year_dir)
    if problems:
        print("MANIFEST VERIFY FAILED:")
        for p in problems:
            print("  ", p)
        if not args.force:
            sys.exit(2)

    for b in _select_books(data, args.only, args.kind):
        pdf = year_dir / b["filename"]
        print(f"\n=== {b['id']} ({b['pages']} pages, {b['kind']}) ===")

        cache = extract.extract_book(pdf, out, b["id"], b["sha256"], force=args.force_extract)
        for w in cache.get("warnings", []):
            print("  warn:", w)

        page_tmpl = [classify.classify(pg["xpdf"]) for pg in cache["pages"]]

        # --- universal cross-engine reconciliation ---
        rec = reconcile.reconcile_book(cache)
        n = cache["npages"]
        hard_pages = {m["page"] for m in rec["mismatches"]}
        seg_pages = set(rec["segmentation_pages"])
        # strict-match pages only, used for the gold-standard `verified` gate
        rec_ok_pages = set(range(1, n + 1)) - hard_pages - seg_pages
        print(f"  reconciliation: {rec['n_match']}/{n} numeric-identical "
              f"({rec['strict_coverage']*100:.2f}%); {rec['n_segmentation']} segmentation-only "
              f"(benign, same digits); {rec['n_mismatch']} hard mismatch "
              f"[digit-coverage {rec['digit_coverage']*100:.2f}%]")

        # Only a real digit-level mismatch is a failure (-> review queue). A
        # segmentation-only page is benign (identical digits) and passes with a note.
        recon_checks = []
        for p in range(1, n + 1):
            if p in hard_pages:
                ok, detail = False, "xpdf/pdfplumber DIGIT content differs (real)"
            elif p in seg_pages:
                ok, detail = True, "segmentation-only: identical digits, different token boundaries"
            else:
                ok, detail = True, ""
            recon_checks.append({"name": "cross-engine numbers", "ok": ok,
                                 "scope": f"page {p}", "page": p, "detail": detail})

        sections = {"reconciliation": {"checks": recon_checks,
                                       "summary": validate.summarize(recon_checks)}}
        all_checks = list(recon_checks)
        rows = []

        if b["kind"] in ("development", "recurrent"):
            summary_tmpl = (classify.DEV_VOTE_SUMMARY_I if b["kind"] == "development"
                            else classify.REC_VOTE_SUMMARY_I)
            votes = _collect_votes(cache, page_tmpl, summary_tmpl)

            sum_checks = []
            for vote, vrec in votes.items():
                sum_checks += validate.validate_vote_summary(vote, vrec)
            sections["VOTE_SUMMARY_I"] = {"checks": sum_checks,
                                          "summary": validate.summarize(sum_checks)}
            all_checks += sum_checks

            # --- verified flag ---
            # A vote's totals reconcile only if EVERY per-column sum check passes
            # AND the vote actually has a parsed TOTAL row.
            head_ok = {c["scope"]: c["ok"] for c in sum_checks
                       if c["name"] == "gross-aia=net"}
            vote_total_ok = {v: (rec.get("total") is not None) for v, rec in votes.items()}
            for c in sum_checks:
                if c["name"].startswith("sum(head "):
                    v = c["scope"].split()[-1]
                    vote_total_ok[v] = vote_total_ok.get(v, True) and c["ok"]

            rows = report.summary_rows(b["id"], votes)
            for row in rows:
                page_ok = (str(row["page"]).isdigit()
                           and int(row["page"]) in rec_ok_pages)
                if row["row_type"] == "vote_total":
                    ok = vote_total_ok.get(row["vote"], False) and page_ok
                else:
                    scope = f"vote {row['vote']} head {row['head_code']}"
                    ok = (head_ok.get(scope, False)
                          and vote_total_ok.get(row["vote"], False) and page_ok)
                row["verified"] = "yes" if ok else "review"

            # CSV is canonical; Markdown is derived from it.
            summary_csv = out / "dataset" / f"{b['id']}_summary.csv"
            report.write_csv(summary_csv, rows, report.SUMMARY_COLUMNS)
            report.write_summary_markdown_from_csv(out / "markdown" / b["id"], b["id"], summary_csv)

            head_rows = [r for r in rows if r["row_type"] == "head"]
            n_ver = sum(1 for r in head_rows if r["verified"] == "yes")
            print(f"  VOTE_SUMMARY (Table I): {len(votes)} votes, {len(head_rows)} head rows, "
                  f"{n_ver} verified ({(n_ver/len(head_rows)*100) if head_rows else 0:.1f}%)")

            # development additionally has the front-matter Table I
            if b["kind"] == "development":
                fm1 = _collect_fm1(cache, page_tmpl)
                fm1_checks = validate.validate_fm_table_i(fm1)
                cross = validate.cross_check_fm1_vs_summary(fm1, votes)
                sections["DEV_FM_TABLE_I"] = {"checks": fm1_checks,
                                              "summary": validate.summarize(fm1_checks)}
                sections["cross_check_fm1_vs_summary"] = {"checks": cross,
                                                          "summary": validate.summarize(cross)}
                all_checks += fm1_checks + cross

                fm1_ready = report.fm1_rows(b["id"], fm1)
                fm1_bad = {r["vote"] for r in fm1["rows"] if r["values"] is None}
                for row in fm1_ready:
                    row["verified"] = "review" if (row["row_type"] == "vote"
                                                   and row["vote"] in fm1_bad) else "yes"
                report.write_csv(out / "dataset" / f"{b['id']}_fm_table_i.csv",
                                 fm1_ready, report.FM1_COLUMNS)
                print(f"  DEV_FM_TABLE_I:   {len([r for r in fm1['rows'] if r['values']])} vote rows, "
                      f"pass-rate {sections['DEV_FM_TABLE_I']['summary']['pass_rate']*100:.1f}%")
                print(f"  cross-check:      pass-rate "
                      f"{sections['cross_check_fm1_vs_summary']['summary']['pass_rate']*100:.1f}%")
        else:
            print(f"  (structural parsing for '{b['kind']}' not in first pass; "
                  f"reconciliation only)")

        report.write_validation_report(out / "reports" / f"{b['id']}.md", b["id"], sections)
        report.write_review_queue(out / "review-queue" / f"{b['id']}.csv", b["id"], all_checks)

        n_fail = sum(1 for c in all_checks if not c["ok"])
        print(f"  review queue: {n_fail} items -> {out / 'review-queue' / (b['id']+'.csv')}")


def main():
    ap = argparse.ArgumentParser(prog="kbudget")
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("manifest", help="build manifest.yaml for a year folder")
    m.add_argument("--year-dir", required=True)
    m.set_defaults(func=cmd_manifest)

    r = sub.add_parser("run", help="extract + reconcile + parse + validate")
    r.add_argument("--year-dir", required=True)
    r.add_argument("--only", default=None, help="substring filter on filename")
    r.add_argument("--kind", default=None,
                   choices=["development", "recurrent", "program-based"])
    r.add_argument("--force", action="store_true", help="ignore checksum drift")
    r.add_argument("--force-extract", action="store_true", help="ignore extraction cache")
    r.set_defaults(func=cmd_run)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
