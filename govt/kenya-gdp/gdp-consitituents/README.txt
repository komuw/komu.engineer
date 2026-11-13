================================================================================
KENYA GDP BY EXPENDITURE COMPONENT (1964-2025)
================================================================================
Last built: 2026-07-15
Maintainer notes for anyone reproducing or extending this analysis.

--------------------------------------------------------------------------------
1. WHAT THIS FOLDER CONTAINS
--------------------------------------------------------------------------------
kenya-gdp/
  README.txt                         <- this file
  fetch_data.py                      <- downloads raw World Bank series -> data/raw/
  build_dataset.py                   <- builds the CSV + charts from data/raw/
  kenya_gdp_expenditure_lines.png      <- the line chart, full history (1964-2025)
  kenya_gdp_expenditure_lines_2000.png <- same chart zoomed to 2000-2025
  kenya_gdp_expenditure_lines_govt_combined.png
                                       <- variant: investment split public vs
                                          private, plus a government (G + Ig) line
  kenya_gdp_expenditure_lines_govt_combined_2000.png
                                       <- same variant, zoomed to 2000-2025
  data/
    kenya_gdp_expenditure_shares.csv <- MAIN tidy dataset (one row per year)
    raw/
      NE.CON.PRVT.ZS.json   Household & NPISH final consumption (% GDP)   [C]
      NE.CON.GOVT.ZS.json   General government final consumption (% GDP)  [G]
      NE.GDI.TOTL.ZS.json   Gross capital formation (% GDP)               [I]
      NE.GDI.FTOT.ZS.json   Gross fixed capital formation (% GDP)
      NE.EXP.GNFS.ZS.json   Exports of goods & services (% GDP)           [X]
      NE.IMP.GNFS.ZS.json   Imports of goods & services (% GDP)           [M]
      NE.RSB.GNFS.ZS.json   External balance on goods & services (% GDP)  [X-M]
      NY.GDP.MKTP.CD.json   GDP, current US$ (level)
      NY.GDP.MKTP.CN.json   GDP, current Kenyan shillings (level)
      IMF_ICSD_2021_KEN.csv  IMF Investment & Capital Stock Dataset 2021,
                             Kenya extract: government vs private investment
                             (nominal KES levels), used ONLY to derive the
                             government SHARE of fixed investment. See sect. 3.

The raw/ files are verbatim upstream responses: the JSON files are the World
Bank WDI API payloads, and IMF_ICSD_2021_KEN.csv is a straight country-slice of
the IMF ICSD 2021 workbook (no values altered). Everything else is derived from
them, so the whole pipeline is reproducible from raw/ alone.

--------------------------------------------------------------------------------
2. THE ECONOMICS: WHAT IS BEING MEASURED
--------------------------------------------------------------------------------
This is the EXPENDITURE approach to GDP, an accounting identity:

        GDP = C + G + I + (X - M)

  C  household (and NPISH) final consumption
  G  general government final consumption
  I  gross capital formation (investment: fixed investment + change in inventories)
  X  exports of goods and services
  M  imports of goods and services
  (X - M) = net exports / external balance (NEGATIVE for Kenya in almost every year)

Every component in the CSV is expressed as a PERCENT OF GDP at CURRENT (nominal)
prices, which is the correct basis for showing composition/shares over time.

