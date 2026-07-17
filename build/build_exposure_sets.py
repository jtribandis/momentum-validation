#!/usr/bin/env python3
"""build_exposure_sets.py — deterministic, versioned terminal-exposure sets (schema v2).

Computes lot windows and CORE/clone exposure pairs from DECLARED REPOSITORY INPUTS ONLY.
Clone selections are READ from the frozen draw artifact — never regenerated here.
No returns, no performance, no sealed-period evaluation.

Guarantees:
  - every input is declared and hard-fails if missing (no silent omission)
  - created_utc lives in the MANIFEST only; the artifact itself is timestamp-free (F-024)
  - FIRST terminal event inside a lot interval is the applicable one; later events are
    preserved as related evidence only
"""
import json, sys, hashlib, datetime, glob
from pathlib import Path
import duckdb

SCHEMA_VERSION = 'terminal_exposure_sets_v2'
WIN = ('2016-01-01', '2023-12-31'); PHASE_F = ('2006-01-01', '2015-12-31')
CONFIG_INPUTS = ['config/core_frozen.yaml', 'config/terminal_policy.yaml',
                 'config/risk_limits.yaml', 'config/tolerance_contract.yaml']
DATA_INPUTS = ['data/clean/eligible_snapshots.parquet', 'data/clean/terminal_events.parquet',
               'data/clean/month_end_calendar.parquet', 'results/phaseE/clone_draws.parquet']
CONTROLLING_PARAMS = {
    'development_window': WIN, 'phaseF_window': PHASE_F, 'holding_months': 6,
    'rebalance_months': [3, 6, 9, 12], 'selection_count': 3,
    'execution_timing': 'first tradable open after formation month-end; scheduled exit = first '
                        'tradable open after month_end(formation)+6',
    'identity_rule': 'permaticker (data_fidelity_contract)',
    'first_terminal_event_rule': 'earliest valid event inside [deploy, scheduled_exit); later events = related evidence only'}

def byte_sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()

def describe(con, p):
    rows = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{p}')").fetchall()
    schema = [(r[0], r[1]) for r in rows]
    n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{p}')").fetchone()[0]
    return hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest(), int(n)

