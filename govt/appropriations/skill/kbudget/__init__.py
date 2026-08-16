"""kbudget - fidelity-first extraction of Kenya GoK budget appropriation PDFs.

The numeric ground truth is produced by *deterministic* code only. No LLM is ever
in the number path. Fidelity is guaranteed by two mechanisms:

  1. Cross-engine reconciliation: the multiset of numeric tokens on every page is
     extracted independently by two PDF parsers (Xpdf `pdftotext -table` and
     pdfplumber/pdfminer.six). If they disagree, the page is flagged.
  2. Arithmetic validation: parsed tables must satisfy the accounting identities
     embedded in the documents (Gross - AiA = Net; components sum to totals;
     per-vote totals reconcile to the front-matter summary). Anything that fails
     is routed to a manual-review queue - never silently accepted.
"""

__version__ = "0.1.0"
