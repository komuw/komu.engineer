#!/usr/bin/env python3
"""
build_dataset.py
----------------
Builds the Kenya GDP-by-expenditure dataset and chart from raw World Bank
World Development Indicators (WDI) JSON responses stored in ./data/raw/.

It does NOT hit the network. It reads the raw JSON files that were downloaded
from the World Bank API (see fetch_data.py for how those were obtained) and
produces:
    data/kenya_gdp_expenditure_shares.csv   (tidy, one row per year)
    kenya_gdp_expenditure_lines.png         (line chart, 1964-2025)

Run:  python build_dataset.py
Deps: pandas, matplotlib   (pip install pandas matplotlib)
"""
import json, os, glob
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
RAW  = os.path.join(HERE, "data", "raw")

# Second source, used ONLY for the private/government investment split.
# The World Bank WDI has no private/public investment breakdown for Kenya
# (NE.GDI.FPRV.ZS / .CN return zero observations), so the split ratio is
# imported from the IMF Investment and Capital Stock Dataset (ICSD, 2021).
ICSD_FILE = os.path.join(RAW, "IMF_ICSD_2021_KEN.csv")

# WDI indicator code -> (short column name, human label)
INDICATORS = {
    "NE.CON.PRVT.ZS": ("household_consumption_pctGDP", "Household consumption (C)"),
    "NE.CON.GOVT.ZS": ("govt_consumption_pctGDP",      "Government consumption (G)"),
    "NE.GDI.TOTL.ZS": ("gross_capital_formation_pctGDP","Investment / gross capital formation (I)"),
    "NE.GDI.FTOT.ZS": ("gross_fixed_capital_formation_pctGDP","Gross fixed capital formation"),
    "NE.EXP.GNFS.ZS": ("exports_pctGDP",               "Exports (X)"),
    "NE.IMP.GNFS.ZS": ("imports_pctGDP",               "Imports (M)"),
    "NE.RSB.GNFS.ZS": ("net_exports_pctGDP",           "External balance / net exports (X-M)"),
    "NY.GDP.MKTP.CD": ("gdp_current_usd",              "GDP (current US$)"),
    "NY.GDP.MKTP.CN": ("gdp_current_lcu_kes",          "GDP (current KES)"),
}

# Kenya national-accounts revision (rebasing) years and the new base year adopted.
# Source: KNBS, summarised in Cytonn "Note on the 2021 Revision and Rebasing of
# National Accounts" (Oct 2021). The 2014 and 2021 rebasings are the modern,
# best-documented ones and are the most material to the WDI series.
REBASINGS = {
    1976: "new base 1972",
    1986: "new base 1982",
    2006: "new base 2001",
    2014: "new base 2009 (+25.3% GDP)",
    2021: "new base 2016 (+5.3% GDP)",
}


def load_indicator(code):
    """Read one WDI JSON file -> {year:int -> value:float}."""
    path = os.path.join(RAW, code + ".json")
    with open(path, encoding="utf-8") as fh:
        payload = json.load(fh)
    rows = payload[1]  # payload[0] is metadata, payload[1] is the data array
    return {int(r["date"]): r["value"] for r in rows if r["value"] is not None}


def load_icsd_gov_investment_share():
    """
    IMF Investment and Capital Stock Dataset (ICSD, 2021 vintage), Kenya extract.
    Returns {year -> government share of fixed investment} = igov / (igov + ipriv),
    computed from the nominal (current-KES) columns igov_n and ipriv_n.

    This is the ONE quantity imported from a second source: the World Bank WDI
    publishes no private/public investment split for Kenya. ICSD covers 1970-2019,
    so the returned dict has no entries outside that window (the split lines on the
    chart simply stop where coverage ends).
    Source: IMF, https://infrastructuregovern.imf.org/ (ICSD 2021).
    """
    if not os.path.exists(ICSD_FILE):
        print("WARNING: ICSD file missing, investment split will be blank:", ICSD_FILE)
        return {}
    icsd = pd.read_csv(ICSD_FILE).dropna(subset=["igov_n", "ipriv_n"])
    share = icsd["igov_n"] / (icsd["igov_n"] + icsd["ipriv_n"])
    return dict(zip(icsd["year"].astype(int), share))


