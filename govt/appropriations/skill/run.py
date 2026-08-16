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
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kbudget import manifest as M
from kbudget import extract, classify, reconcile, parse_dev, parse_rec, parse_pb, parse_dev_est, validate, report


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


_VOTE_HDR = re.compile(r"VOTE\s+[A-Z]?(\d{4})\b")


def _collect_rec_items(cache, page_tmpl, tmpl=None):
    """Group Table II pages (recurrent or development) by vote and parse each."""
    tmpl = tmpl or classify.REC_VOTE_SUMMARY_II
    by_vote: dict = {}
    for i, pg in enumerate(cache["pages"]):
        if page_tmpl[i] != tmpl:
            continue
        m = _VOTE_HDR.search(re.sub(r"\s+", " ", pg["xpdf"]).upper())
        v = m.group(1) if m else "UNKNOWN"
        by_vote.setdefault(v, []).append((i + 1, pg["xpdf"]))
    return [parse_rec.parse_table_ii(v, pgs) for v, pgs in by_vote.items()]


def _collect_dev_estimates(cache, page_tmpl):
    """Group Development Table III pages by vote and parse each into project detail."""
    by_vote: dict = {}
    for i, pg in enumerate(cache["pages"]):
        if page_tmpl[i] != classify.DEV_VOTE_ESTIMATES:
            continue
        m = _VOTE_HDR.search(re.sub(r"\s+", " ", pg["xpdf"]).upper())
        v = m.group(1) if m else "UNKNOWN"
        by_vote.setdefault(v, []).append((i + 1, pg["xpdf"]))
    return [parse_dev_est.parse_estimates(v, pgs) for v, pgs in by_vote.items()]


