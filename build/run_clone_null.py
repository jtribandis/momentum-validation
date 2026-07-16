#!/usr/bin/env python3
"""run_clone_null.py — Stage 5 primary gate: full-mechanical exchangeable clone null (v3.2.4).
For each formation, the CORE picks top-3 by signal from the eligible set. A clone draws 3 names
UNIFORMLY AT RANDOM from the SAME eligible set at that formation, runs the identical lot
mechanics, and compounds a quarterly series. 10,000 clones build the null distribution of CAGR.
Gate (FD-01, frozen): CORE must exceed the 99th percentile of the clone CAGR distribution AND
clear the 3.00% annualized net-excess floor vs the clone median.
Deterministic seed = sha256(blotter)||'clone-null' so the draw is reproducible."""
import csv, json, sys, hashlib, random, datetime
from collections import defaultdict
from pathlib import Path
import duckdb

def main() -> int:
    con = duckdb.connect()
    con.execute("CREATE VIEW elig AS SELECT * FROM read_parquet('data/clean/eligible_snapshots.parquet')")
    con.execute("CREATE VIEW px AS SELECT permaticker p, date d, closeadj c, openadj o FROM read_parquet('data/clean/sep_prices_part*.parquet')")
    con.execute("CREATE VIEW term AS SELECT permaticker p, last_trade_date FROM read_parquet('data/clean/terminal_events.parquet')")
    summary = json.load(open('results/phaseE/core_summary.json'))
    core_cagr = summary['core_cagr']
    forms = sorted(summary['quarterly_returns'])
    trading = [r[0] for r in con.execute("SELECT DISTINCT d FROM px ORDER BY d").fetchall()]
    me = [r[0] for r in con.execute("SELECT month_end FROM read_parquet('data/clean/month_end_calendar.parquet') ORDER BY month").fetchall()]
    def first_open_after(d):
        for t in trading:
            if str(t) > d: return t
        return None
    def me_plus6(d):
        for i, m in enumerate(me):
            if str(m) == d: return me[i+6] if i+6 < len(me) else None
        return None
    COST = 0.001

    # precompute per-formation eligible universe + entry/exit prices for ALL eligible names
    universe = {}
    for f in forms:
        rows = con.execute(f"SELECT permaticker FROM elig WHERE formation = DATE '{f}'").fetchall()
        perms = [r[0] for r in rows]
        deploy = first_open_after(f); ex_me = me_plus6(f); exit_day = first_open_after(str(ex_me)) if ex_me else None
        pr = {}
        for p in perms:
            eo = con.execute(f"SELECT o FROM px WHERE p={p} AND d=DATE '{deploy}'").fetchone()
            if not eo or not eo[0] or eo[0] <= 0: continue
            tt = con.execute(f"SELECT last_trade_date FROM term WHERE p={p} AND last_trade_date BETWEEN DATE '{deploy}' AND DATE '{exit_day}'").fetchone()
            if tt:
                xp = con.execute(f"SELECT c FROM px WHERE p={p} AND d <= DATE '{tt[0]}' ORDER BY d DESC LIMIT 1").fetchone()
                ret = xp[0] / (eo[0]*(1+COST)) - 1
            else:
                xo = con.execute(f"SELECT o FROM px WHERE p={p} AND d=DATE '{exit_day}'").fetchone()
                xpx = xo[0] if xo and xo[0] else eo[0]
                ret = (xpx*(1-COST)) / (eo[0]*(1+COST)) - 1
            pr[p] = ret
        universe[f] = pr

    seed = int(hashlib.sha256((summary['blotter_sha256'] + 'clone-null').encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    N = 10000
    clone_cagrs = []
    yrs = len(forms)/4.0
    for _ in range(N):
        cum = 1.0
        for f in forms:
            pr = universe[f]
            picks = rng.sample(list(pr), min(3, len(pr)))
            cum *= (1 + sum(pr[p] for p in picks)/len(picks))
        clone_cagrs.append(cum ** (1/yrs) - 1)
    clone_cagrs.sort()
    import statistics
    p99 = clone_cagrs[int(0.99*N)-1]
    med = statistics.median(clone_cagrs)
    pct = sum(1 for c in clone_cagrs if c < core_cagr) / N
    net_excess = core_cagr - med
    passes_pct = core_cagr > p99
    passes_floor = net_excess >= 0.03
    rep = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'seed': seed, 'clones': N, 'window': summary['window'],
           'core_cagr': round(core_cagr,6), 'clone_median_cagr': round(med,6),
           'clone_p99_cagr': round(p99,6), 'core_percentile_in_clone_dist': round(pct,4),
           'net_excess_vs_median': round(net_excess,6),
           'gate_fd01': {'threshold': '99th pct AND 3% floor',
                         'passes_percentile': passes_pct, 'passes_floor': passes_floor,
                         'PRIMARY_GATE': 'PASS' if (passes_pct and passes_floor) else 'FAIL'}}
    Path('results/phaseE/clone_null.json').write_text(json.dumps(rep, indent=2) + '\n')
    print(json.dumps(rep['gate_fd01'], indent=2))
    print(f"CORE {rep['core_cagr']} vs clone median {rep['clone_median_cagr']} / p99 {rep['clone_p99_cagr']}; CORE at {rep['core_percentile_in_clone_dist']*100:.1f}th pct")
    return 0

if __name__ == '__main__':
    sys.exit(main())
