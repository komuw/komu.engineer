"""Borrowing per term, measured two ways.

1. change in the CBK debt stock (includes exchange-rate revaluation of external debt)
2. the fiscal deficit from rev.csv: total expenditure - revenue - grants
   (what actually had to be borrowed; no exchange-rate effect)

Output: kenya_net_borrowing.csv
"""
from common import *

R = load_rev(); D = load_debt()
years = sorted(R)
rows = []
for y in years:
    a, b, r = D[y - 1], D[y], R[y]
    ch = b['total'] - a['total']
    rows.append([label(y), president(y), round(a['total']), round(b['total']), round(ch),
                 round(b['dom'] - a['dom']), round(b['ext'] - a['ext']), round(r['deficit']),
                 round(ch - r['deficit']), round(r['dev']),
                 round(100 * (r['dev'] - r['deficit']) / (r['rev'] - r['interest']), 1)])
write_csv('kenya_net_borrowing.csv',
          ['FY', 'president', 'debt_start_KShm', 'debt_end_KShm', 'debt_change_KShm', 'dom_change_KShm',
           'ext_change_KShm', 'deficit_KShm', 'debt_change_minus_deficit_KShm', 'dev_KShm',
           'recurrent_balance_pct_rev_after_int'], rows)

for row in rows:
    print(f"{row[0]} debtΔ={row[4]/1e3:6.0f}bn deficit={row[7]/1e3:6.0f}bn (gap {row[8]/1e3:5.0f}) dev={row[9]/1e3:5.0f}bn")
print()
for n, ys in terms_present(years):
    ch = D[ys[-1]]['total'] - D[ys[0] - 1]['total']
    de = sum(R[y]['deficit'] for y in ys); dev = sum(R[y]['dev'] for y in ys)
    print(f"{n:9s} debt {D[ys[0]-1]['total']/1e6:5.2f}tn -> {D[ys[-1]]['total']/1e6:5.2f}tn  "
          f"debt added {ch/1e6:4.2f}tn  deficits {de/1e6:4.2f}tn  dev {dev/1e6:4.2f}tn  "
          f"debt added/dev {ch/dev:4.2f}  deficit/dev {de/dev:4.2f}")