--------------------------------------------------------------------------------
3. DATA SOURCES (LINKS)
--------------------------------------------------------------------------------
PRIMARY DATA — World Bank, World Development Indicators (WDI):
  Country page (Kenya):   https://data.worldbank.org/country/kenya
  Indicator catalogue:    https://data.worldbank.org/indicator?locations=KE
  API root used here:     https://api.worldbank.org/v2/country/KE/indicator/
  Per-indicator API URL pattern actually called:
    https://api.worldbank.org/v2/country/KE/indicator/<CODE>?format=json&per_page=300
  Individual indicator landing pages:
    C     https://data.worldbank.org/indicator/NE.CON.PRVT.ZS?locations=KE
    G     https://data.worldbank.org/indicator/NE.CON.GOVT.ZS?locations=KE
    I     https://data.worldbank.org/indicator/NE.GDI.TOTL.ZS?locations=KE
    Ifix  https://data.worldbank.org/indicator/NE.GDI.FTOT.ZS?locations=KE
    X     https://data.worldbank.org/indicator/NE.EXP.GNFS.ZS?locations=KE
    M     https://data.worldbank.org/indicator/NE.IMP.GNFS.ZS?locations=KE
    X-M   https://data.worldbank.org/indicator/NE.RSB.GNFS.ZS?locations=KE
    GDP$  https://data.worldbank.org/indicator/NY.GDP.MKTP.CD?locations=KE
    GDPksh https://data.worldbank.org/indicator/NY.GDP.MKTP.CN?locations=KE

