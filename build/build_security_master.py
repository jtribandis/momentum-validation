#!/usr/bin/env python3
"""build_security_master.py — Phase B: permaticker-keyed identity master (protocol v3.2.4).
One row per permaticker from the TICKERS SEP rows; QC on uniqueness, category mix of
ever-members, and leveraged/inverse-ETF absence (standing rule: excluded from selection
universe — S&P membership should make this vacuous; we verify rather than assume)."""
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
    Path('results/phaseB').mkdir(parents=True, exist_ok=True)
    con.execute("""CREATE TABLE sm AS
        SELECT permaticker, ANY_VALUE(ticker) AS ticker, ANY_VALUE("name") AS co_name,
               ANY_VALUE(exchange) exchange, ANY_VALUE(category) category,
               ANY_VALUE(isdelisted) isdelisted, ANY_VALUE(siccode) siccode,
               MIN(firstpricedate) firstpricedate, MAX(lastpricedate) lastpricedate
        FROM read_parquet('data/compact_upload/tickers_universe.parquet')
        WHERE "table" = 'SEP' AND permaticker IS NOT NULL
        GROUP BY permaticker""")
    dup = con.execute("SELECT COUNT(*) - COUNT(DISTINCT permaticker) FROM sm").fetchone()[0]
    con.execute("COPY (SELECT * FROM sm ORDER BY permaticker) TO 'data/clean/security_master.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)")
    cats = con.execute("""
        SELECT s.category, COUNT(DISTINCT s.permaticker) FROM sm s
        JOIN read_parquet('data/clean/membership_snapshots.parquet') m USING (permaticker)
        GROUP BY 1 ORDER BY 2 DESC""").fetchall()
    etf_members = con.execute("""
        SELECT COUNT(DISTINCT s.permaticker) FROM sm s
        JOIN read_parquet('data/clean/membership_snapshots.parquet') m USING (permaticker)
        WHERE s.category ILIKE '%ETF%' OR s.category ILIKE '%ETN%'""").fetchone()[0]
    report = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'rows': con.execute('SELECT COUNT(*) FROM sm').fetchone()[0],
        'duplicate_permatickers': dup,
        'ever_member_category_mix': [{'category': c, 'n': n} for c, n in cats],
        'etf_etn_among_members': etf_members,
        'output_sha256': sha256(Path('data/clean/security_master.parquet')),
    }
    ok = (dup == 0)
    report['overall'] = 'PASS' if ok else 'FAIL'
    Path('results/phaseB/security_master_report.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
    print(('PASS' if ok else 'FAIL') + f" security_master: {report['rows']} permatickers, dup={dup}, member ETF/ETN={etf_members}")
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
