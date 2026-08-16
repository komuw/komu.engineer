"""Two independent extraction engines, with an on-disk cache.

Engine A  (Xpdf `pdftotext -table`)  -> per-page reconstructed-table text.
Engine B  (pdfplumber / pdfminer.six) -> per-page word list with coordinates.

These are genuinely independent PDF parsers (different codebases), which is what
makes the cross-engine reconciliation a real fidelity check rather than a tautology.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

import pdfplumber


def _xpdf_table_pages(pdf: Path) -> list[str]:
    """Run Xpdf once for the whole book; split into pages on form feeds."""
    out = subprocess.run(
        ["pdftotext", "-table", str(pdf), "-"],
        capture_output=True, text=True, errors="ignore",
    ).stdout
    pages = out.split("\f")
    if pages and pages[-1].strip() == "":
        pages = pages[:-1]  # trailing empty from final separator
    return pages


def _plumber_pages(pdf: Path) -> list[list]:
    """Per page: [[x0, top, x1, text], ...] rounded to 0.1pt."""
    pages = []
    with pdfplumber.open(str(pdf)) as doc:
        for page in doc.pages:
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            pages.append([
                [round(w["x0"], 1), round(w["top"], 1), round(w["x1"], 1), w["text"]]
                for w in words
            ])
    return pages


def cache_path(out_dir: Path, book_id: str) -> Path:
    return Path(out_dir) / "cache" / f"{book_id}.json"


def extract_book(pdf: Path, out_dir: Path, book_id: str, sha: str,
                 force: bool = False) -> dict:
    """Extract both engines for a book and cache the result. Idempotent:
    a cache whose sha matches is reused unless force=True."""
    cp = cache_path(out_dir, book_id)
    if cp.exists() and not force:
        data = json.loads(cp.read_text(encoding="utf-8"))
        if data.get("sha256") == sha:
            return data

    xpdf = _xpdf_table_pages(Path(pdf))
    plumber = _plumber_pages(Path(pdf))

    n = max(len(xpdf), len(plumber))
    # pad the shorter one so indices line up; mismatch is surfaced in `warnings`
    warnings = []
    if len(xpdf) != len(plumber):
        warnings.append(f"page-count mismatch: xpdf={len(xpdf)} plumber={len(plumber)}")
    xpdf += [""] * (n - len(xpdf))
    plumber += [[] for _ in range(n - len(plumber))]

    pages = [{"xpdf": xpdf[i], "words": plumber[i]} for i in range(n)]
    data = {"sha256": sha, "book_id": book_id, "npages": n,
            "warnings": warnings, "pages": pages}

    cp.parent.mkdir(parents=True, exist_ok=True)
    cp.write_text(json.dumps(data), encoding="utf-8")
    return data


def words_to_text(words: list) -> str:
    """Reconstruct plain page text from pdfplumber words (row-grouped by `top`)."""
    if not words:
        return ""
    rows: dict[int, list] = {}
    for x0, top, x1, text in words:
        key = round(top)
        rows.setdefault(key, []).append((x0, text))
    lines = []
    for top in sorted(rows):
        toks = [t for _, t in sorted(rows[top])]
        lines.append(" ".join(toks))
    return "\n".join(lines)
