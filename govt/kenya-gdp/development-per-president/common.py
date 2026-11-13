"""Shared loaders and the president/term rule, used by every script.

All money is KSh million. A financial year (FY) is identified by the calendar
year in which it ends (July 2025 - June 2026 -> 2026, label "25/26").
"""
import csv, json, re

FIRST_FY = 2004  # FY03/04, first year on the Stats Kenya chart


def num(s):
    s = str(s).replace(',', '').strip()
    return float(s) if s else 0.0


def label(y):
    return f"{str(y - 1)[2:]}/{str(y)[2:]}"


# ---- who was president -------------------------------------------------
# Each FY goes to the president in office for most of it.
# Kibaki: 30 Dec 2002 - 9 Apr 2013  -> FY03/04 .. FY12/13
# Kenyatta: 9 Apr 2013 - 13 Sep 2022 -> FY13/14 .. FY21/22
# Ruto: 13 Sep 2022 -               -> FY22/23 .. FY26/27 (term ends Aug 2027)
TERMS = [('Kibaki', 2004, 2013), ('Kenyatta', 2014, 2022), ('Ruto', 2023, 2027)]
COLORS = {'Kibaki': '#5ab4e5', 'Kenyatta': '#f7f76a', 'Ruto': '#ff9966'}


def president(y, terms=TERMS):
    for n, a, b in terms:
        if a <= y <= b:
            return n
    raise ValueError(f"FY ending {y} is not assigned to a president; update TERMS in common.py")


# ---- CBK revenue & expenditure (June row = full-year total) -------------
# Columns of rev.csv (see header rows 5-7):
#  9 TOTAL REVENUE (tax + non-tax), 12 Total grants, 13 Domestic interest,
# 14 Foreign interest, 19 County transfer, 20 DEVELOPMENT EXPENDITURE,
# 21 TOTAL EXPENDITURE
def load_rev(path='rev.csv'):
    out = {}
    for r in csv.reader(open(path)):
        if r[0].strip().isdigit() and r[1].strip() == '6' and int(r[0]) >= FIRST_FY:
            y = int(r[0])
            out[y] = dict(rev=num(r[9]), grants=num(r[12]), dom_int=num(r[13]), for_int=num(r[14]),
                          county=num(r[19]), dev=num(r[20]), total_exp=num(r[21]))
            out[y]['interest'] = out[y]['dom_int'] + out[y]['for_int']
            # deficit = what had to be borrowed (commitment basis)
            out[y]['deficit'] = out[y]['total_exp'] - out[y]['rev'] - out[y]['grants']
    return out


# ---- CBK public debt stock, end of June ---------------------------------
def load_debt(path='debt.csv'):
    return {int(r[0]): dict(dom=num(r[2]), ext=num(r[3]), total=num(r[4]))
            for r in csv.reader(open(path)) if r[0].strip().isdigit() and r[1].strip() == '6'}


# ---- IMF WEO nominal GDP, KSh, calendar year ----------------------------
# The World Bank WDI series (NY.GDP.MKTP.CN) has rebasing breaks in 2006 and
# 2009 and does not reproduce the Stats Kenya chart before FY09/10; the IMF
# WEO series reproduces it to within 0.1pp for every year.
def load_gdp(path='imf_weo_NGDP.xml'):
    s = open(path).read()
    return {int(a): float(b) / 1e6 for a, b in re.findall(r'TIME_PERIOD="(\d+)" OBS_VALUE="([^"]+)"', s)}


def fy_gdp(gdp, y):
    """FY GDP = mean of the two calendar years it spans."""
    return (gdp[y - 1] + gdp[y]) / 2


# ---- World Bank: external public principal (US$) and KSh/US$ ------------
def load_ext_principal(p_path='wb_amt.json', fx_path='wb_PA.NUS.FCRF.json'):
    P = {int([t['value'] for t in v['variable'] if t['concept'] == 'Time'][0]): v['value']
         for v in json.load(open(p_path))['source']['data'] if v['value'] is not None}
    FX = {int(x['date']): x['value'] for x in json.load(open(fx_path))[1] if x['value'] is not None}
    last = min(max(P), max(FX))
    ksh = lambda cy: P[min(cy, last)] * FX[min(cy, last)] / 1e6  # KSh million
    return (lambda y: (ksh(y - 1) + ksh(y)) / 2), last           # FY = mean of 2 calendar years


def terms_present(years, terms=TERMS):
    """[(name, [years...])] for the years we actually have."""
    return [(n, [y for y in years if a <= y <= b]) for n, a, b in terms if any(a <= y <= b for y in years)]


def write_csv(path, header, rows):
    with open(path, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