def main() -> int:
    con = duckdb.connect(); con.execute('SET threads TO 1')
    parts = sorted(glob.glob('data/clean/sep_prices_part*.parquet'))   # stable filename order
    if not parts: raise SystemExit('HARD FAIL: no sep_prices_part*.parquet found')
    declared = DATA_INPUTS + parts + CONFIG_INPUTS
    missing = [p for p in declared if not Path(p).exists()]
    if missing: raise SystemExit(f'HARD FAIL: declared inputs missing: {missing}')

    for v, p in [('el', 'data/clean/eligible_snapshots.parquet'), ('te', 'data/clean/terminal_events.parquet'),
                 ('dr', 'results/phaseE/clone_draws.parquet')]:
        con.execute(f"CREATE VIEW {v} AS SELECT * FROM read_parquet('{p}')")
    con.execute("CREATE VIEW px AS SELECT permaticker p, date d, openadj o FROM read_parquet('data/clean/sep_prices_part*.parquet')")
    trading = [str(r[0]) for r in con.execute('SELECT DISTINCT d FROM px ORDER BY d').fetchall()]
    me = [str(r[0]) for r in con.execute("SELECT month_end FROM read_parquet('data/clean/month_end_calendar.parquet') ORDER BY month").fetchall()]
    def foa(d):
        for t in trading:
            if t > d: return t
    def mp6(d):
        for i, m in enumerate(me):
            if m == d: return me[i + 6] if i + 6 < len(me) else None
    def windows(w):
        out = {}
        for f in [str(r[0]) for r in con.execute(
            f"SELECT DISTINCT formation FROM el WHERE formation BETWEEN DATE '{w[0]}' AND DATE '{w[1]}' ORDER BY formation").fetchall()]:
            dep = foa(f); xm = mp6(f); ex = foa(xm) if xm else None
            if dep and ex: out[f] = {'deploy': dep, 'scheduled_exit': ex}
        return out
    lw_dev, lw_f = windows(WIN), windows(PHASE_F)

    term = {}
    for p, ltd, et, ad in con.execute(
        'SELECT permaticker, last_trade_date, event_type, action_date FROM te ORDER BY permaticker, last_trade_date').fetchall():
        term.setdefault(p, []).append({'last_trade_date': str(ltd), 'event_type': et,
                                       'action_date': str(ad) if ad else None})

    multi = {'dev': 0, 'phaseF': 0, 'examples': []}
    def expose(pairs, lw, tag, bucket):
        out = []
        for f, p in sorted(pairs):
            if f not in lw: continue
            dep, ex = lw[f]['deploy'], lw[f]['scheduled_exit']
            inside = sorted([e for e in term.get(p, []) if dep <= e['last_trade_date'] < ex],
                            key=lambda e: (e['last_trade_date'], e['event_type']))
            if not inside: continue
            if len(inside) > 1:
                multi[bucket] += 1
                multi['examples'].append({'formation': f, 'permaticker': p, 'n_events': len(inside),
                                          'events': inside})
            first, later = inside[0], inside[1:]
            out.append({'window_tag': tag, 'formation': f, 'permaticker': p, 'deploy_date': dep,
                        'scheduled_exit_date': ex, **first,
                        'terminal_event_selection_rule': 'FIRST_EVENT_IN_INTERVAL',
                        'events_in_interval': len(inside),
                        'related_evidence_only_events': later})
        return out

    core_pairs = {(f, r[0]) for f in lw_dev for r in con.execute(
        f"SELECT permaticker FROM el WHERE formation = DATE '{f}' ORDER BY signal DESC, permaticker ASC LIMIT 3").fetchall()}
    clone_hits = {}
    for f, p, nc, nl, first in con.execute("""SELECT formation_date, permaticker, COUNT(DISTINCT clone_id),
        COUNT(*), MIN(clone_id) FROM dr GROUP BY 1,2 ORDER BY 1,2""").fetchall():
        clone_hits[(str(f), p)] = {'affected_clone_count': nc, 'clone_lot_hits': nl, 'first_clone_id': first}
    pf_pairs = {(f, r[0]) for f in lw_f for r in con.execute(
        f"SELECT permaticker FROM el WHERE formation = DATE '{f}' ORDER BY permaticker").fetchall()}

    core_exp = expose(core_pairs, lw_dev, 'DEV_2016_2023_CORE', 'dev')
    clone_exp = expose(set(clone_hits), lw_dev, 'DEV_2016_2023_ACTUAL_CLONE_EXPOSURE', 'dev')
    pf_exp = expose(pf_pairs, lw_f, 'PHASEF_2006_2015_POSSIBLE_ELIGIBLE_UNIVERSE_ONLY', 'phaseF')
    exposed = {(e['formation'], e['permaticker']) for e in clone_exp}

    sets = {'schema_version': SCHEMA_VERSION,
            'controlling_parameters': CONTROLLING_PARAMS,
            'lot_windows_dev': lw_dev, 'lot_windows_phaseF': lw_f,
            'core_exposures': core_exp, 'clone_exposures': clone_exp,
            'phaseF_possible_exposures': pf_exp,
            'clone_hit_stats': {f'{f}|{p}': dict(v, semantic='clones drawing this name at this formation; '
                'identical to clones exposed to its terminal event (shared lot window)')
                for (f, p), v in sorted(clone_hits.items()) if (f, p) in exposed},
            'clone_hit_stats_scope': 'EXPOSED_PAIRS_ONLY',
            'multi_terminal_event_intervals': {'dev': multi['dev'], 'phaseF': multi['phaseF'],
                'examples': multi['examples'][:20],
                'structural_note': ('terminal_events.parquet currently carries at most ONE row per '
                    'permaticker (build_terminal_events.py collapses by priority), so multi-event '
                    'intervals are structurally impossible at this vintage. The FIRST_EVENT_IN_INTERVAL '
                    'rule is implemented and tested regardless, so a future multi-row terminal ledger '
                    'cannot silently change exposure selection.')},
            'returns_computed': False}
    art = 'results/phaseE/terminal_exposure_sets.json'
    Path(art).write_text(json.dumps(sets, indent=2, sort_keys=True) + '\n')
    content = hashlib.sha256(json.dumps(sets, sort_keys=True).encode()).hexdigest()

    def rec(p):
        e = {'path': p, 'byte_sha256': byte_sha(p)}
        if p.endswith('.parquet'):
            s, n = describe(con, p); e['schema_sha256'] = s; e['row_count'] = n
        else:
            e['schema_sha256'] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
            e['row_count'] = sum(1 for _ in open(p))
        return e
    Path('results/phaseE/terminal_exposure_sets_manifest.json').write_text(json.dumps({
        'schema_version': SCHEMA_VERSION,
        'artifact': art, 'artifact_byte_sha256': byte_sha(art), 'output_content_sha256': content,
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'generator_file': 'build/build_exposure_sets.py',
        'generator_blob_sha': byte_sha('build/build_exposure_sets.py'),
        'exact_command': 'python build/build_exposure_sets.py',
        'controlling_parameters': CONTROLLING_PARAMS,
        'inputs': [rec(p) for p in declared],
        'counts': {'core_exposures': len(core_exp), 'clone_exposures': len(clone_exp),
                   'phaseF_possible_exposures': len(pf_exp),
                   'multi_event_intervals_dev': multi['dev'], 'multi_event_intervals_phaseF': multi['phaseF']},
        'timestamp_excluded_from_artifact': True, 'no_scratch_dependency': True}, indent=2) + '\n')
    print(f"PASS exposure sets v2: core={len(core_exp)} clone={len(clone_exp)} phaseF={len(pf_exp)} "
          f"multi_dev={multi['dev']} multi_phaseF={multi['phaseF']} content={content[:16]}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
