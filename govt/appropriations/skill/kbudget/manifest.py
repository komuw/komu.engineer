"""Per-year manifest: the single declarative input for a financial year.

A manifest freezes exactly which PDFs are in scope, their checksums (so a silent
re-download or edit is detected), and their page counts. Running a new financial
year is: drop the PDFs in a folder, `build` a manifest, run the pipeline.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path

import yaml


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def page_count(path: Path) -> int:
    """Page count via Xpdf form-feed separators (no extra dependency)."""
    out = subprocess.run(
        ["pdftotext", str(path), "-"], capture_output=True, text=True, errors="ignore"
    ).stdout
    return out.count("\f")


def slug(name: str) -> str:
    s = re.sub(r"\.pdf$", "", name, flags=re.I)
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()
    return s


@dataclass
class Book:
    id: str
    filename: str
    sha256: str
    pages: int
    kind: str  # development | recurrent | program-based | unknown


def _guess_kind(filename: str) -> str:
    f = filename.lower()
    if "development" in f:
        return "development"
    if "recurrent" in f:
        return "recurrent"
    if "program" in f or "programme" in f:
        return "program-based"
    return "unknown"


def build(year_dir: Path) -> dict:
    year_dir = Path(year_dir)
    books = []
    for pdf in sorted(year_dir.glob("*.pdf")):
        books.append(
            Book(
                id=slug(pdf.name),
                filename=pdf.name,
                sha256=sha256(pdf),
                pages=page_count(pdf),
                kind=_guess_kind(pdf.name),
            )
        )
    return {
        "year_dir": str(year_dir),
        "books": [asdict(b) for b in books],
    }


def manifest_path(year_dir: Path) -> Path:
    return Path(year_dir) / "manifest.yaml"


def write(year_dir: Path, data: dict) -> Path:
    p = manifest_path(year_dir)
    p.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return p


def load(year_dir: Path) -> dict:
    return yaml.safe_load(manifest_path(year_dir).read_text(encoding="utf-8"))


def verify(year_dir: Path) -> list[str]:
    """Re-check checksums against the manifest. Returns a list of problems."""
    data = load(year_dir)
    problems = []
    for b in data["books"]:
        p = Path(year_dir) / b["filename"]
        if not p.exists():
            problems.append(f"missing file: {b['filename']}")
            continue
        got = sha256(p)
        if got != b["sha256"]:
            problems.append(f"checksum drift: {b['filename']} expected {b['sha256'][:12]} got {got[:12]}")
    return problems
