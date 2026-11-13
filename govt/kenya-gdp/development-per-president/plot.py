"""All charts. Run after calc.py, nb.py and principal.py.
uv run --with matplotlib python plot.py
"""
import csv, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from common import COLORS

BG = '#4a4a4a'


def load(p):
    return list(csv.DictReader(open(p)))


def chart(fname, rows, col, title, subtitle, foot, line=None, line_label=None, ylim=None, fmt='{:.0f}', unit='%'):
    fy = [r['FY'] for r in rows]; v = [float(r[col]) for r in rows]; pres = [r['president'] for r in rows]
    groups = []
    for i, p in enumerate(pres):
        if not groups or groups[-1][0] != p: groups.append([p, i, i + 1])
        else: groups[-1][2] = i + 1
    lo = min(0, min(v)) * 1.15; hi = ylim or max(v + (line or [0])) * 1.35
    fig, ax = plt.subplots(figsize=(12, 6.5)); fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
    for p, a, b in groups:
        c = COLORS[p]; x = range(a, b); ax.bar(x, v[a:b], color=c)
        m = sum(v[a:b]) / (b - a); ax.hlines(m, a - .4, b - .6, colors='white', linestyles='--')
        extra = ''
        if line: extra = f"\n{line_label.split(' as ')[0] if line_label else ''} avg {sum(line[a:b])/(b-a):.0f}%"
        ax.text((a + b - 1) / 2, hi * .86, f"{p} ({b-a} yrs)\nAverage {fmt.format(m) if fmt!='{:.0f}' else f'{m:.1f}'}{unit}{extra}",
                ha='center', va='center', color=c, fontsize=10)
        for i in x:
            ax.text(i, v[i] + (hi * .01 if v[i] >= 0 else -hi * .045), fmt.format(v[i]), ha='center', color='white', fontsize=8)
        if a: ax.axvline(a - .5, color='white', ls=':', lw=1)
    if line:
        ax.plot(range(len(line)), line, color='white', lw=1.5, marker='o', ms=3, label=line_label)
        ax.legend(loc='upper left', bbox_to_anchor=(0, .72), facecolor=BG, labelcolor='white', frameon=False)
    if lo < 0: ax.axhline(0, color='white', lw=.8)
    ax.set_xticks(range(len(fy))); ax.set_xticklabels(fy, rotation=45, color='white', fontsize=8)
    ax.tick_params(colors='white'); ax.set_ylim(lo, hi)
    for s in ax.spines.values(): s.set_visible(False)
    fig.suptitle(title, color='white', fontsize=15, x=.02, ha='left')
    ax.set_title(subtitle, color='white', fontsize=9, loc='left')
    fig.text(.02, .01, foot, color='white', fontsize=7.5)
    plt.tight_layout(rect=(0, .025 * (foot.count('\n') + 1) + .02, 1, 1)); plt.savefig(fname, dpi=130, facecolor=fig.get_facecolor()); plt.close(fig)
    print('wrote', fname)


d = load('kenya_dev_vs_net_revenue.csv')
SRC = "Source: CBK, Composition of Government Revenue and Expenditure (June cumulative, commitment basis)."
NOTE = "Each FY assigned to the president in office for most of it. ~KSh160bn of FY12/13 spending booked in FY13/14 (not adjusted)."

chart('kenya-devt-spending-pct-gdp.png', d, 'dev_pct_gdp',
      'Development spending as a share of GDP (independent reproduction of a Stats Kenya chart)',
      'National govt development expenditure ÷ nominal GDP, %, by FY (excludes county transfers)',
      SRC + " GDP: IMF WEO (Oct 2026), KSh, FY = mean of two calendar years; 2026 is an IMF projection.\n" + NOTE,
      fmt='{:.1f}')

chart('kenya-devt-spending-after-interest.png', d, 'dev_pct_rev_after_interest',
      'Development spending as a share of revenue left after interest',
      'National govt development expenditure ÷ (tax + non-tax revenue − domestic & foreign interest), %, by FY',
      SRC + " Excludes grants and county transfers. Principal not deducted.\n" + NOTE,
      line=[float(r['interest_pct_rev']) for r in d], line_label='Interest as % of revenue')

chart('kenya-devt-spending-after-inherited-interest.png', d, 'dev_pct_rev_after_inherited_int',
      'Development spending as a share of revenue left after inherited interest',
      'National govt development expenditure ÷ (revenue − interest on debt inherited at start of term), %, by FY',
      SRC + " \n"
      "Inherited interest = interest × (debt at start of term ÷ debt at start of FY); assumes old and new debt cost the same.\n"
      "Interest on a president's own new borrowing is NOT deducted. " + NOTE,
      line=[float(r['inherited_interest_pct_rev']) for r in d], line_label='Inherited interest as % of revenue')

chart('kenya-recurrent-balance.png', d, 'recurrent_balance_pct_rev_after_int',
      'Recurrent balance: did borrowing pay for day-to-day spending?',
      '(Revenue + grants − recurrent spending − county transfers) ÷ (revenue − interest), %, by FY.  '
      'Below zero = borrowing paid for recurrent spending',
      SRC + "\nEquals (development − deficit) ÷ (revenue − interest); deficit = total expenditure − revenue − grants (commitment basis).\n"
      "Not a measure of development effort: development spending cancels out. " + NOTE)

p = load('kenya_dev_after_interest_and_principal.csv')
chart('kenya-devt-spending-after-interest-and-principal.png', p, 'dev_pct_rev_after_int_and_ext_principal',
      'Development spending as a share of revenue left after interest and external principal (illustrative)',
      'National govt development expenditure ÷ (revenue − interest − external principal repayments), %, by FY',
      "Sources: CBK; World Bank IDS DT.AMT.DEPS.CD (public external principal, USD, calendar year) at WB average KSh per USD, FY = mean of two calendar years;\n"
      "FY25/26 uses 2025 only. Domestic principal excluded (mostly rolled-over T-bills/bonds). Most external principal was refinanced, so this double-counts.",
      line=[float(r['debt_service_pct_rev']) for r in p], line_label='Interest + external principal as % of revenue')
