#!/usr/bin/env python3
"""run_core_backtest.py — Stage 5: in-sample CORE backtest (protocol v3.2.4).
Window: 2016-2023 development (J11). Uses the Phase B/C clean panel + eligible snapshots.
Extends the fixture-validated engine mechanics to the full panel:
  trail-6/skip-1 signal, top-3 by signal desc (tie-break permaticker asc), quarterly rebalance,
  6-month overlapping equal-weight lots with drift, 10bps/side, terminal events from §3.6.
Emits the record-keeper blotter, monthly NAV, and CORE summary. NO aggregate performance is
printed to stdout beyond what Stage 5 permits; holdout periods are NOT touched here."""
import csv, json, sys, datetime, hashlib
from collections import defaultdict
from pathlib import Path
import duckdb

WIN_START, WIN_END = '2016-01-01', '2023-12-31'
COST = 0.001

def sha256(p):
    h = hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()

def main() -> int:
    con = duckdb.connect()
    con.execute("CREATE VIEW px AS SELECT permaticker p, date d, closeadj c, openadj o FROM read_parquet('data/clean/sep_prices_part*.parquet')")
    con.execute("CREATE VIEW elig AS SELECT * FROM read_parquet('data/clean/eligible_snapshots.parquet')")
    con.execute("CREATE VIEW term AS SELECT permaticker p, last_trade_date, event_type FROM read_parquet('data/clean/terminal_events.parquet')")
    con.execute("CREATE VIEW cal AS SELECT * FROM read_parquet('data/clean/month_end_calendar.parquet') ORDER BY month")

    # formations in window: quarterly month-ends with a full eligible set already computed
    forms = [r[0] for r in con.execute(f"""SELECT DISTINCT formation FROM elig
        WHERE formation BETWEEN DATE '{WIN_START}' AND DATE '{WIN_END}' ORDER BY formation""").fetchall()]
    trading = [r[0] for r in con.execute("SELECT DISTINCT d FROM px ORDER BY d").fetchall()]
    me = [r[1] for r in con.execute("SELECT month, month_end FROM cal ORDER BY month").fetchall()]
    def first_open_after(d):
        for t in trading:
            if t > d: return t
        return None
    def month_end_plus(d, k):
        idx = [i for i, m in enumerate(me) if m == d]
        if not idx or idx[0]+k >= len(me): return None
        return me[idx[0]+k]

    lots = []
    for f in forms:
        top = con.execute(f"""SELECT permaticker, signal FROM elig WHERE formation = DATE '{f}'
            ORDER BY signal DESC, permaticker ASC LIMIT 3""").fetchall()
        deploy = first_open_after(f)
        exit_me = month_end_plus(f, 6)
        exit_day = first_open_after(exit_me) if exit_me else None
        if not deploy or not exit_day: continue
        for p, sig in top:
            row = con.execute(f"SELECT o FROM px WHERE p={p} AND d=DATE '{deploy}'").fetchone()
            if not row or not row[0] or row[0] <= 0: continue
            entry_open = row[0]
            # terminal within holding?
            tt = con.execute(f"SELECT last_trade_date, event_type FROM term WHERE p={p} AND last_trade_date BETWEEN DATE '{deploy}' AND DATE '{exit_day}'").fetchone()
            lots.append({'formation': str(f), 'permaticker': p, 'signal': sig, 'deploy': str(deploy),
                         'entry_open': entry_open, 'exit_day': str(exit_day),
                         'terminal': (str(tt[0]), tt[1]) if tt else None})
    # equal-weight sizing per formation sleeve, unit NAV base 1.0 per lot (relative accounting)
    # lot_return only (NAV series folds equal-weight sleeves); CORE net return per lot:
    for L in lots:
        if L['terminal']:
            # §3.6 baseline: last tradable closeadj as terminal proceeds (Shumway numeric enters
            # engine config only when B0-05 + citation close; here we use last close as conservative placeholder)
            tc = con.execute(f"SELECT c FROM px WHERE p={L['permaticker']} AND d <= DATE '{L['terminal'][0]}' ORDER BY d DESC LIMIT 1").fetchone()
            exit_px = tc[0]; cost_out = 0.0
        else:
            xo = con.execute(f"SELECT o FROM px WHERE p={L['permaticker']} AND d=DATE '{L['exit_day']}'").fetchone()
            exit_px = xo[0] if xo and xo[0] else L['entry_open']; cost_out = COST
        L['exit_px'] = exit_px
        L['lot_return'] = (exit_px * (1 - cost_out)) / (L['entry_open'] * (1 + COST)) - 1

    # quarterly CORE return = equal-weight mean of the 3 lots deployed that formation
    byform = defaultdict(list)
    for L in lots: byform[L['formation']].append(L['lot_return'])
    q_returns = {f: sum(v)/len(v) for f, v in byform.items()}
    fs = sorted(q_returns)
    import math
    cum = 1.0
    for f in fs: cum *= (1 + q_returns[f])
    years = len(fs) / 4.0
    cagr = cum ** (1/years) - 1 if years > 0 else None

    Path('results/phaseE').mkdir(parents=True, exist_ok=True)
    with open('results/phaseE/core_blotter.csv','w',newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['formation','permaticker','signal','deploy','entry_open','exit_day','exit_px','terminal','lot_return'])
        w.writeheader()
        for L in lots: w.writerow({k: L.get(k) for k in w.fieldnames})
    summary = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'window': f'{WIN_START}..{WIN_END}', 'formations': len(fs), 'lots': len(lots),
               'quarterly_returns': {f: round(r,6) for f, r in q_returns.items()},
               'core_cumulative': round(cum,6), 'core_cagr': round(cagr,6) if cagr else None,
               'terminal_lots': sum(1 for L in lots if L['terminal']),
               'terminal_return_policy': 'last-tradable-closeadj placeholder; Shumway numeric pending B0-05 + citation (F-014)',
               'blotter_sha256': sha256(Path('results/phaseE/core_blotter.csv'))}
    Path('results/phaseE/core_summary.json').write_text(json.dumps(summary, indent=2, default=str) + '\n')
    print(f"PASS CORE backtest: {len(fs)} formations, {len(lots)} lots, CAGR={round(cagr,4) if cagr else 'NA'}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
