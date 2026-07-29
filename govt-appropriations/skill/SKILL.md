# Skill: Kenya GoK Budget Appropriation PDF -> fidelity-checked data

Convert the National Treasury's annual appropriation PDFs (Development, Recurrent,
Program-based books) into an analysis-ready dataset **without losing or corrupting
any number**, and prove it.

## Why this exists / the fidelity model

These PDFs are machine-generated reports whose numeric columns are drawn at
inconsistent vertical positions. Naive extraction (`pdftotext -layout`, copy-paste,
generic "PDF->Markdown") **silently mis-assigns values to the wrong rows**. That is
the worst failure mode for financial analysis because the numbers still look valid.

Fidelity is therefore guaranteed by **two independent mechanisms**, and no LLM is
ever in the number path:

1. **Cross-engine reconciliation (universal).** Every page is extracted by two
   independent parsers - Xpdf `pdftotext -table` and pdfplumber/pdfminer.six - and
   compared at both the number-token level and the individual-digit level, giving
   three per-page outcomes:
   - `match` - identical number tokens (nothing lost, boundaries agree).
   - `segmentation` - tokens differ but the digit multiset is identical: benign, the
     engines merely disagree where one number ends and the next begins. This happens
     only on dense grand-total tables where adjacent large numbers touch; Xpdf
     `-table` segments them correctly. Passes with a note, not a failure.
   - `mismatch` - the digit content actually differs (a digit dropped/added/changed).
     This is the only reconciliation state that goes to the review queue.
   `digit-coverage` (match + segmentation) proves "no digit was lost, added, or
   garbled" for the whole book, regardless of table template.
2. **Arithmetic validation (structural).** Parsed tables must satisfy the accounting
   identities printed in the documents (`Gross - AiA = Net`; components sum to
   totals; per-vote totals reconcile to the front-matter summary; front-matter
   Table I reconciles to the per-vote summaries). Anything that fails is routed to a
   **manual-review queue** - never silently accepted.

**Correctness bar: 100%.** A value is `verified` only if its page reconciled across
both engines AND every arithmetic identity touching it holds. Everything else is
`review`. (Automation floor target ~80%; below that a book/template needs work.)

## Prerequisites

- `uv` (Astral) on PATH. Scripts are self-contained (PEP 723) - deps auto-install.
- Xpdf `pdftotext` on PATH (provides the `-table` engine). Verify: `pdftotext -v`
  should say "xpdfreader.com". (Poppler's `pdftotext` lacks `-table`.)

## Run it for a financial year

```bash
# 1. Put the year's PDFs in one folder, e.g. govt-appropriations/2026-2027/
# 2. Freeze the inputs (records filenames, SHA-256, page counts):
uv run --script skill/run.py manifest --year-dir govt-appropriations/2026-2027

# 3. Run the pipeline (start with one book to gauge coverage):
uv run --script skill/run.py run --year-dir govt-appropriations/2026-2027 \
       --only "Development Book Volume 1"

# whole year, or filter by kind:
uv run --script skill/run.py run --year-dir govt-appropriations/2026-2027
uv run --script skill/run.py run --year-dir govt-appropriations/2026-2027 --kind development
```

Flags: `--only <substr>` filter by filename, `--kind development|recurrent|program-based`,
`--force` (proceed despite checksum drift), `--force-extract` (ignore extraction cache).

## Outputs (under `<year-dir>/_out/`)

CSV is the **canonical, analysis-ready** output; Markdown is **derived from the CSV**
so the two cannot drift. Nil values are stored as `0` in CSV (numeric) and rendered
as `-` in Markdown (mirroring the PDF).

- `cache/<book>.json` - both engines' per-page output (regenerable; git-ignored).
- `dataset/<book>_summary.csv` - per-vote head-level table; one row per head plus a
  `row_type=vote_total` row per vote. Columns include descriptive, year-tagged money
  fields (`gross_expenditure_2026_2027`, ...) plus `page` and `verified`.
- `dataset/<book>_fm_table_i.csv` - front-matter summary of development expenditure
  & source of finance (per-vote; AiA composition + external revenue columns).
- `markdown/<book>/vote-<n>.md` - per-vote table regenerated from the CSV; headers
  carry the years exactly as the PDF (e.g. `Gross Expenditure 2026/2027`).
- `reports/<book>.md` - every validation check, pass/fail, with pass-rates.
- `review-queue/<book>.csv` - the only things a human must look at (check, scope,
  page, detail). Empty queue == fully auto-verified.

## Review-queue workflow

Open each item, go to the cited `page` in the source PDF, confirm the correct value,
and either fix the parser (preferred, so it's repeatable) or record a manual override.
Nothing ships as `verified` until its queue item is resolved.

## Coverage status

| Template | Status |
|---|---|
| every page, all six books | cross-engine numeric reconciliation (digit-coverage 100%) |
| `DEV_FM_TABLE_I` (development front-matter summary) | parsed + arithmetic-validated |
| `DEV_VOTE_SUMMARY_I` (development per-vote head-level) | parsed + arithmetic-validated |
| `REC_VOTE_SUMMARY_I` (recurrent per-vote head-level) | parsed + arithmetic-validated |
| `DEV_VOTE_SUMMARY_II`, `DEV_VOTE_ESTIMATES` (development item-level detail) | TODO structural parse |
| `REC_VOTE_SUMMARY_II` (recurrent heads-and-items detail) | TODO structural parse |
| `REC_FM` (recurrent front-matter summary) | TODO structural parse |
| Program-based `PART F/G/H` (expenditure by programme / economic class) | TODO structural parse |

Reconciliation already guarantees *no numbers lost* on the not-yet-parsed templates;
only the structured row/column dataset for them is pending. The head-level summary
parser is shared by Development and Recurrent (`REC_VOTE_SUMMARY_I` reuses it: same
6 columns, same `gross - aia = net` identity; head codes may be 10 or 11 digits).

## Architecture (`skill/kbudget/`)

- `textutil.py`  whitespace/number tokenisation (single source of numeric truth)
- `manifest.py`  freeze/verify the per-year input set (SHA-256)
- `extract.py`   two engines + on-disk cache
- `classify.py`  page-template detection (UNKNOWN == layout-drift alarm)
- `reconcile.py` cross-engine multiset check
- `parse_dev.py` structural parsers (arithmetic-guided row repair)
- `validate.py`  accounting identities + cross-template checks
- `report.py`    dataset / markdown / report / review-queue writers
- `run.py`       PEP 723 CLI orchestrator

## Handling layout drift (future years)

If the Treasury changes a template, pages fall to `UNKNOWN` (classifier) or rows fail
arithmetic (validator) - both surface loudly rather than corrupting data. Update the
relevant signature in `classify.py` and/or the parser in `parse_dev.py`, then re-run;
the frozen prior-year outputs in `dataset/` act as a regression baseline.