def build_dataframe():
    series = {}
    for code, (col, _label) in INDICATORS.items():
        series[col] = load_indicator(code)
    years = sorted(set().union(*[set(v) for v in series.values()]))
    df = pd.DataFrame({"year": years})
    for col in series:
        df[col] = df["year"].map(series[col])
    # Accounting identity check (statistical discrepancy = 100 - sum):
    df["identity_sum_CGI_netX"] = (
        df["household_consumption_pctGDP"]
        + df["govt_consumption_pctGDP"]
        + df["gross_capital_formation_pctGDP"]
        + df["net_exports_pctGDP"]
    )
    df["statistical_discrepancy"] = 100.0 - df["identity_sum_CGI_netX"]

    # --- Investment split: private vs government --------------------------------
    # WDI has no public/private investment breakdown for Kenya. We import ONLY the
    # government share of FIXED investment from the IMF ICSD (1970-2019) and apply
    # it to the WDI fixed-investment line. The residual up to WDI *total* gross
    # capital formation (i.e. including changes in inventories, which are treated
    # as private) is private investment. By construction:
    #     govt_investment + private_investment == gross_capital_formation (I)
    gov_share = load_icsd_gov_investment_share()
    df["imf_govt_share_of_fixed_investment"] = df["year"].map(gov_share)
    df["govt_investment_pctGDP"] = (
        df["gross_fixed_capital_formation_pctGDP"]
        * df["imf_govt_share_of_fixed_investment"]
    )
    df["private_investment_pctGDP"] = (
        df["gross_capital_formation_pctGDP"] - df["govt_investment_pctGDP"]
    )
    # (b) requested aggregate: the state's direct demand footprint in GDP
    #     (government consumption G + government investment). Excludes transfers.
    df["govt_C_plus_I_pctGDP"] = (
        df["govt_consumption_pctGDP"] + df["govt_investment_pctGDP"]
    )
    return df


def plot(df, start_year=1964, out_name="kenya_gdp_expenditure_lines.png"):
    d = df[df["year"] >= start_year].copy()
    end_year = int(d["year"].max())
    fig, ax = plt.subplots(figsize=(13, 7.6))
    # High-contrast, colourblind-safe palette (Wong 2011). Distinct hue per line;
    # line styles add separation for series with neighbouring hues (G vs M).
    lines = [
        ("household_consumption_pctGDP",  "Household consumption (C)",                "#0072B2", "-"),   # blue
        ("govt_consumption_pctGDP",       "Government consumption (G)",               "#E69F00", "-"),   # orange, solid
        ("gross_capital_formation_pctGDP","Investment / gross capital formation (I)", "#009E73", "-"),   # green
        ("exports_pctGDP",                "Exports (X)",                              "#CC79A7", "--"),  # magenta, dashed
        ("imports_pctGDP",                "Imports (M)",                              "#D55E00", (0, (5, 2))),  # vermillion, dashed
        ("net_exports_pctGDP",            "Net exports (X - M)",                      "#000000", "-."),  # black, dash-dot
    ]
    for col, lab, c, ls in lines:
        ax.plot(d["year"], d[col], label=lab, color=c, lw=2.1, ls=ls)
    ax.axhline(0, color="k", lw=.7, alpha=.4)

    # Rebasing markers, labelled just under the top of the plot
    ax.set_xlim(d["year"].min(), d["year"].max())
    ymin, ymax = ax.get_ylim()
    for yr, note in sorted(REBASINGS.items()):
        if d["year"].min() <= yr <= d["year"].max():
            ax.axvline(yr, color="grey", ls=":", lw=1.1, alpha=.7)
            ax.text(yr - 0.4, ymax - 1.5, f"{yr}  {note}", rotation=90,
                    va="top", ha="right", fontsize=7, color="dimgrey")

    ax.set_title(f"Kenya — GDP by expenditure component (% of GDP), {start_year}-{end_year}\n"
                 "Source: World Bank WDI. Dotted grey lines = national-accounts rebasing years (KNBS).",
                 fontsize=13, weight="bold")
    ax.set_xlabel("Year"); ax.set_ylabel("% of GDP")
    # Legend moved OUT of the plot area, into a row beneath the axes.
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=3,
              fontsize=9.5, framealpha=.9, borderaxespad=0.)
    ax.grid(alpha=.25)
    # leave room at the bottom for the external legend
    fig.subplots_adjust(bottom=0.18, top=0.88, left=0.07, right=0.98)
    out = os.path.join(HERE, out_name)
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print("wrote", out)


