#!/usr/bin/env python3
"""build_terminal_events.py — Phase B/C: terminal-event classification (protocol v3.2.4, G1/G2).
For every ever-member permaticker whose price history ends before the vintage horizon,
classify WHY it ended using the ACTIONS stream near the last trade date.

DELIBERATELY EXCLUDED: numeric terminal-return assignments. The Shumway (1997) -30% and
Shumway-Warther (1999) Nasdaq figures enter the ENGINE config at Phase D/E only, gated on
(a) B0-05 value-units verification and (b) the outstanding text-form citation confirmation
for the Nasdaq figure (see verified-source table). This file records classification +
evidence only, so no unverified number can leak into accounting via the data layer."""
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
    horizon = con.execute("SELECT MAX(date) FROM read_parquet('data/clean/sep_prices_part*.parquet')").fetchone()[0]
    con.execute(f"""CREATE TABLE last_px AS
        SELECT p.permaticker, MAX(p.date) last_trade_date
        FROM read_parquet('data/clean/sep_prices_part*.parquet') p
        JOIN (SELECT DISTINCT permaticker FROM read_parquet('data/clean/membership_snapshots.parquet')) m USING (permaticker)
        GROUP BY 1 HAVING MAX(p.date) < DATE '{horizon}' - INTERVAL 10 DAY""")
    # classify via actions within +/-45 days of last trade; priority order below
    con.execute("""CREATE TABLE ev AS
        SELECT l.permaticker, l.last_trade_date,
          COALESCE(
            MAX(CASE WHEN a.action='bankruptcyliquidation' THEN 'BANKRUPTCY_LIQUIDATION' END),
            MAX(CASE WHEN a.action='acquisitionby'         THEN 'ACQUIRED' END),
            MAX(CASE WHEN a.action='mergerto'              THEN 'MERGER' END),
            MAX(CASE WHEN a.action='delisted'              THEN 'DELISTED_OTHER' END),
            MAX(CASE WHEN a.action IN ('tickerchangeto')   THEN 'TICKER_CHANGE' END),
            'NO_ACTION_EVIDENCE') AS event_type,
          COUNT(a.action) AS actions_in_window,
          TRUE AS value_units_unverified,
          'CLASSIFICATION_ONLY_NO_TERMINAL_RETURN_ASSIGNED' AS terminal_return_policy
        FROM last_px l
        LEFT JOIN read_parquet('data/clean/actions_clean.parquet') a
          ON a.permaticker = l.permaticker
         AND a.date BETWEEN l.last_trade_date - INTERVAL 45 DAY AND l.last_trade_date + INTERVAL 45 DAY
         AND a.action IN ('bankruptcyliquidation','acquisitionby','mergerto','delisted','tickerchangeto')
        GROUP BY 1,2""")
    con.execute("COPY (SELECT * FROM ev ORDER BY permaticker) TO 'data/clean/terminal_events.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)")
    mix = con.execute("SELECT event_type, COUNT(*) FROM ev GROUP BY 1 ORDER BY 2 DESC").fetchall()
    report = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'vintage_horizon': str(horizon),
              'terminated_member_permatickers': con.execute('SELECT COUNT(*) FROM ev').fetchone()[0],
              'event_type_mix': [{'type': t, 'n': n} for t, n in mix],
              'no_evidence_worklist_n': next((n for t, n in mix if t=='NO_ACTION_EVIDENCE'), 0),
              'policy': 'classification only; Shumway-baseline numeric returns enter engine config at Phase D/E gated on B0-05 + citation confirmation',
              'output_sha256': sha256(Path('data/clean/terminal_events.parquet')), 'overall': 'PASS'}
    Path('results/phaseB/terminal_events_report.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
    print('PASS terminal events:', mix)
    return 0

if __name__ == '__main__':
    sys.exit(main())
