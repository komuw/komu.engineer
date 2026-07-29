"""Page template classification.

Every page is assigned to exactly one template id. Detection is by normalised
(whitespace-collapsed) header signatures. An unmatched *content* page returns
UNKNOWN, which the pipeline treats as a layout-drift alarm rather than guessing.
"""
from __future__ import annotations

from .textutil import norm_upper

# Template ids ---------------------------------------------------------------
BLANK = "BLANK"
COVER = "COVER"
TOC = "TOC"
# Development book
FM_TABLE_I = "DEV_FM_TABLE_I"        # summary of dev expenditure & source of finance
FM_TABLE_II = "DEV_FM_TABLE_II"      # summary of external funding (by donor)
FM_TABLE_III = "DEV_FM_TABLE_III"    # details of external funding (by donor)
DEV_VOTE_SUMMARY_I = "DEV_VOTE_SUMMARY_I"    # per-vote head-level summary (Table I)
DEV_VOTE_SUMMARY_II = "DEV_VOTE_SUMMARY_II"  # per-vote "heads and items" breakdown (Table II)
DEV_VOTE_ESTIMATES = "DEV_VOTE_ESTIMATES"  # per-vote item detail + external funding
# Recurrent book
REC_FM = "REC_FM"                            # front-matter "summary of recurrent expenditure"
REC_VOTE_SUMMARY_I = "REC_VOTE_SUMMARY_I"    # per-vote head-level summary (Table I)
REC_VOTE_SUMMARY_II = "REC_VOTE_SUMMARY_II"  # per-vote "heads and items" breakdown (Table II)
# Program-based book
PB_PART = "PB_PART"                  # PART A-H programme-based sections
UNKNOWN = "UNKNOWN"


def classify(page_text: str) -> str:
    if len((page_text or "").strip()) < 15:
        return BLANK
    u = norm_upper(page_text)

    # --- front matter, shared markers ---
    if "TABLE OF CONTENTS" in u:
        return TOC

    # --- development book ---
    if "SUMMARY OF DEVELOPMENT EXPENDITURE AND" in u:
        return FM_TABLE_I
    if "SUMMARY OF EXTERNAL FUNDING" in u:
        return FM_TABLE_II
    if "DETAILS OF EXTERNAL FUNDING" in u:
        return FM_TABLE_III
    if "DEVELOPMENT EXPENDITURE SUMMARY" in u:
        # Table I is head-level; Table II is the "Heads and Items..." breakdown.
        if "HEADS AND ITEMS UNDER WHICH THIS VOTE" in u:
            return DEV_VOTE_SUMMARY_II
        return DEV_VOTE_SUMMARY_I
    if "DEVELOPMENT EXPENDITURE ESTIMATES" in u:
        return DEV_VOTE_ESTIMATES
    if "ESTIMATES OF DEVELOPMENT EXPENDITURE" in u and "GOVERNMENT OF" in u:
        return COVER

    # --- recurrent book ---
    if "SUMMARY OF RECURRENT EXPENDITURE" in u:
        return REC_FM
    if "RECURRENT EXPENDITURE SUMMARY" in u:
        if "HEADS AND ITEMS UNDER WHICH THIS VOTE" in u:
            return REC_VOTE_SUMMARY_II
        return REC_VOTE_SUMMARY_I
    if "ESTIMATES OF RECURRENT EXPENDITURE" in u and "GOVERNMENT OF" in u:
        return COVER

    # --- program-based book ---
    if u.startswith("PART ") or " PART A" in u[:60] or "PART A." in u[:80]:
        return PB_PART

    return UNKNOWN