def plot_govt_combined(df, start_year=1964,
                       out_name="kenya_gdp_expenditure_lines_govt_combined.png"):
    """
    Variant of the main expenditure chart that:
      (a) SPLITS investment into private and government investment (government
          share of fixed investment from the IMF ICSD, 1970-2019), and
      (b) adds an emphasized line = government consumption + government investment
          (the state's direct demand footprint in GDP; excludes transfers/subsidies).

    Total investment (I) is retained as a light CONTEXT line across the full span
    because the public/private split is only defined through the ICSD's 2019 cutoff.
    Everything else (C, G, X, M, net exports) is unchanged World Bank WDI.
    """
    d = df[df["year"] >= start_year].copy()
    end_year = int(d["year"].max())
    have_split = d["govt_investment_pctGDP"].notna()
    split_last = int(d.loc[have_split, "year"].max()) if have_split.any() else end_year

    fig, ax = plt.subplots(figsize=(13, 7.6))

    # Context: total investment (I) across the whole span, thin and muted.
    ax.plot(d["year"], d["gross_capital_formation_pctGDP"],
            label="Total investment (I) — context", color="#999999",
            lw=1.3, ls=(0, (1, 1.6)), alpha=.9, zorder=1)

    # (col, label, colour, linestyle, linewidth). Wong-2011 colourblind-safe hues;
    # the government aggregate (G + Ig) is drawn thick to read as the headline.
    lines = [
        ("household_consumption_pctGDP", "Household consumption (C)",        "#0072B2", "-",         2.1),
        ("govt_consumption_pctGDP",      "Government consumption (G)",       "#E69F00", "-",         2.1),
        ("private_investment_pctGDP",    "Private investment",               "#009E73", "-",         2.1),
        ("govt_investment_pctGDP",       "Government investment",            "#56B4E9", "-",         2.3),
        ("exports_pctGDP",               "Exports (X)",                      "#CC79A7", "--",        2.1),
        ("imports_pctGDP",               "Imports (M)",                      "#D55E00", (0, (5, 2)), 2.1),
        ("net_exports_pctGDP",           "Net exports (X - M)",              "#000000", "-.",        2.1),
        ("govt_C_plus_I_pctGDP",         "Government consumption + investment", "#882255", "-",      3.0),
    ]
    for col, lab, c, ls, lw in lines:
        ax.plot(d["year"], d[col], label=lab, color=c, lw=lw, ls=ls)
    ax.axhline(0, color="k", lw=.7, alpha=.4)

    ax.set_xlim(d["year"].min(), d["year"].max())
    ymin, ymax = ax.get_ylim()
    for yr, note in sorted(REBASINGS.items()):
        if d["year"].min() <= yr <= d["year"].max():
            ax.axvline(yr, color="grey", ls=":", lw=1.1, alpha=.7)
            ax.text(yr - 0.4, ymax - 1.5, f"{yr}  {note}", rotation=90,
                    va="top", ha="right", fontsize=7, color="dimgrey")

    # Mark where the ICSD-based investment split stops.
    if split_last < end_year:
        ax.axvline(split_last, color="#2c6e91", ls=(0, (2, 2)), lw=1.1, alpha=.7)
        ax.text(split_last - 0.4, ymin + 0.8,
                f"public/private split ends {split_last}  (IMF ICSD coverage)",
                rotation=90, va="bottom", ha="right", fontsize=7, color="#2c6e91")

    ax.set_title(
        f"Kenya — GDP by expenditure, investment split public vs private (% of GDP), {start_year}-{end_year}\n"
        "Lines: World Bank WDI.  Investment split: IMF ICSD 2021 (govt share of fixed investment), "
        f"1970-{split_last}.  Dotted grey = KNBS rebasing years.",
        fontsize=10.5, weight="bold")
    ax.set_xlabel("Year"); ax.set_ylabel("% of GDP")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=3,
              fontsize=9, framealpha=.9, borderaxespad=0.)
    ax.grid(alpha=.25)
    fig.subplots_adjust(bottom=0.20, top=0.86, left=0.07, right=0.98)
    out = os.path.join(HERE, out_name)
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print("wrote", out)


def main():
    df = build_dataframe()
    csv = os.path.join(HERE, "data", "kenya_gdp_expenditure_shares.csv")
    # round the share/level columns for readability but keep full precision GDP levels
    share_cols = [c for c in df.columns if c.endswith("pctGDP") or c in
                  ("identity_sum_CGI_netX", "statistical_discrepancy")]
    df[share_cols] = df[share_cols].round(3)
    if "imf_govt_share_of_fixed_investment" in df.columns:
        df["imf_govt_share_of_fixed_investment"] = df["imf_govt_share_of_fixed_investment"].round(4)
    df.to_csv(csv, index=False)
    print("wrote", csv, f"({len(df)} rows, {df.year.min()}-{df.year.max()})")
    plot(df, start_year=1964, out_name="kenya_gdp_expenditure_lines.png")
    plot(df, start_year=2000, out_name="kenya_gdp_expenditure_lines_2000.png")
    plot_govt_combined(df, start_year=1964,
                       out_name="kenya_gdp_expenditure_lines_govt_combined.png")
    plot_govt_combined(df, start_year=2000,
                       out_name="kenya_gdp_expenditure_lines_govt_combined_2000.png")


if __name__ == "__main__":
    main()
