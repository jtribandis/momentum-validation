#!/usr/bin/env python3
"""build_clone_draws.py — preserve EXACT clone draws (v3.2.4; review item 1).
Every eligible universe is ORDER BY permaticker before sampling: seeded RNG output depends on
list order, so unordered SQL made the draws nondeterministic despite a fixed seed (F-018).
Emits results/phaseE/clone_draws.parquet + a schema/version manifest. NO returns computed."""
import json, sys, hashlib, random, datetime
from pathlib import Path
import duckdb

WIN = ('2016-01-01', '2023-12-31')
N_CLONES = 10000
RNG_ALGO = 'python-random.Random.sample (Mersenne Twister MT19937)'
RNG_VER = f'CPython {sys.version_info.major}.{sys.version_info.minor}'

def main() -> int:
    con = duckdb.connect()
    con.execute("CREATE VIEW el AS SELECT * FROM read_parquet('data/clean/eligible_snapshots.parquet')")
    con.execute("CREATE VIEW px AS SELECT permaticker p, date d, openadj o FROM read_parquet('data/clean/sep_prices_part*.parquet')")
    trading = [str(r[0]) for r in con.execute("SELECT DISTINCT d FROM px ORDER BY d").fetchall()]
    me = [str(r[0]) for r in con.execute("SELECT month_end FROM read_parquet('data/clean/month_end_calendar.parquet') ORDER BY month").fetchall()]
    def first_open_after(d):
        for t in trading:
            if t > d: return t
    def me_plus6(d):
        for i, m in enumerate(me):
            if m == d: return me[i+6] if i+6 < len(me) else None
    forms = [str(r[0]) for r in con.execute(
        f"SELECT DISTINCT formation FROM el WHERE formation BETWEEN DATE '{WIN[0]}' AND DATE '{WIN[1]}' ORDER BY formation").fetchall()]
    lw = {}
    for f in forms:
        dep = first_open_after(f); xm = me_plus6(f); ex = first_open_after(xm) if xm else None
        if dep and ex: lw[f] = (dep, ex)
    forms = sorted(lw)

    # ORDER BY permaticker is MANDATORY: seeded sample() is order-dependent (F-018)
    universe, snap_hash = {}, {}
    for f in forms:
        u = [r[0] for r in con.execute(f"""
            SELECT DISTINCT e.permaticker FROM el e
            JOIN px x ON x.p = e.permaticker AND x.d = DATE '{lw[f][0]}' AND x.o > 0
            WHERE e.formation = DATE '{f}' ORDER BY e.permaticker""").fetchall()]
        if len(u) < 3:
            raise SystemExit(f'HARD FAIL (frozen policy undersized_universe_policy): formation {f} '
                             f'has {len(u)} eligible names; 3 required. Never silently sample fewer.')
        universe[f] = u
        snap_hash[f] = hashlib.sha256(','.join(map(str, u)).encode()).hexdigest()

    summary = json.load(open('results/phaseE/core_summary.json'))
    seed = int(hashlib.sha256((summary['blotter_sha256'] + 'clone-null').encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    rows = []
    for cid in range(N_CLONES):
        for f in forms:
            picks = rng.sample(universe[f], min(3, len(universe[f])))
            for rk, p in enumerate(picks, start=1):
                rows.append((cid, f, rk, p, snap_hash[f], len(universe[f]), str(seed), RNG_ALGO, RNG_VER))
    import csv as _csv, tempfile, os
    tmp = tempfile.NamedTemporaryFile('w', suffix='.csv', delete=False, newline='')
    w = _csv.writer(tmp)
    w.writerow(['clone_id','formation_date','rank_position','permaticker','eligible_snapshot_hash',
                'eligible_universe_size','seed','rng_algorithm','rng_version'])
    w.writerows(sorted(rows, key=lambda x: (x[0], x[1], x[2])))
    tmp.close()
    # Explicit column types: read_csv_auto inferred `seed` as DOUBLE, silently truncating
    # 12878176638248399935 -> 1.28781766382484e+19 (F-020). Seeds are IDENTIFIERS, not numbers.
    con.execute(f"""COPY (SELECT * FROM read_csv('{tmp.name}', header=true, columns={{
        'clone_id':'BIGINT','formation_date':'DATE','rank_position':'INTEGER','permaticker':'BIGINT',
        'eligible_snapshot_hash':'VARCHAR','eligible_universe_size':'INTEGER','seed':'VARCHAR',
        'rng_algorithm':'VARCHAR','rng_version':'VARCHAR'}})
        ORDER BY clone_id, formation_date, rank_position)
        TO 'results/phaseE/clone_draws.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)""")
    os.unlink(tmp.name)
    # content hash = canonical sort of the logical rows (parquet bytes may vary; content must not)
    # content hash covers ALL NINE columns (review item 4), not just the first four
    canon = '\n'.join('|'.join(map(str, row)) for row in sorted(rows, key=lambda x: (x[0], x[1], x[2])))
    content_hash = hashlib.sha256(canon.encode()).hexdigest()
    man = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'artifact': 'results/phaseE/clone_draws.parquet', 'schema_version': 'clone_draws_v1',
           'columns': ['clone_id','formation_date','rank_position','permaticker','eligible_snapshot_hash',
                       'eligible_universe_size','seed','rng_algorithm','rng_version'],
           'canonical_sort': ['clone_id','formation_date','rank_position'],
           'rows': len(rows), 'clones': N_CLONES, 'formations': len(forms),
           'seed': str(seed), 'rng_algorithm': RNG_ALGO, 'rng_version': RNG_VER,
           'content_hash_sha256': content_hash,
           'parquet_file_sha256': hashlib.sha256(open('results/phaseE/clone_draws.parquet','rb').read()).hexdigest(),
           'order_by_fix': 'F-018: eligible universes are ORDER BY permaticker; without this the seeded sample was nondeterministic.',
           'returns_computed': False}
    Path('results/phaseE/clone_draws_manifest.json').write_text(json.dumps(man, indent=2) + '\n')
    print(f"PASS clone draws: {len(rows)} rows, content_hash {content_hash[:16]}...")
    return 0

if __name__ == '__main__':
    sys.exit(main())
