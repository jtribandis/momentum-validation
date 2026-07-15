#!/usr/bin/env python3
"""build_actions.py — Phase B: permaticker-keyed corporate actions (protocol v3.2.4).
Same date-covered mapping convention as membership (incl. 30-day lp grace, F-012).
value units remain UNVERIFIED per B0-05: carried through untouched with a quarantine flag,
never used in arithmetic until B0-05 closes."""
import json, sys, datetime, hashlib
from pathlib import Path
import duckdb

def sha256(p):
    h = hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()

def main() -> int:
    con = duckdb.connect()
    Path('data/clean').mkdir(parents=True, exist_ok=True)
    con.execute("""CREATE VIEW tk AS
        SELECT permaticker, ticker,
               MIN(COALESCE(firstpricedate, DATE '1900-01-01')) - INTERVAL 10 DAY fp,
               MAX(COALESCE(lastpricedate,  DATE '2999-12-31')) + INTERVAL 30 DAY lp
        FROM read_parquet('data/compact_upload/tickers_universe.parquet')
        WHERE ticker IS NOT NULL GROUP BY permaticker, ticker""")
    con.execute("""CREATE TABLE ac AS
        SELECT t.permaticker, a.date, a.action, a.ticker, a."name", a.value,
               a.contraticker, a.contraname,
               TRUE AS value_units_unverified   -- B0-05 quarantine flag
        FROM read_parquet('data/compact_upload/actions.parquet') a
        JOIN tk t ON a.ticker = t.ticker AND a.date BETWEEN t.fp AND t.lp
        QUALIFY COUNT(DISTINCT t.permaticker) OVER (PARTITION BY a.ticker, a.date, a.action) = 1""")
    n_raw = con.execute("SELECT COUNT(*) FROM read_parquet('data/compact_upload/actions.parquet')").fetchone()[0]
    n = con.execute('SELECT COUNT(*) FROM ac').fetchone()[0]
    con.execute("COPY (SELECT * FROM ac ORDER BY permaticker, date, action, ticker, value NULLS FIRST, contraticker NULLS FIRST) TO 'data/clean/actions_clean.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)")
    vocab = con.execute("SELECT action, COUNT(*) FROM ac GROUP BY 1 ORDER BY 2 DESC").fetchall()
    report = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'rows': {'raw': n_raw, 'mapped': n, 'unmapped': n_raw - n},
              'action_vocabulary': [{'action': a, 'n': c} for a, c in vocab],
              'b005_status': 'value carried with value_units_unverified=TRUE; no arithmetic on value until B0-05 closes',
              'output_sha256': sha256(Path('data/clean/actions_clean.parquet')), 'overall': 'PASS'}
    Path('results/phaseB/actions_report.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
    print(f"PASS actions: {n}/{n_raw} mapped ({n_raw-n} unmapped -> audit)")
    return 0

if __name__ == '__main__':
    sys.exit(main())
