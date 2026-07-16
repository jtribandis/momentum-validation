#!/usr/bin/env python3
"""momentum_engine_py.py — G7 Python reference engine (protocol v3.2.4).
Computes the golden fixture's 77 values from fixtures/golden_v2/inputs/ ONLY.
No value from expected_outputs_SIGNED.csv is read here — the comparator does the diff."""
import csv, sys
from collections import defaultdict
from pathlib import Path

IN = Path('fixtures/golden_v2/inputs')

def load():
    px = defaultdict(dict)          # px[permaticker][date_str] = closeadj
    for r in csv.DictReader(open(IN/'month_end_prices.csv')):
        px[int(r['permaticker'])][r['month_end_date']] = float(r['closeadj'])
    op = defaultdict(dict)
    for r in csv.DictReader(open(IN/'opens.csv')):
        op[int(r['permaticker'])][r['date']] = float(r['openadj'])
    term = {int(r['permaticker']): (r['event_date'], float(r['cash_per_share']))
            for r in csv.DictReader(open(IN/'terminal_events.csv'))}
    cfg = {r['param']: r['value'] for r in csv.DictReader(open(IN/'fixture_config.csv'))}
    return px, op, term, cfg

def main() -> int:
    px, op, term, cfg = load()
    COST = float(cfg['cost_bps_per_side']) / 10000.0
    perms = sorted(px)
    open_dates = sorted({d for p in op for d in op[p]})   # actual deploy/exit days from inputs
    dep_of = {'F1': open_dates[0], 'F2': open_dates[1], 'F3': open_dates[2]}
    ext_of = {'F1': open_dates[2], 'F2': open_dates[3], 'F3': open_dates[4]}
    formations = [('F1','2020-03-31','2020-02-28','2019-08-30',dep_of['F1'],ext_of['F1']),
                  ('F2','2020-06-30','2020-05-29','2019-11-29',dep_of['F2'],ext_of['F2']),
                  ('F3','2020-09-30','2020-08-31','2020-02-28',dep_of['F3'],ext_of['F3'])]
    out = []
    signals, top3 = {}, {}
    for fid, fdate, m1, m7, dep, ext in formations:
        sig = {p: px[p][m1]/px[p][m7] - 1 for p in perms if m1 in px[p] and m7 in px[p]}
        signals[fid] = sig
        ranked = sorted(sig, key=lambda p: (-sig[p], p))   # desc signal, then permaticker ASC
        top3[fid] = ranked[:3]
        for p in perms:
            out.append(('signal', fdate, str(p), 'signal_6dp', f"{sig[p]:.6f}"))
        out.append(('selection', fdate, '', 'top3_permatickers_in_rank_order', ','.join(map(str, top3[fid]))))

    # lots
    lots = {}   # (fid, perm) -> dict
    sleeveA_F1_proceeds = 0.0
    for fid, fdate, m1, m7, dep, ext in formations:
        if fid == 'F1': allocs = {p: 150000.0/3 for p in top3['F1']}
        elif fid == 'F2': allocs = {p: 150000.0/3 for p in top3['F2']}
        else: allocs = {p: sleeveA_F1_proceeds/3 for p in top3['F3']}
        for p in allocs:
            o = op[p][dep]
            alloc = allocs[p]
            shares = alloc / (o * (1 + COST))
            entry_cost = shares * o * COST
            if p in term and term[p][0] > dep and term[p][0] < ext:
                exit_val = shares * term[p][1]; kind = 'terminal_cash_2dp'
            else:
                exit_val = shares * op[p][ext] * (1 - COST); kind = 'exit_proceeds_2dp'
            lot_ret = exit_val / alloc - 1
            lots[(fid, p)] = dict(shares=shares, entry_cost=entry_cost, exit_val=exit_val,
                                  kind=kind, lot_ret=lot_ret, dep=dep, ext=ext, alloc=alloc)
            if fid == 'F1': sleeveA_F1_proceeds += exit_val
        if fid == 'F1':
            pass
    # template lot order: F1 in rank order, F2 in rank order, F3 in rank order
    for fid in ('F1','F2','F3'):
        for p in top3[fid]:
            L = lots[(fid, p)]
            fd = dict(formations := None) if False else None
            out.append(('lot', fid, str(p), 'shares_6dp', f"{L['shares']:.6f}"))
            out.append(('lot', fid, str(p), 'entry_cost_2dp', f"{L['entry_cost']:.2f}"))
            out.append(('lot', fid, str(p), L['kind'], f"{L['exit_val']:.2f}"))
            out.append(('lot', fid, str(p), 'lot_return_6dp', f"{L['lot_ret']:.6f}"))

    # NAV
    me_dates = sorted({d for p in px for d in px[p]})
    nav_dates = [d for d in me_dates if '2020-03-31' <= d <= '2021-03-31']
    ge_term_date, ge_cash_px = term[900005]
    for d in nav_dates:
        nav = 0.0
        # sleeve cash before deployments
        if d < '2020-04-01': nav += 150000.0            # sleeve A pre-F1
        if d < '2020-07-01': nav += 150000.0            # sleeve B pre-F2
        for (fid, p), L in lots.items():
            active = L['dep'] <= d < L['ext']
            if not active: continue
            if p in term and term[p][0] <= d:
                nav += L['exit_val']                    # terminal cash held at 0%
            else:
                nav += L['shares'] * px[p][d]
        # matured sleeves' cash between exit and redeploy / after final exit
        if ext_of['F2'] <= d:                            # sleeve B fully cash after F2 exit
            nav += sum(L['exit_val'] for (fid, p), L in lots.items() if fid == 'F2')
        out.append(('nav', d, '', 'total_nav_2dp', f"{nav:.2f}"))
    final = sum(L['exit_val'] for (fid, p), L in lots.items() if fid == 'F3')
    final += sum(L['exit_val'] for (fid, p), L in lots.items() if fid == 'F2')
    out.append(('nav', '2021-04-01', '', 'final_nav_after_F3_exit_2dp', f"{final:.2f}"))

    with open('results/phaseE/engine_outputs_py.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['section','formation_or_date','permaticker','field','value'])
        w.writerows(out)
    print(f'PASS engine run: {len(out)} values -> results/phaseE/engine_outputs_py.csv')
    return 0

if __name__ == '__main__':
    Path('results/phaseE').mkdir(parents=True, exist_ok=True)
    sys.exit(main())