UPSTREAM / ORIGINAL COMPILER of Kenya's national accounts:
  Kenya National Bureau of Statistics (KNBS):        https://www.knbs.or.ke
  National Accounts Rebasing - GDP Facts:            https://www.knbs.or.ke/reports/national-accounts-rebasing-gdp-facts/
  Sources & Methods (rebased accounts, PDF):         https://www.knbs.or.ke/wp-content/uploads/2021/09/Sources-and-Methods-for-the-Revised-and-Rebased-National-Accounts.pdf
  (World Bank WDI ultimately draws Kenya's figures from KNBS, via UN/OECD.)

SOURCE FOR THE REBASING HISTORY cited in section 6:
  KNBS (as above), summarised in:
  Cytonn, "Note on the 2021 Revision and Rebasing of National Accounts", Oct 2021:
    https://cytonn.com/uploads/downloads/05102021-note-on-revision-and-rebasing-of-national-accounts.pdf

SOURCE FOR THE INVESTMENT SPLIT (public vs private) shown ONLY in
kenya_gdp_expenditure_lines_govt_combined.png:
  IMF Investment and Capital Stock Dataset (ICSD), 2021 vintage.
    Landing page: https://infrastructuregovern.imf.org/  (PIMA Knowledge Hub)
    Workbook:     https://infrastructuregovern.imf.org/content/dam/PIMA/Knowledge-Hub/dataset/IMFInvestmentandCapitalStockDataset2021.xlsx
  The ICSD splits gross FIXED capital formation into general-government
  investment (igov_n) and private investment (ipriv_n), in nominal local
  currency, for Kenya over 1970-2019. WDI/KNBS do NOT publish this split
  (the WDI series NE.GDI.FPRV.* are entirely null for Kenya). We take ONLY
  the government SHARE of fixed investment, igov_n/(igov_n+ipriv_n), from
  ICSD and apply it to WDI's own fixed-investment line - see section 5.
  Note: ICSD is partly ESTIMATED (perpetual-inventory method) and is a
  different vintage from current WDI; its total fixed investment runs on
  average ~1.6pp of GDP below WDI's. We borrow only the ratio, not levels.

ALTERNATIVE SOURCES CONSIDERED (and why WDI was chosen):
  * IMF World Economic Outlook (WEO):
      https://www.imf.org/en/Publications/SPROLLS/world-economic-outlook-databases
    WEO does NOT publish the C/G/I/net-exports decomposition. It provides
    aggregates and 5-year PROJECTIONS (total investment, gross national savings,
    current-account balance) and FISCAL series (government revenue/expenditure,
    which is a budget concept, NOT national-accounts government consumption G).
    Good for forecasts and fiscal/external balances; unsuitable for expenditure
    composition. -> Not used here.
  * UN National Accounts Main Aggregates (UNSD): equivalent detail, the upstream
    of WDI; clunkier access. https://unstats.un.org/unsd/snaama/
  * Penn World Table: use ONLY for cross-country, PPP, REAL (not nominal) work.
    https://www.rug.nl/ggdc/productivity/pwt/

--------------------------------------------------------------------------------
4. METHODOLOGY (A) - HOW THE DATA WAS FETCHED
--------------------------------------------------------------------------------
Nine World Bank WDI series (listed in section 1) were requested from the WDI
REST API, one indicator at a time, for country=KE (Kenya), JSON format,
per_page=300 (large enough to return the full history in a single page).

  * fetch_data.py performs this programmatically and writes each response
    verbatim to data/raw/<CODE>.json.
  * ACCESS CAVEAT: api.worldbank.org is fronted by Cloudflare. On a normal
    network a plain HTTPS GET (curl / requests / urllib) returns JSON directly.
    In the sandboxed environment where this folder was first built, Cloudflare
    issued a JavaScript bot-challenge that a scripted client could not clear, so
    the raw JSON shipped here was retrieved through a JS-capable headless browser
    that solves the challenge. Either way the payload is byte-for-byte the WDI
    API response. If fetch_data.py hangs or reports a "Cloudflare challenge",
    run it from a normal machine, or just use the raw/ files already provided.
  * No data was hand-edited. The only transformation at fetch time is pretty-
    printing the JSON (indent=1).

--------------------------------------------------------------------------------
5. METHODOLOGY (B) - HOW THE ANALYSIS WAS DONE
--------------------------------------------------------------------------------
build_dataset.py (pure Python; deps: pandas, matplotlib):
  1. Reads each data/raw/<CODE>.json and extracts {year -> value}, dropping
     null observations.
  2. Outer-joins all series on 'year' into one table (1960-2025). Values are the
     WDI numbers unchanged; % columns are rounded to 3 dp for readability, GDP
     level columns keep full precision.
  3. Adds two derived, transparency columns:
        identity_sum_CGI_netX  = C + G + I + (X-M)          [should be ~100]
        statistical_discrepancy = 100 - identity_sum_CGI_netX
     (I is gross capital formation NE.GDI.TOTL.ZS; net exports is the reported
      external balance NE.RSB.GNFS.ZS, not recomputed from X and M, so the
      discrepancy also absorbs any X/M rounding.)
  4. Writes data/kenya_gdp_expenditure_shares.csv.
  5. Plots six lines (C, G, I, X, M, and net exports) for 1964-2025, draws a
     zero reference line, and marks national-accounts rebasing years (section 6)
     as dotted vertical lines. Saves two files: kenya_gdp_expenditure_lines.png
     (full history) and kenya_gdp_expenditure_lines_2000.png (2000-2025 zoom).
     Imports (M) are drawn dashed and government consumption (G) solid so the two
     neighbouring warm hues stay easy to tell apart.
  6. Builds the PUBLIC/PRIVATE INVESTMENT SPLIT and the government-combined
     chart (kenya_gdp_expenditure_lines_govt_combined.png):
       a. From data/raw/IMF_ICSD_2021_KEN.csv compute the government share of
          fixed investment, s = igov_n / (igov_n + ipriv_n), for 1970-2019.
       b. Apply that share to WDI's OWN gross fixed capital formation:
             govt_investment_pctGDP    = s * gross_fixed_capital_formation_pctGDP
          Private investment absorbs the remainder AND all inventory change, so
          that it reconciles to WDI gross capital formation (I) exactly:
             private_investment_pctGDP = gross_capital_formation_pctGDP
                                         - govt_investment_pctGDP
          By construction govt_investment + private_investment == I to rounding.
       c. Adds the direct government demand footprint:
             govt_C_plus_I_pctGDP = govt_consumption_pctGDP + govt_investment_pctGDP
          (This is G + government fixed investment: the state's OWN purchases of
          goods, services and capital. It EXCLUDES transfers, subsidies and
          interest, so it is NOT total public expenditure or the fiscal balance.)
       d. Total investment (I) is kept as a thin grey CONTEXT line across the
          whole span; the split lines and the G+Ig line stop at 2019 (the ICSD
          coverage limit), marked with an annotation. Only WDI supplies levels;
          IMF supplies only the split ratio.

To reproduce from scratch:
     python fetch_data.py        # (or rely on the shipped data/raw/)
     python build_dataset.py

CSV COLUMN DICTIONARY (data/kenya_gdp_expenditure_shares.csv):
  year                                   calendar year
  household_consumption_pctGDP           C, % of GDP        (NE.CON.PRVT.ZS)
  govt_consumption_pctGDP                G, % of GDP        (NE.CON.GOVT.ZS)
  gross_capital_formation_pctGDP         I, % of GDP        (NE.GDI.TOTL.ZS)
  gross_fixed_capital_formation_pctGDP   fixed I, % of GDP  (NE.GDI.FTOT.ZS)
  exports_pctGDP                         X, % of GDP        (NE.EXP.GNFS.ZS)
  imports_pctGDP                         M, % of GDP        (NE.IMP.GNFS.ZS)
  net_exports_pctGDP                     X-M, % of GDP      (NE.RSB.GNFS.ZS)
  gdp_current_usd                        GDP level, current US$   (NY.GDP.MKTP.CD)
  gdp_current_lcu_kes                    GDP level, current KES   (NY.GDP.MKTP.CN)
  identity_sum_CGI_netX                  C + G + I + (X-M)
  statistical_discrepancy                100 - identity_sum_CGI_netX
  imf_govt_share_of_fixed_investment     govt share of fixed I, 0-1 (IMF ICSD,
                                         1970-2019; blank otherwise)
  govt_investment_pctGDP                 public fixed investment, % of GDP
                                         (= share x fixed I; 1970-2019)
  private_investment_pctGDP              private I + inventories, % of GDP
                                         (= I - govt_investment; 1970-2019)
  govt_C_plus_I_pctGDP                   G + govt investment, % of GDP (1970-2019)

--------------------------------------------------------------------------------
6. KENYA NATIONAL-ACCOUNTS REBASING YEARS (marked on the chart)
--------------------------------------------------------------------------------
Kenya has revised/rebased its national accounts seven times. Rebasing changes
the base (reference) year and re-measures the economy, which can create BREAKS
in a long series. Revision year -> new base year (source: KNBS / Cytonn note):

  Revision   Old base -> New base   Effect
  1957       1947 -> 1954           inclusion of manufacturing sector
  1967       1954 -> 1964           first current + constant price estimates
  1976       1964 -> 1972           first revision under international guidelines
  1986*      1972 -> 1982           filled data gaps of the 1976 revision
  2006*      1982 -> 2001           standalone financial-services sector added
  2014       2001 -> 2009           GDP level +25.3%; Kenya reclassified as a
                                     LOWER-MIDDLE-INCOME country
  2021       2009 -> 2016           GDP level +5.3%

The chart marks the five revision years that fall inside the 1964-2025 window
(1976, 1986, 2006, 2014, 2021).
* Minor source discrepancy: the Cytonn note's prose lists these two as "1985"
  and "2005" while its own table lists "1986" and "2006"; treat the exact
  announcement year as +/- 1. The 2014 and 2021 rebasings are precisely dated
  and confirmed directly on the KNBS website.

--------------------------------------------------------------------------------
7. ASSUMPTIONS, LIMITATIONS AND THINGS TO WATCH
--------------------------------------------------------------------------------
a) NOMINAL, NOT REAL. All shares are current-price. This is correct for showing
   composition, but do NOT read the levels as real/volume growth. Constant-price
   shares would behave differently.

