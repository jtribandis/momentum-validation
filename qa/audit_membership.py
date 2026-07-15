#!/usr/bin/env python3
"""audit_membership.py — Phase C membership audit (B0-04 / F-010 worklist).
Classifies every membership row that failed permaticker mapping, splits by evaluated-era
impact, and quantifies per-snapshot-date coverage. Output is the human review worklist:
only evaluated-era items block B0-04."""
import json, sys, datetime
from pathlib import Path
import duckdb

def main() -> int:
    con = duckdb.connect()
    con.execute("""CREATE VIEW tk AS
        SELECT permaticker, ticker,
               MIN(COALESCE(firstpricedate, DATE '1900-01-01')) - INTERVAL 10 DAY fp,
               MAX(COALESCE(lastpricedate,  DATE '2999-12-31')) + INTERVAL 30 DAY lp
        FROM read_parquet('data/compact_upload/tickers_universe.parquet')
        WHERE ticker IS NOT NULL GROUP BY permaticker, ticker""")
    con.execute("""CREATE TABLE un AS
        SELECT s.date, s.action, s.ticker,
               CASE
                 WHEN NOT EXISTS (SELECT 1 FROM tk t WHERE t.ticker = s.ticker)
                   THEN 'TICKER_STRING_ABSENT_FROM_TICKERS'
                 WHEN (SELECT COUNT(DISTINCT t2.permaticker) FROM tk t2
                       WHERE t2.ticker = s.ticker AND s.date BETWEEN t2.fp AND t2.lp) > 1
                   THEN 'AMBIGUOUS_MULTIPLE_PERMATICKERS'
                 ELSE 'DATE_OUTSIDE_PRICE_COVERAGE'
               END AS reason,
               CASE WHEN s.date >= DATE '1997-12-31' THEN 'EVALUATED_ERA' ELSE 'PRE_COVERAGE' END AS era
        FROM read_parquet('data/compact_upload/sp500_membership_raw.parquet') s
        WHERE NOT EXISTS (
          SELECT 1 FROM (SELECT ticker, fp, lp, permaticker FROM tk) t
          WHERE t.ticker = s.ticker AND s.date BETWEEN t.fp AND t.lp
          GROUP BY s.ticker HAVING COUNT(DISTINCT t.permaticker) = 1)""")
    summary = con.execute("SELECT era, reason, action, COUNT(*) FROM un GROUP BY 1,2,3 ORDER BY 1,4 DESC").fetchall()
    # evaluated-era snapshot coverage impact: unmapped snapshot rows per date
    snap_gap = con.execute("""SELECT date, COUNT(*) FROM un
        WHERE era='EVALUATED_ERA' AND action IN ('historical','current') GROUP BY 1 ORDER BY 2 DESC""").fetchall()
    eval_worklist = con.execute("""SELECT date, action, ticker, reason FROM un
        WHERE era='EVALUATED_ERA' ORDER BY action, date""").fetchall()
    # actions-side residuals
    ac_un = con.execute("""SELECT a.action, COUNT(*) FROM read_parquet('data/compact_upload/actions.parquet') a
        WHERE NOT EXISTS (SELECT 1 FROM tk t WHERE t.ticker=a.ticker AND a.date BETWEEN t.fp AND t.lp
                          GROUP BY a.ticker HAVING COUNT(DISTINCT t.permaticker)=1)
        GROUP BY 1 ORDER BY 2 DESC""").fetchall()
    report = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'unmapped_total': con.execute('SELECT COUNT(*) FROM un').fetchone()[0],
        'by_era_reason_action': [{'era': e, 'reason': r, 'action': a, 'n': n} for e, r, a, n in summary],
        'evaluated_era_total': con.execute("SELECT COUNT(*) FROM un WHERE era='EVALUATED_ERA'").fetchone()[0],
        'evaluated_era_snapshot_gaps_by_date': [{'date': str(d), 'missing': n} for d, n in snap_gap],
        'evaluated_era_worklist': [{'date': str(d), 'action': a, 'ticker': t, 'reason': r} for d, a, t, r in eval_worklist],
        'actions_unmapped_by_type': [{'action': a, 'n': n} for a, n in ac_un],
        'b004_ruling_needed': 'Jason classifies each evaluated-era worklist item (or approves bulk classification); PRE_COVERAGE items are recorded as no-impact.',
    }
    Path('results/phaseC/membership_audit.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
    print('PASS audit. evaluated-era unmapped:', report['evaluated_era_total'], '| snapshot-gap dates:', len(snap_gap))
    for row in report['by_era_reason_action'][:10]: print(' ', row)
    return 0

if __name__ == '__main__':
    sys.exit(main())
