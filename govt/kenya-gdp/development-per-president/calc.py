"""Yearly measures, per-president summaries and sensitivity checks.

Outputs
  kenya_dev_vs_net_revenue.csv  one row per FY, every measure
  kenya_by_president.csv        per-president average of yearly values AND pooled (sum/sum)
  kenya_sensitivities.csv       headline measures under alternative assumptions
"""
from common import *

R = load_rev(); D = load_debt(); G = load_gdp()
years = sorted(R)
missing = [y for y in years if y not in G or y - 1 not in G or y - 1 not in D]
if missing:
    raise SystemExit(f"missing GDP/debt for FY {missing}")

# debt stock at the start of each president's term (June before first FY)
term_start = {n: D[ys[0] - 1]['total'] for n, ys in terms_present(years)}


def inherited_interest(y, r, terms=TERMS):
    """Interest on the debt the president inherited, assuming old and new debt
    cost the same: interest x (debt at start of term / debt at start of this FY)."""
    n = president(y, terms)
    a = [t for t in terms if t[0] == n][0][1]
    return r['interest'] * min(1.0, D[a - 1]['total'] / D[y - 1]['total'])


# Each measure is (numerator, denominator) so we can pool over a term.
MEASURES = {
    # 1. original chart
    'dev_pct_gdp':                       (lambda y, r: r['dev'],                   lambda y, r: fy_gdp(G, y)),
    # 2. headline: development / (revenue - interest)
    'dev_pct_rev_after_interest':        (lambda y, r: r['dev'],                   lambda y, r: r['rev'] - r['interest']),
    # 2a. only deduct interest on INHERITED debt (don't credit a president for interest on his own borrowing)
    'dev_pct_rev_after_inherited_int':   (lambda y, r: r['dev'],                   lambda y, r: r['rev'] - inherited_interest(y, r)),
    # 2b. recurrent balance: dev - deficit == revenue + grants - recurrent - county transfers.
    #     Development cancels out, so this measures whether borrowing paid for recurrent
    #     spending (burden passed on with no asset), NOT development effort.
    'recurrent_balance_pct_rev_after_int': (lambda y, r: r['dev'] - r['deficit'],  lambda y, r: r['rev'] - r['interest']),
    # 2c. also remove county transfers from the denominator
    'dev_pct_rev_after_int_and_county':  (lambda y, r: r['dev'],                   lambda y, r: r['rev'] - r['interest'] - r['county']),
    # 2d. include grants in the denominator (numerator already contains grant-funded projects)
    'dev_pct_rev_grants_after_int':      (lambda y, r: r['dev'],                   lambda y, r: r['rev'] + r['grants'] - r['interest']),
    # context
    'interest_pct_rev':                  (lambda y, r: r['interest'],              lambda y, r: r['rev']),
    'inherited_interest_pct_rev':        (lambda y, r: inherited_interest(y, r),   lambda y, r: r['rev']),
    'interest_pct_gdp':                  (lambda y, r: r['interest'],              lambda y, r: fy_gdp(G, y)),
    'rev_after_int_pct_gdp':             (lambda y, r: r['rev'] - r['interest'],   lambda y, r: fy_gdp(G, y)),
    'deficit_pct_gdp':                   (lambda y, r: r['deficit'],               lambda y, r: fy_gdp(G, y)),
    'deficit_per_dev':                   (lambda y, r: r['deficit'] / 100,         lambda y, r: r['dev']),  # ratio, not %
}


def value(m, y, r):
    a, b = MEASURES[m]
    return 100 * a(y, r) / b(y, r)


# ---- yearly file -------------------------------------------------------
hdr = ['FY', 'president', 'revenue_KShm', 'grants_KShm', 'interest_KShm', 'inherited_interest_KShm', 'dev_KShm',
       'county_transfers_KShm', 'total_exp_KShm', 'deficit_KShm', 'gdp_fy_KShm'] + list(MEASURES)
rows = []
for y in years:
    r = R[y]
    rows.append([label(y), president(y), round(r['rev']), round(r['grants']), round(r['interest']),
                 round(inherited_interest(y, r)), round(r['dev']), round(r['county']), round(r['total_exp']),
                 round(r['deficit']), round(fy_gdp(G, y))] +
                [round(value(m, y, r), 2 if m == 'deficit_per_dev' else 1) for m in MEASURES])
write_csv('kenya_dev_vs_net_revenue.csv', hdr, rows)


# ---- per-president -----------------------------------------------------
def summarise(m, ys, data=R, terms=TERMS):
    a, b = MEASURES[m]
    avg = sum(100 * a(y, data[y]) / b(y, data[y]) for y in ys) / len(ys)
    pooled = 100 * sum(a(y, data[y]) for y in ys) / sum(b(y, data[y]) for y in ys)
    return avg, pooled


out = []
print(f"{'measure':36s}" + ''.join(f"{n:>22s}" for n, _ in terms_present(years)))
print(f"{'':36s}" + ''.join(f"{'avg-of-yrs / pooled':>22s}" for _ in terms_present(years)))
for m in MEASURES:
    line = f"{m:36s}"
    for n, ys in terms_present(years):
        avg, pooled = summarise(m, ys)
        k = 2 if m == 'deficit_per_dev' else 1
        out.append([n, f"{label(ys[0])}-{label(ys[-1])}", len(ys), m, round(avg, k), round(pooled, k)])
        line += f"{avg:>13.{k}f} / {pooled:<6.{k}f}"
    print(line)
write_csv('kenya_by_president.csv', ['president', 'FYs', 'n_years', 'measure', 'avg_of_yearly', 'pooled_sum_over_sum'], out)

# ---- sensitivities -----------------------------------------------------
HEAD = ['dev_pct_gdp', 'dev_pct_rev_after_interest', 'dev_pct_rev_after_inherited_int', 'recurrent_balance_pct_rev_after_int']

# (a) ~KSh160bn of FY12/13 development spending booked in FY13/14
#     (source: footnote of the Stats Kenya chart "Development spending has halved as a share of GDP")
R160 = {y: dict(r) for y, r in R.items()}
for y, s in ((2013, -160000), (2014, 160000)):
    R160[y]['dev'] += s; R160[y]['total_exp'] += s; R160[y]['deficit'] += s
# (b) budget authorship: FY13/14 budget passed under Kibaki, FY22/23 under Kenyatta
TERMS_BUDGET = [('Kibaki', 2004, 2014), ('Kenyatta', 2015, 2023), ('Ruto', 2024, 2027)]

sens = []
for case, data, terms in (('baseline', R, TERMS), ('160bn moved back to FY12/13', R160, TERMS),
                          ('FY assigned to president who passed the budget', R, TERMS_BUDGET)):
    for n, ys in terms_present(years, terms):
        for m in HEAD:
            if m == 'dev_pct_rev_after_inherited_int':  # "inherited" depends on where terms start
                avg = sum(100 * data[y]['dev'] / (data[y]['rev'] - inherited_interest(y, data[y], terms))
                          for y in ys) / len(ys)
            else:
                avg, _ = summarise(m, ys, data)
            sens.append([case, n, f"{label(ys[0])}-{label(ys[-1])}", m, round(avg, 1)])
write_csv('kenya_sensitivities.csv', ['case', 'president', 'FYs', 'measure', 'avg_of_yearly'], sens)
print()
for case in dict.fromkeys(s[0] for s in sens):
    print(case)
    for n in [t[0] for t in TERMS]:
        v = [s for s in sens if s[0] == case and s[1] == n]
        if v:
            print(f"  {n:9s} {v[0][2]:12s} " + '  '.join(f"{s[3]}={s[4]}" for s in v))