def _emit_table_ii(book_id, results, vt_by_vote, digit_ok_pages, out, csv_name):
    """Build item rows + checks for a Table II (recurrent or development) and write CSV."""
    checks = []
    item_rows_all = []
    fc = report.ITEM_MONEY_COLS[0]
    for res in results:
        v = res["vote"]
        for code, ok in res["subhead_ok"].items():
            checks.append({"name": "subhead reconciles", "ok": ok,
                           "scope": f"vote {v} subhead {code}", "detail": ""})
        for code, ok in res["head_ok"].items():
            checks.append({"name": "head reconciles", "ok": ok,
                           "scope": f"vote {v} head {code}", "detail": ""})
        checks.append({"name": "vote total (Table II)", "ok": res["total_ok"],
                       "scope": f"vote {v}", "detail": ""})
        for p in res["problems"]:
            checks.append({"name": "parse", "ok": False, "scope": f"vote {v}", "detail": p})
        rows = report.item_rows(book_id, vt_by_vote.get(v, ""), res)
        for row in rows:
            page_ok = str(row["page"]).isdigit() and int(row["page"]) in digit_ok_pages
            ok = (res["subhead_ok"].get(row["subhead_code"], False)
                  and res["head_ok"].get(row["head_code"], False)
                  and res["total_ok"] and page_ok and row[fc] != "")
            row["verified"] = "yes" if ok else "review"
        item_rows_all += rows
    report.write_csv(out / "dataset" / csv_name, item_rows_all, report.ITEM_COLUMNS)
    return item_rows_all, checks


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
        # digit-identical pages (match OR benign segmentation); used to gate the
        # item-level rows, whose values are additionally validated by the subtotal
        # arithmetic (which catches transpositions on segmentation pages).
        digit_ok_pages = set(range(1, n + 1)) - hard_pages
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

            # development additionally has the item-level Table III (source of funding)
            if b["kind"] == "development":
                head_amt = {}
                for vrec in votes.values():
                    for h in vrec["heads"]:
                        if h.get("values"):
                            head_amt[h["code"]] = (h["values"]["approved_2025_26"], h["values"]["net"])
                est_results = _collect_dev_estimates(cache, page_tmpl)
                est_checks = []
                est_rows_all = []
                for res in est_results:
                    v = res["vote"]
                    proj_ok = {}
                    for p in res["projects"]:
                        proj_ok[p["project_code"]] = bool(p["amount_ok"] and p["ext_ok"])
                        est_checks.append({"name": "project reconciles", "ok": proj_ok[p["project_code"]],
                                           "scope": f"vote {v} project {p['project_code']}", "detail": ""})
                    for hc, net in res["head_nets"].items():
                        if hc in head_amt and net:
                            ok = (head_amt[hc][0] == net["approved_2025_26"]
                                  and head_amt[hc][1] == net["est_2026_27"])
                            est_checks.append({"name": "head net == Table I", "ok": ok,
                                               "scope": f"vote {v} head {hc}", "detail": ""})
                    for p in res["problems"]:
                        est_checks.append({"name": "parse", "ok": False,
                                           "scope": f"vote {v}", "detail": p})
                    rows = report.dev_est_rows(b["id"], res)
                    for row in rows:
                        page_ok = (str(row["page"]).isdigit()
                                   and int(row["page"]) in digit_ok_pages)
                        ok = proj_ok.get(row["project_code"], False) and page_ok
                        row["verified"] = "yes" if ok else "review"
                    est_rows_all += rows
                report.write_csv(out / "dataset" / f"{b['id']}_estimates.csv",
                                 est_rows_all, report.DEV_EST_COLUMNS)
                sections["DEV_TABLE_III"] = {"checks": est_checks,
                                             "summary": validate.summarize(est_checks)}
                all_checks += est_checks
                nproj = sum(len(r["projects"]) for r in est_results)
                nver = sum(1 for row in est_rows_all if row["verified"] == "yes")
                print(f"  DEV_TABLE_III: {nproj} projects, {len(est_rows_all)} rows, {nver} verified "
                      f"({(nver/len(est_rows_all)*100) if est_rows_all else 0:.1f}%)")

                # development Table II: heads-and-items economic detail (reuses Table II parser)
                vt2 = {v: (rec.get("vote_title") or "") for v, rec in votes.items()}
                t2_results = _collect_rec_items(cache, page_tmpl, classify.DEV_VOTE_SUMMARY_II)
                t2_rows, t2_checks = _emit_table_ii(
                    b["id"], t2_results, vt2, digit_ok_pages, out, f"{b['id']}_heads_items.csv")
                sections["DEV_TABLE_II"] = {"checks": t2_checks,
                                            "summary": validate.summarize(t2_checks)}
                all_checks += t2_checks
                nv2 = sum(1 for r in t2_rows if r["verified"] == "yes")
                print(f"  DEV_TABLE_II (items): {len(t2_rows)} items, {nv2} verified "
                      f"({(nv2/len(t2_rows)*100) if t2_rows else 0:.1f}%)")

            # recurrent additionally has the item-level Table II + front-matter summary
            if b["kind"] == "recurrent":
                vt_by_vote = {v: (rec.get("vote_title") or "") for v, rec in votes.items()}
                ii_results = _collect_rec_items(cache, page_tmpl)
                item_rows_all, ii_checks = _emit_table_ii(
                    b["id"], ii_results, vt_by_vote, digit_ok_pages, out, f"{b['id']}_items.csv")
                sections["REC_TABLE_II"] = {"checks": ii_checks,
                                            "summary": validate.summarize(ii_checks)}
                all_checks += ii_checks
                nver = sum(1 for r in item_rows_all if r["verified"] == "yes")
                print(f"  REC_TABLE_II (items): {len(item_rows_all)} items, {nver} verified "
                      f"({(nver/len(item_rows_all)*100) if item_rows_all else 0:.1f}%)")

                fm_pages = [pg["xpdf"] for i, pg in enumerate(cache["pages"])
                            if page_tmpl[i] == classify.REC_FM]
                if fm_pages:
                    fmr = parse_rec.parse_fm(fm_pages)
                    fm_rows = report.rec_fm_rows(b["id"], fmr)
                    for row, src in zip(fm_rows, fmr["rows"]):
                        vv = src.get("values")
                        page_ok = str(row["page"]).isdigit() and int(row["page"]) in digit_ok_pages
                        good = vv is not None and page_ok
                        if good and src["row_type"] in ("vote", "cfs"):
                            good = (vv["gross_approved_2025_26"] - vv["aia_2025_26"] == vv["net_approved_2025_26"]
                                    and vv["gross_est_2026_27"] - vv["aia_2026_27"] == vv["net_est_2026_27"])
                        row["verified"] = "yes" if good else "review"
                    report.write_csv(out / "dataset" / f"{b['id']}_fm_summary.csv",
                                     fm_rows, report.REC_FM_COLUMNS)
                    fm_checks = list(fmr["checks"])
                    for p in fmr["problems"]:
                        fm_checks.append({"name": "parse", "ok": False, "scope": "REC_FM", "detail": p})
                    sections["REC_FM"] = {"checks": fm_checks, "summary": validate.summarize(fm_checks)}
                    all_checks += fm_checks
                    nvotes = len([r for r in fm_rows if r["row_type"] == "vote"])
                    okc = sum(1 for c in fm_checks if c["ok"])
                    print(f"  REC_FM: {nvotes} votes + CFS, {okc}/{len(fm_checks)} checks pass")
        elif b["kind"] == "program-based":
            pb = parse_pb.parse_part_h([pg["xpdf"] for pg in cache["pages"]])
            pb_rows_all = report.pb_rows(b["id"], pb)
            for row, src in zip(pb_rows_all, pb["rows"]):
                page_ok = (str(row["page"]).isdigit()
                           and int(row["page"]) in digit_ok_pages)
                row["verified"] = "yes" if (src["block_ok"] and page_ok) else "review"
            report.write_csv(out / "dataset" / f"{b['id']}_part_h.csv",
                             pb_rows_all, report.PB_COLUMNS)
            pb_checks = list(pb["checks"])
            for p in pb["problems"]:
                pb_checks.append({"name": "parse", "ok": False, "scope": "part-h", "detail": p})
            sections["PB_PART_H"] = {"checks": pb_checks,
                                     "summary": validate.summarize(pb_checks)}
            all_checks += pb_checks
            econ = [r for r in pb_rows_all if r["row_type"] == "econ"]
            nblk = len(pb["checks"]); okblk = sum(1 for c in pb["checks"] if c["ok"])
            print(f"  PB_PART_H: {okblk}/{nblk} programme blocks reconcile "
                  f"({(okblk/nblk*100) if nblk else 0:.1f}%), {len(econ)} economic rows")

            # PART G (vote x economic class) and PART F (by programme)
            pages_txt = [pg["xpdf"] for pg in cache["pages"]]
            for label, parsed, name in (
                    ("PB_PART_G", parse_pb.parse_part_g(pages_txt), "part_g"),
                    ("PB_PART_F", parse_pb.parse_part_f(pages_txt), "part_f")):
                rr = report.pb_rows(b["id"], parsed)
                failed_votes = {c["scope"].replace("vote ", "") for c in parsed["checks"] if not c["ok"]}
                for row, src in zip(rr, parsed["rows"]):
                    page_ok = str(row["page"]).isdigit() and int(row["page"]) in digit_ok_pages
                    ok = src.get("block_ok", row["vote"] not in failed_votes)
                    row["verified"] = "yes" if (ok and page_ok) else "review"
                report.write_csv(out / "dataset" / f"{b['id']}_{name}.csv", rr, report.PB_COLUMNS)
                pchecks = list(parsed["checks"])
                for p in parsed["problems"]:
                    pchecks.append({"name": "parse", "ok": False, "scope": label, "detail": p})
                sections[label] = {"checks": pchecks, "summary": validate.summarize(pchecks)}
                all_checks += pchecks
                okc = sum(1 for c in parsed["checks"] if c["ok"])
                ndata = len([x for x in rr if x["row_type"] in ("econ", "programme")])
                print(f"  {label}: {okc}/{len(parsed['checks'])} reconcile, {ndata} rows")
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
