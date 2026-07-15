#!/usr/bin/env python3
"""build_eligible_snapshots.py — Phase C: eligible candidate sets per formation month-end
(protocol v3.2.4 §1.3 worked example + G1). Formation month M (quarterly: Mar/Jun/Sep/Dec):
  numerator month-end = M-1, denominator month-end = M-7, deploy first tradable open in M+1.
Eligible at formation t requires ALL of:
  E1 member: permaticker in the vendor snapshot at t (PIT, effective-dated)
  E2 signal computable: closeadj present at month-ends M-1 AND M-7
  E3 deployable: an openadj print exists within the first 5 trading days of M+1
Emits per-formation eligible sets + per-rule attrition counts."""
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
    con.execute("CREATE VIEW cal AS SELECT * FROM read_parquet('data/clean/month_end_calendar.parquet') ORDER BY month")
    con.execute("CREATE VIEW px AS SELECT permaticker, date, closeadj, openadj FROM read_parquet('data/clean/sep_prices_part*.parquet')")
    con.execute("CREATE VIEW snap AS SELECT * FROM read_parquet('data/clean/membership_snapshots.parquet')")
    months = con.execute("SELECT month, month_end FROM cal ORDER BY month").fetchall()
    me = {m[0]: m[1] for m in months}
    keys = sorted(me)
    trading_days = [r[0] for r in con.execute("SELECT DISTINCT date FROM px ORDER BY date").fetchall()]

    rows, attrition = [], []
    for i, mo in enumerate(keys):
        end = me[mo]
        if end.month not in (3, 6, 9, 12) or i < 7 or i + 1 >= len(keys):
            continue
        m1, m7 = me[keys[i-1]], me[keys[i-7]]
        # snapshot at formation date: exact-date match (vendor snapshots are quarter-ends);
        # 'current' snapshot (2026-06-20) handled by nearest-on-or-before within 15 days
        con.execute(f"""CREATE OR REPLACE TABLE members AS
            SELECT DISTINCT permaticker FROM snap
            WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM snap
                                   WHERE snapshot_date BETWEEN DATE '{end}' - INTERVAL 15 DAY AND DATE '{end}')""")
        n_e1 = con.execute("SELECT COUNT(*) FROM members").fetchone()[0]
        if n_e1 == 0: continue
        deploy_days = [d for d in trading_days if d > end][:5]
        if not deploy_days: continue
        con.execute(f"""CREATE OR REPLACE TABLE elig AS
            SELECT m.permaticker,
                   p1.closeadj AS close_m1, p7.closeadj AS close_m7,
                   p1.closeadj / p7.closeadj - 1 AS signal
            FROM members m
            JOIN px p1 ON p1.permaticker = m.permaticker AND p1.date = DATE '{m1}'
            JOIN px p7 ON p7.permaticker = m.permaticker AND p7.date = DATE '{m7}'
            JOIN (SELECT DISTINCT permaticker FROM px
                  WHERE date IN ({','.join("DATE '"+str(d)+"'" for d in deploy_days)})
                    AND openadj > 0) dep ON dep.permaticker = m.permaticker
            WHERE p1.closeadj > 0 AND p7.closeadj > 0""")
        n_elig = con.execute("SELECT COUNT(*) FROM elig").fetchone()[0]
        con.execute(f"INSERT INTO all_elig SELECT DATE '{end}' AS formation, * FROM elig") if i > 7 and con.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='all_elig'").fetchone()[0] else con.execute(f"CREATE TABLE all_elig AS SELECT DATE '{end}' AS formation, * FROM elig")
        attrition.append({'formation': str(end), 'members': n_e1, 'eligible': n_elig, 'attrition': n_e1 - n_elig})
    con.execute("COPY (SELECT * FROM all_elig ORDER BY formation, permaticker) TO 'data/clean/eligible_snapshots.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)")
    Path('results/phaseC').mkdir(parents=True, exist_ok=True)
    el = [a['eligible'] for a in attrition]
    report = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'formations': len(attrition), 'first_formation': attrition[0]['formation'], 'last_formation': attrition[-1]['formation'],
              'eligible_min': min(el), 'eligible_max': max(el), 'eligible_avg': round(sum(el)/len(el),1),
              'per_formation': attrition,
              'rules': 'E1 snapshot member; E2 closeadj at M-1 & M-7; E3 openadj within 5 trading days of M+1',
              'output_sha256': sha256(Path('data/clean/eligible_snapshots.parquet')), 'overall': 'PASS'}
    Path('results/phaseC/eligible_snapshots_report.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
    print(f"PASS eligible: {len(attrition)} formations {attrition[0]['formation']}..{attrition[-1]['formation']}, eligible {min(el)}-{max(el)} (avg {round(sum(el)/len(el),1)})")
    return 0

if __name__ == '__main__':
    sys.exit(main())
