#!/usr/bin/env python3
"""build_terminal_exposures.py — mechanically exposure-relevant terminal worklist (v3.2.4).
Steps 8/10/11 of the 2026-07-16 review directive.

Exposure rule: an event is exposure-relevant to a lot iff
    deploy_date <= last_trade_date < scheduled_exit_date
Date triangulation: ACTIONS.date (vendor: LAST TRADE DATE), TICKERS.lastpricedate, and
SEP max date are compared per permaticker; discrepancies are FLAGGED, never silently merged.
ACTIONS.date is NOT a legal completion date and is never labeled as such.

Clone draws are generated with the SAME deterministic seed as the recorded run and hashed
BEFORE any return is computed, then intersected with the worklist. NO performance, NO CAGR,
NO returns are computed anywhere in this file."""
import csv, json, sys, hashlib, random, datetime
from pathlib import Path
import duckdb

WIN = ('2016-01-01', '2023-12-31')
PHASE_F = ('2006-01-01', '2015-12-31')

def main() -> int:
    con = duckdb.connect()
    con.execute("CREATE VIEW te AS SELECT * FROM read_parquet('data/clean/terminal_events.parquet')")
    con.execute("CREATE VIEW el AS SELECT * FROM read_parquet('data/clean/eligible_snapshots.parquet')")
    con.execute("CREATE VIEW px AS SELECT permaticker p, date d, openadj o FROM read_parquet('data/clean/sep_prices_part*.parquet')")
    con.execute("CREATE VIEW tk AS SELECT permaticker, MAX(lastpricedate) lpd FROM read_parquet('data/compact_upload/tickers_universe.parquet') GROUP BY 1")
    con.execute("CREATE VIEW ac AS SELECT * FROM read_parquet('data/clean/actions_clean.parquet')")

    trading = [str(r[0]) for r in con.execute("SELECT DISTINCT d FROM px ORDER BY d").fetchall()]
    me = [str(r[0]) for r in con.execute("SELECT month_end FROM read_parquet('data/clean/month_end_calendar.parquet') ORDER BY month").fetchall()]
    def first_open_after(d):
        for t in trading:
            if t > d: return t
        return None
    def me_plus6(d):
        for i, m in enumerate(me):
            if m == d: return me[i+6] if i+6 < len(me) else None
        return None

    # --- date triangulation (step 8) ---
    tri = con.execute("""
        SELECT t.permaticker, t.last_trade_date AS sep_max_date, t.action_date AS actions_date,
               k.lpd AS tickers_lastpricedate, t.event_type
        FROM te t LEFT JOIN tk k USING (permaticker)""").fetchall()
    disc = []
    for p, sepmax, acd, lpd, et in tri:
        flags = []
        if acd and str(acd) != str(sepmax): flags.append(f'ACTIONS.date({acd}) != SEP_max({sepmax})')
        if lpd and str(lpd) != str(sepmax): flags.append(f'TICKERS.lastpricedate({lpd}) != SEP_max({sepmax})')
        if flags: disc.append({'permaticker': p, 'event_type': et, 'flags': flags})

    # --- formations + CORE selections (selection identity only; NO returns) ---
    def formations(w):
        return [str(r[0]) for r in con.execute(
            f"SELECT DISTINCT formation FROM el WHERE formation BETWEEN DATE '{w[0]}' AND DATE '{w[1]}' ORDER BY formation").fetchall()]
    def lot_windows(forms):
        out = {}
        for f in forms:
            dep = first_open_after(f); xme = me_plus6(f)
            ex = first_open_after(xme) if xme else None
            if dep and ex: out[f] = (dep, ex)
        return out

    forms = formations(WIN)
    lw = lot_windows(forms)
    core_sel = {f: [r[0] for r in con.execute(
        f"SELECT permaticker FROM el WHERE formation = DATE '{f}' ORDER BY signal DESC, permaticker ASC LIMIT 3").fetchall()]
        for f in lw}

    term = {r[0]: (str(r[1]), r[2]) for r in con.execute("SELECT permaticker, last_trade_date, event_type FROM te").fetchall()}

    def exposures(sel_map, tag):
        rows = []
        for f, picks in sel_map.items():
            dep, ex = lw[f]
            for p in picks:
                if p in term and dep <= term[p][0] < ex:
                    rows.append({'window_tag': tag, 'formation': f, 'permaticker': p,
                                 'deploy_date': dep, 'scheduled_exit_date': ex,
                                 'last_trade_date': term[p][0], 'event_type': term[p][1]})
        return rows

    core_exp = exposures(core_sel, 'CORE_2016_2023')

    # --- deterministic clone draws, hashed BEFORE any return (step 10) ---
    summary = json.load(open('results/phaseE/core_summary.json'))
    seed = int(hashlib.sha256((summary['blotter_sha256'] + 'clone-null').encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    N = 10000
    universe = {f: [r[0] for r in con.execute(
        f"SELECT DISTINCT e.permaticker FROM el e JOIN px x ON x.p = e.permaticker AND x.d = DATE '{lw[f][0]}' AND x.o > 0 WHERE e.formation = DATE '{f}'").fetchall()]
        for f in lw}
    draws = []
    for i in range(N):
        for f in sorted(lw):
            picks = rng.sample(universe[f], min(3, len(universe[f])))
            draws.append((i, f, tuple(sorted(picks))))
    draw_blob = '\n'.join(f'{i}|{f}|{",".join(map(str,p))}' for i, f, p in draws)
    draws_sha = hashlib.sha256(draw_blob.encode()).hexdigest()
    Path('results/phaseE/clone_draws.sha256').write_text(json.dumps(
        {'seed': seed, 'clones': N, 'formations': len(lw), 'draw_rows': len(draws),
         'draws_sha256': draws_sha, 'hashed_before_returns': True,
         'note': 'Exact clone selections preserved as a hash; regenerate with this seed to reproduce identically.'}, indent=2) + '\n')

    clone_exp = {}
    for i, f, picks in draws:
        dep, ex = lw[f]
        for p in picks:
            if p in term and dep <= term[p][0] < ex:
                k = (f, p)
                clone_exp.setdefault(k, {'formation': f, 'permaticker': p, 'deploy_date': dep,
                                         'scheduled_exit_date': ex, 'last_trade_date': term[p][0],
                                         'event_type': term[p][1], 'clone_ids_hit': 0})
                clone_exp[k]['clone_ids_hit'] += 1

    # --- Phase F possible exposures (event dates only; NO selection, NO returns, sealed) ---
    ff = formations(PHASE_F); flw = lot_windows(ff)
    pf = []
    for f, (dep, ex) in flw.items():
        elig = [r[0] for r in con.execute(f"SELECT permaticker FROM el WHERE formation = DATE '{f}'").fetchall()]
        for p in elig:
            if p in term and dep <= term[p][0] < ex:
                pf.append({'formation': f, 'permaticker': p, 'deploy_date': dep, 'scheduled_exit_date': ex,
                           'last_trade_date': term[p][0], 'event_type': term[p][1],
                           'note': 'ELIGIBLE-UNIVERSE exposure only; no selection or return computed (period sealed)'})

    def dump(path, rows, fields):
        with open(path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
            for r in rows: w.writerow({k: r.get(k) for k in fields})
    dump('results/phaseE/core_terminal_exposures.csv', core_exp,
         ['window_tag','formation','permaticker','deploy_date','scheduled_exit_date','last_trade_date','event_type'])
    dump('results/phaseE/clone_terminal_exposures.csv', sorted(clone_exp.values(), key=lambda r: (r['formation'], r['permaticker'])),
         ['formation','permaticker','deploy_date','scheduled_exit_date','last_trade_date','event_type','clone_ids_hit'])
    dump('results/phaseE/phaseF_possible_terminal_exposures.csv', pf,
         ['formation','permaticker','deploy_date','scheduled_exit_date','last_trade_date','event_type','note'])
    queue = {}
    for r in core_exp + list(clone_exp.values()) + pf:
        k = (r['permaticker'], r['last_trade_date'])
        queue.setdefault(k, {'permaticker': r['permaticker'], 'last_trade_date': r['last_trade_date'],
                             'event_type': r['event_type'], 'in_core': False, 'in_clones': False, 'in_phaseF': False,
                             'evidence_required': 'SEC 8-K Item 2.01/1.03, merger agreement, exchange ratio, equity recovery'})
    for r in core_exp: queue[(r['permaticker'], r['last_trade_date'])]['in_core'] = True
    for r in clone_exp.values(): queue[(r['permaticker'], r['last_trade_date'])]['in_clones'] = True
    for r in pf: queue[(r['permaticker'], r['last_trade_date'])]['in_phaseF'] = True
    dump('results/phaseE/manual_transaction_review_queue.csv', sorted(queue.values(), key=lambda r: r['last_trade_date']),
         ['permaticker','last_trade_date','event_type','in_core','in_clones','in_phaseF','evidence_required'])

    by_class = {}
    for r in queue.values(): by_class[r['event_type']] = by_class.get(r['event_type'], 0) + 1
    rep = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'date_triangulation_discrepancies': len(disc), 'discrepancy_sample': disc[:10],
           'core_terminal_exposures': len(core_exp),
           'clone_distinct_exposure_pairs': len(clone_exp),
           'clone_total_lot_hits': sum(v['clone_ids_hit'] for v in clone_exp.values()),
           'phaseF_possible_exposures': len(pf),
           'manual_review_queue_size': len(queue), 'manual_review_by_class': by_class,
           'clone_draws_sha256': draws_sha, 'seed': seed,
           'NO_PERFORMANCE_COMPUTED': True}
    Path('results/phaseE/terminal_exposures_report.json').write_text(json.dumps(rep, indent=2, default=str) + '\n')
    print(json.dumps({k: rep[k] for k in ['date_triangulation_discrepancies','core_terminal_exposures',
        'clone_distinct_exposure_pairs','clone_total_lot_hits','phaseF_possible_exposures',
        'manual_review_queue_size','manual_review_by_class']}, indent=2))
    return 0

if __name__ == '__main__':
    sys.exit(main())
