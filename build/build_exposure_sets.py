#!/usr/bin/env python3
"""build_exposure_sets.py — deterministic, versioned terminal-exposure sets (review item 2).
Replaces the undocumented scratch-file dependency (formerly a temp-dir JSON). Computes lot windows and CORE/clone
exposure pairs from DECLARED REPOSITORY INPUTS ONLY and emits a hashed, schema-validated
artifact. Clone selections are READ from results/phaseE/clone_draws.parquet (the frozen draw
artifact) - never regenerated here. No returns, no performance."""
import json, sys, hashlib, datetime
from pathlib import Path
import duckdb

WIN = ('2016-01-01', '2023-12-31'); PHASE_F = ('2006-01-01', '2015-12-31')
INPUTS = ['data/clean/eligible_snapshots.parquet', 'data/clean/terminal_events.parquet',
          'data/clean/month_end_calendar.parquet', 'results/phaseE/clone_draws.parquet']

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''): h.update(c)
    return h.hexdigest()

def main() -> int:
    con = duckdb.connect(); con.execute('SET threads TO 1')
    for v, p in [('el','data/clean/eligible_snapshots.parquet'), ('te','data/clean/terminal_events.parquet'),
                 ('dr','results/phaseE/clone_draws.parquet')]:
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

    term = {}   # permaticker -> list of events (event-level, review item 3: never collapse)
    for p, ltd, et, ad in con.execute('SELECT permaticker, last_trade_date, event_type, action_date FROM te ORDER BY permaticker, last_trade_date').fetchall():
        term.setdefault(p, []).append({'last_trade_date': str(ltd), 'event_type': et,
                                       'action_date': str(ad) if ad else None})

    def expose(pairs, lw, tag):
        out = []
        for f, p in sorted(pairs):
            if f not in lw: continue
            dep, ex = lw[f]['deploy'], lw[f]['scheduled_exit']
            for e in term.get(p, []):
                if dep <= e['last_trade_date'] < ex:
                    out.append({'window_tag': tag, 'formation': f, 'permaticker': p, 'deploy_date': dep,
                                'scheduled_exit_date': ex, **e})
        return out

    core_pairs = {(f, r[0]) for f in lw_dev for r in con.execute(
        f"SELECT permaticker FROM el WHERE formation = DATE '{f}' ORDER BY signal DESC, permaticker ASC LIMIT 3").fetchall()}
    clone_hits = {}
    for f, p, n_clones, n_lots, first in con.execute("""
        SELECT formation_date, permaticker, COUNT(DISTINCT clone_id), COUNT(*), MIN(clone_id)
        FROM dr GROUP BY 1,2 ORDER BY 1,2""").fetchall():
        clone_hits[(str(f), p)] = {'affected_clone_count': n_clones, 'clone_lot_hits': n_lots, 'first_clone_id': first}
    clone_pairs = set(clone_hits)
    pf_pairs = {(f, r[0]) for f in lw_f for r in con.execute(
        f"SELECT permaticker FROM el WHERE formation = DATE '{f}' ORDER BY permaticker").fetchall()}

    sets = {'schema_version': 'terminal_exposure_sets_v1',
            'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'lot_windows_dev': lw_dev, 'lot_windows_phaseF': lw_f,
            'core_exposures': expose(core_pairs, lw_dev, 'DEV_2016_2023_CORE'),
            'clone_exposures': expose(clone_pairs, lw_dev, 'DEV_2016_2023_ACTUAL_CLONE_EXPOSURE'),
            'phaseF_possible_exposures': expose(pf_pairs, lw_f, 'PHASEF_2006_2015_POSSIBLE_ELIGIBLE_UNIVERSE_ONLY'),
            'clone_hit_stats': {f'{f}|{p}': v for (f, p), v in sorted(clone_hits.items())},
            'returns_computed': False}
    Path('results/phaseE/terminal_exposure_sets.json').write_text(json.dumps(sets, indent=2, sort_keys=True) + '\n')
    content = hashlib.sha256(json.dumps(sets, sort_keys=True).encode()).hexdigest()
    Path('results/phaseE/terminal_exposure_sets_manifest.json').write_text(json.dumps({
        'artifact': 'results/phaseE/terminal_exposure_sets.json', 'schema_version': 'terminal_exposure_sets_v1',
        'generator_file': 'build/build_exposure_sets.py',
        'generator_blob_sha': hashlib.sha256(open('build/build_exposure_sets.py','rb').read()).hexdigest(),
        'input_paths': INPUTS, 'input_sha256': {p: sha(p) for p in INPUTS if Path(p).exists()},
        'output_content_sha256': content,
        'counts': {'core_exposures': len(sets['core_exposures']), 'clone_exposures': len(sets['clone_exposures']),
                   'phaseF_possible_exposures': len(sets['phaseF_possible_exposures'])},
        'created_utc': sets['created_utc'], 'no_tmp_dependency': True}, indent=2) + '\n')
    print(f"PASS exposure sets: core={len(sets['core_exposures'])} clone={len(sets['clone_exposures'])} "
          f"phaseF={len(sets['phaseF_possible_exposures'])} content={content[:16]}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