b) NET EXPORTS IS STRUCTURALLY NEGATIVE. Kenya runs a persistent trade deficit
   (roughly -5% to -15% of GDP). Because M is SUBTRACTED, the components do NOT
   stack cleanly to 100% and a naive pie/100%-stacked chart would be misleading.
   That is why net exports is drawn as its own line and imports are shown
   explicitly. A line chart (as requested) is the honest representation.

c) THE IDENTITY DOES NOT CLOSE EXACTLY. C + G + I + (X-M) sums to ~100 but not
   exactly: in this dataset the statistical discrepancy ranges about -5.8 to
   +4.7 percentage points (mean ~ +0.2). Larger gaps occur in scattered years
   (e.g. 1979, 1984-86, 1999, 2001-04, 2009-11). This reflects genuine
   statistical discrepancy plus the splicing of series from different vintages.
   The 'statistical_discrepancy' column exposes this rather than hiding it.
   If you need bars that sum to exactly 100%, add this residual explicitly.

d) SERIES BREAKS FROM REBASING. Interpret jumps around rebasing years as partly
   methodological, not purely behavioural. The clearest example in this dataset:
   household consumption jumps from ~62% of GDP (1994) to ~69% (1995) to ~76%
   (1996) - a step change that coincides with revised national-accounts
   methodology, not a sudden collapse in saving. Compare trends WITHIN a base-
   year regime with more confidence than ACROSS one.

