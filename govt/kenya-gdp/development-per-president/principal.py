"""Illustration only: also subtract EXTERNAL principal repayments from revenue.

Output: kenya_dev_after_interest_and_principal.csv
"""
from common import *

R = load_rev(); P, last = load_ext_principal()
years = sorted(R)
out = []
for y in years:
    r = R[y]; pr = P(y)
    out.append([label(y), president(y), round(r['rev']), round(r['interest']), round(pr), round(r['dev']),
                round(100 * (r['interest'] + pr) / r['rev'], 1), round(100 * r['dev'] / (r['rev'] - r['interest']), 1),
                round(100 * r['dev'] / (r['rev'] - r['interest'] - pr), 1)])
write_csv('kenya_dev_after_interest_and_principal.csv',
          ['FY', 'president', 'revenue_KShm', 'interest_KShm', 'ext_principal_KShm_est', 'dev_KShm',
           'debt_service_pct_rev', 'dev_pct_rev_after_int', 'dev_pct_rev_after_int_and_ext_principal'], out)
print(f"external principal: latest calendar year with data = {last}; later years reuse it")
for n, ys in terms_present(years):
    sel = [o for o in out if o[1] == n]
    m = lambda k: sum(o[k] for o in sel) / len(sel)
    print(f"{n:9s} debt service {m(6):4.1f}% of rev | dev/(rev-int-ext principal) {m(8):4.1f}% | after interest only {m(7):4.1f}%")
