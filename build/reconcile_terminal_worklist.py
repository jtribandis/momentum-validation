#!/usr/bin/env python3
"""reconcile_terminal_worklist.py — old-vs-new terminal worklist reconciliation with EXPLICIT
denominators (v3.2.4). Every number below names the set it counts. No performance computed."""
import csv, json, sys, datetime
from pathlib import Path
import duckdb

def main() -> int:
    con = duckdb.connect(); con.execute("SET threads TO 1")
    old = json.load(open('results/phaseE/terminal_ledger.json'))
    # OLD set: name-level proximity, pre-vendor-correction classification
    old_rows = [e for e in old['ledger'] if e['in_2016_2023_window']]
    OLD = {(e['permaticker'], e['last_trade_date']) for e in old_rows}

    con.execute("CREATE VIEW dr AS SELECT * FROM read_parquet('results/phaseE/clone_draws.parquet')")
    con.execute("CREATE VIEW te AS SELECT * FROM read_parquet('data/clean/terminal_events.parquet')")
    con.execute("CREATE VIEW el AS SELECT * FROM read_parquet('data/clean/eligible_snapshots.parquet')")
    con.execute("CREATE VIEW px AS SELECT permaticker p, date d, openadj o FROM read_parquet('data/clean/sep_prices_part*.parquet')")
    trading = [str(r[0]) for r in con.execute("SELECT DISTINCT d FROM px ORDER BY d").fetchall()]
    me = [str(r[0]) for r in con.execute("SELECT month_end FROM read_parquet('data/clean/month_end_calendar.parquet') ORDER BY month").fetchall()]
    def foa(d):
        for t in trading:
            if t > d: return t
    def me6(d):
        for i, m in enumerate(me):
            if m == d: return me[i+6] if i+6 < len(me) else None
    forms = [str(r[0]) for r in con.execute("SELECT DISTINCT formation_date FROM dr ORDER BY 1").fetchall()]
    lw = {f: (foa(f), foa(me6(f))) for f in forms if me6(f)}
    term = {r[0]: (str(r[1]), r[2]) for r in con.execute("SELECT permaticker, last_trade_date, event_type FROM te").fetchall()}

    core_sel = {f: [r[0] for r in con.execute(
        f"SELECT permaticker FROM el WHERE formation = DATE '{f}' ORDER BY signal DESC, permaticker ASC LIMIT 3").fetchall()] for f in lw}
    def exposed(f, p):
        dep, ex = lw[f]
        return p in term and dep <= term[p][0] < ex

    CORE_PAIRS = {(f, p) for f, ps in core_sel.items() for p in ps if exposed(f, p)}
    clone_pairs_rows = con.execute("SELECT DISTINCT formation_date, permaticker FROM dr ORDER BY 1,2").fetchall()
    CLONE_PAIRS = {(str(f), p) for f, p in clone_pairs_rows if str(f) in lw and exposed(str(f), p)}
    hits = con.execute("""SELECT d.formation_date, d.permaticker, COUNT(*) n, MIN(d.clone_id) first_id,
        COUNT(DISTINCT d.clone_id) ncl FROM dr d GROUP BY 1,2""").fetchall()
    HIT = {(str(f), p): (n, fid, ncl) for f, p, n, fid, ncl in hits if (str(f), p) in CLONE_PAIRS}
    total_hits = sum(v[0] for v in HIT.values())

    EXPOSED_PAIRS = CORE_PAIRS | CLONE_PAIRS
    EXPOSED_EVENTS = {(p, term[p][0]) for _, p in EXPOSED_PAIRS}
    EXPOSED_PERMS = {p for _, p in EXPOSED_PAIRS}

    # possible pairs = every (formation, eligible name) whose event lands in that lot window
    possible = con.execute("SELECT formation, permaticker FROM el ORDER BY 1,2").fetchall()
    POSSIBLE_PAIRS = {(str(f), p) for f, p in possible if str(f) in lw and exposed(str(f), p)}

    fp = OLD - EXPOSED_EVENTS
    fn = EXPOSED_EVENTS - OLD
    rows = []
    for k in sorted(OLD | EXPOSED_EVENTS):
        p, d = k
        rows.append({'permaticker': p, 'last_trade_date': d,
                     'in_old_111_name_level': k in OLD, 'in_new_exposed_events': k in EXPOSED_EVENTS,
                     'classification': 'FALSE_POSITIVE_OLD_ONLY' if k in fp else ('FALSE_NEGATIVE_NEW_ONLY' if k in fn else 'AGREE'),
                     'new_event_type': term.get(p, (None, None))[1],
                     'in_core_selection': any(pp == p for _, pp in CORE_PAIRS),
                     'in_clone_draws': any(pp == p for _, pp in CLONE_PAIRS)})
    with open('results/phaseE/old_vs_new_terminal_worklist_diff.csv','w',newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

    rep = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'DENOMINATOR_DEFINITIONS': {
        'old_111': 'UNIQUE (permaticker, last_trade_date) TERMINAL EVENTS on names that were EVER eligible with >=1 eligible formation inside 2016-2023. Name-level proximity. Pre-vendor-correction classification. Ignores lot windows and actual draws.',
        'new_61_exposed_events': 'UNIQUE (permaticker, last_trade_date) TERMINAL EVENTS where the event falls inside an ACTUAL lot holding window (deploy <= last_trade < scheduled_exit) for a name actually held by CORE or by >=1 of the 10,000 clones.',
        'new_91_clone_pairs': 'DISTINCT (formation_date, permaticker) CLONE EXPOSURE PAIRS. A single event can appear at multiple formations, so this count is >= the unique-event count. DIFFERENT DENOMINATOR from old_111 - the two were never comparable.',
        'clone_lot_hits': 'TOTAL clone lot instances hitting an exposure pair, summed over all 10,000 clones (a pair drawn by k clones contributes k).',
        'possible_pairs': 'DISTINCT (formation_date, permaticker) pairs over the FULL eligible universe whose event lands in that lot window - the upper bound if every eligible name were held.'},
      'unique_terminal_events': {'old_111_name_level': len(OLD), 'new_exposed': len(EXPOSED_EVENTS),
                                 'false_positives_old_only': len(fp), 'false_negatives_new_only': len(fn)},
      'unique_permatickers': {'old': len({p for p, _ in OLD}), 'new_exposed': len(EXPOSED_PERMS)},
      'formation_permaticker_pairs': {'possible_full_eligible_universe': len(POSSIBLE_PAIRS),
                                      'core_actual': len(CORE_PAIRS), 'clone_actual': len(CLONE_PAIRS)},
      'clone_lot_hits_total': total_hits,
      'RECONCILIATION_NOTE': ('The narrative "old 111 -> new 61, 50 FP, 0 FN" compares UNIQUE TERMINAL EVENTS. '
        'The "91" is DISTINCT CLONE FORMATION-PERMATICKER PAIRS - a different denominator. Both are correct '
        'for their own set; presenting them side by side without denominators was misleading and is corrected here.'),
      'NO_PERFORMANCE_COMPUTED': True}
    Path('results/phaseE/old_vs_new_terminal_worklist_report.json').write_text(json.dumps(rep, indent=2, default=str) + '\n')
    print(json.dumps({k: rep[k] for k in ['unique_terminal_events','unique_permatickers','formation_permaticker_pairs','clone_lot_hits_total']}, indent=2))
    # stash for queue builder
    Path('/tmp/_sets.json').write_text(json.dumps({
        'core_pairs': sorted([[f, p] for f, p in CORE_PAIRS]), 'clone_pairs': sorted([[f, p] for f, p in CLONE_PAIRS]),
        'hits': {f'{f}|{p}': v for (f, p), v in HIT.items()}, 'lw': lw}, default=str))
    return 0

if __name__ == '__main__':
    sys.exit(main())
