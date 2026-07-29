"""Cross-engine numeric reconciliation - the universal, template-agnostic fidelity signal.

For each page we compare what two independent parsers (Xpdf `pdftotext -table` and
pdfplumber/pdfminer.six) extracted, at two levels:

  * token level  - the multiset of comma-grouped number tokens must match exactly.
  * digit level  - the multiset of individual digit characters on the page.

Outcomes per page:
  match         tokens identical                         -> nothing lost, boundaries agree
  segmentation  tokens differ BUT digits identical       -> benign: same digits, the engines
                                                            merely disagree where one number
                                                            ends and the next begins (happens
                                                            on dense grand-total tables where
                                                            adjacent large numbers touch)
  mismatch      digit multiset differs                   -> real: a digit was dropped / added /
                                                            changed. This is the only state
                                                            that must be reviewed.

Caveat: a `segmentation` page shares the same digit multiset, so a pure *transposition*
within that multiset would not be distinguished here. Such pages are grand-total/summary
tables that are derived from detail pages; once their structural parser exists they are
additionally cross-checked by arithmetic (totals must equal the sum of the details),
which is the definitive guard against transposition.
"""
from __future__ import annotations

from collections import Counter

from .extract import words_to_text
from .textutil import number_multiset


def _digit_multiset(s: str) -> Counter:
    return Counter(c for c in s if c.isdigit())


def reconcile_page(xpdf_text: str, words: list) -> dict:
    ptext = words_to_text(words)
    a = number_multiset(xpdf_text)
    b = number_multiset(ptext)
    only_a = a - b
    only_b = b - a
    if not only_a and not only_b:
        status = "match"
    elif _digit_multiset(xpdf_text) == _digit_multiset(ptext):
        status = "segmentation"
    else:
        status = "mismatch"
    return {
        "status": status,
        "n_tokens_xpdf": sum(a.values()),
        "n_tokens_plumber": sum(b.values()),
        "only_xpdf": dict(only_a),
        "only_plumber": dict(only_b),
    }


def reconcile_book(cache: dict) -> dict:
    pages = cache["pages"]
    n = len(pages)
    n_match = n_seg = n_mis = 0
    seg_pages: list[int] = []
    mismatches: list[dict] = []
    for i, pg in enumerate(pages):
        r = reconcile_page(pg["xpdf"], pg["words"])
        r["page"] = i + 1
        if r["status"] == "match":
            n_match += 1
        elif r["status"] == "segmentation":
            n_seg += 1
            seg_pages.append(i + 1)
        else:
            n_mis += 1
            mismatches.append(r)
    return {
        "book_id": cache["book_id"],
        "npages": n,
        "n_match": n_match,
        "n_segmentation": n_seg,
        "n_mismatch": n_mis,
        # fraction of pages whose DIGIT content is identical across both engines
        "digit_coverage": ((n_match + n_seg) / n) if n else 1.0,
        # fraction whose TOKENS are also identical (stricter)
        "strict_coverage": (n_match / n) if n else 1.0,
        "segmentation_pages": seg_pages,
        "mismatches": mismatches,
    }