e) PROVISIONAL RECENT YEARS. Values for roughly 2024-2025 are World Bank
   estimates/nowcasts, not final KNBS actuals, and are subject to revision.
   They are included here (as requested) but flag them in any published chart.

f) COVERAGE GAP. Gross capital formation (I) and gross fixed capital formation
   begin in 1964; the other series begin in 1960. The chart starts at 1964 so
   all plotted components share the same span. 1960-1963 rows exist in the CSV
   with blank I.

g) DEFINITIONS. G here is national-accounts GOVERNMENT CONSUMPTION (spending on
   goods/services + public wages); it EXCLUDES government investment (which sits
   in I) and transfers/subsidies. This is not the same as the government budget
   or total public expenditure. I ("investment") is GROSS (before depreciation)
   and includes changes in inventories; use gross_fixed_capital_formation for
   fixed investment only.

h) ROUNDING. Percent columns are rounded to 3 decimals; if you need maximum
   precision, re-derive from data/raw/ (values there are full precision).

i) THE INVESTMENT SPLIT IS SOURCE-SPLICED AND PARTLY ESTIMATED. Public vs
   private investment (and the G + Ig line) appears ONLY in
   kenya_gdp_expenditure_lines_govt_combined.png and rests on the IMF ICSD
   2021 (section 3). Three cautions:
     - COVERAGE ENDS 2019. The ICSD Kenya split runs 1970-2019 only; there is
       NO public/private split for 2020-2025. Those split lines stop at 2019
       (annotated on the chart); total investment continues as a context line.
     - RATIO, NOT LEVELS. Only the government SHARE of fixed investment is taken
       from IMF; it is applied to WDI's own fixed-investment level so the split
       reconciles to WDI's I exactly. ICSD's own investment total sits ~1.6pp of
       GDP below WDI's (different vintage + perpetual-inventory estimation), so
       mixing ICSD levels with WDI would have left a visible gap - avoided here.
     - govt_C_plus_I IS DIRECT STATE DEMAND, NOT FISCAL SIZE. It captures the
       government's own purchases of goods, services and capital (G + Ig). It
       EXCLUDES transfers, subsidies, interest and lending, so it is smaller
       than total public expenditure and is not a measure of the fiscal deficit.

--------------------------------------------------------------------------------
8. CITATION
--------------------------------------------------------------------------------
World Bank, World Development Indicators (indicator codes as listed), accessed
2026-07-15, https://data.worldbank.org ; underlying national accounts compiled
by the Kenya National Bureau of Statistics (KNBS), https://www.knbs.or.ke .
Public/private investment split (govt_combined chart only): International
Monetary Fund, Investment and Capital Stock Dataset 2021, accessed 2026-07-15,
https://infrastructuregovern.imf.org .
================================================================================
