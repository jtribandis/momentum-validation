#!/usr/bin/env python3
"""build_price_panel.py — Phase B: permaticker-keyed daily price panel (protocol v3.2.4).

Implements the B0-02/R2-validated semantics (see results/phaseB/b002_field_classification_review.md):
  - openadj = open * closeadj / close  (open and close share split/stock-div basis, so the
    ratio layers on exactly the cash-dividend + spinoff factor)
  - closeunadj is the only fully raw field -> basis for split-invariance QC
  - adjustment factor closeadj/closeunadj should change only at corporate-action dates

Outputs:
  data/clean/sep_prices.parquet        (NOT committed: >100MB class; rebuilt deterministically,
                                        SHA-256 recorded in the report — see commit note)
  data/clean/month_end_calendar.parquet (committed; tiny)
  results/phaseB/price_panel_report.json

Also mechanically derives the first computable signal month-end and first computable quarterly
rebalance (resolves the open derivation inside finding F-005).
"""
import json, sys, datetime, hashlib, math
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

    con.execute("""CREATE VIEW raw AS SELECT * FROM read_parquet('data/compact_upload/sep_prices_part*.parquet')""")
    con.execute("""CREATE VIEW tk AS
        SELECT permaticker, ticker,
               MIN(COALESCE(firstpricedate, DATE '1900-01-01')) fp,
               MAX(COALESCE(lastpricedate,  DATE '2999-12-31')) lp
        FROM read_parquet('data/compact_upload/tickers_universe.parquet')
        WHERE ticker IS NOT NULL GROUP BY permaticker, ticker""")

    # date-covered permaticker mapping, unique-candidate rule (same convention as membership builder)
    con.execute("""CREATE TABLE panel AS
        SELECT t.permaticker, r.ticker, r.date, r.open, r.high, r.low, r.close, r.volume,
               r.closeadj, r.closeunadj,
               CASE WHEN r.close > 0 THEN r.open * r.closeadj / r.close ELSE NULL END AS openadj
        FROM raw r JOIN tk t ON r.ticker = t.ticker AND r.date BETWEEN t.fp AND t.lp
        QUALIFY COUNT(DISTINCT t.permaticker) OVER (PARTITION BY r.ticker, r.date) = 1""")

    n_raw = con.execute('SELECT COUNT(*) FROM raw').fetchone()[0]
    n_panel = con.execute('SELECT COUNT(*) FROM panel').fetchone()[0]
    unmapped_tickers = con.execute("""SELECT COUNT(DISTINCT ticker) FROM raw
        WHERE ticker NOT IN (SELECT DISTINCT ticker FROM panel)""").fetchone()[0]
    dups = con.execute("SELECT COUNT(*) FROM (SELECT permaticker, date FROM panel GROUP BY 1,2 HAVING COUNT(*)>1)").fetchone()[0]
    nulls = con.execute("""SELECT
        SUM(CASE WHEN closeadj IS NULL OR closeadj <= 0 THEN 1 ELSE 0 END),
        SUM(CASE WHEN openadj  IS NULL OR openadj  <= 0 THEN 1 ELSE 0 END),
        SUM(CASE WHEN closeunadj IS NULL OR closeunadj <= 0 THEN 1 ELSE 0 END) FROM panel""").fetchone()

    # split-invariance QC on closeunadj: adjustment factor should be piecewise-constant;
    # count factor breaks and check closeadj continuity at unadjusted jumps
    qc = con.execute("""
        WITH f AS (
          SELECT permaticker, date,
                 closeadj / NULLIF(closeunadj,0) AS factor,
                 LAG(closeadj / NULLIF(closeunadj,0)) OVER w AS prev_factor,
                 ABS(LN(closeadj / NULLIF(LAG(closeadj) OVER w, 0))) AS adj_log_move,
                 ABS(LN(closeunadj / NULLIF(LAG(closeunadj) OVER w, 0))) AS unadj_log_move
          FROM panel WINDOW w AS (PARTITION BY permaticker ORDER BY date))
        SELECT
          SUM(CASE WHEN prev_factor IS NOT NULL AND ABS(factor/prev_factor - 1) > 1e-3 THEN 1 ELSE 0 END) AS factor_break_days,
          SUM(CASE WHEN unadj_log_move > LN(1.4) AND adj_log_move <= LN(1.4) THEN 1 ELSE 0 END) AS splits_absorbed,
          SUM(CASE WHEN adj_log_move > LN(1.5) THEN 1 ELSE 0 END) AS extreme_adj_moves
        FROM f""").fetchone()

    con.execute("COPY (SELECT * FROM panel ORDER BY permaticker, date) TO 'data/clean/sep_prices.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)")

    # month-end trading calendar
    con.execute("""CREATE TABLE cal AS
        SELECT DATE_TRUNC('month', date) AS month, MAX(date) AS month_end
        FROM (SELECT DISTINCT date FROM panel) GROUP BY 1 ORDER BY 1""")
    con.execute("COPY (SELECT * FROM cal ORDER BY month) TO 'data/clean/month_end_calendar.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)")

    # first computable signal month-end M: needs month-ends at M-1 and M-7 in calendar
    rows = [r[1] for r in con.execute('SELECT month, month_end FROM cal ORDER BY month').fetchall()]
    first_signal = rows[7] if len(rows) > 7 else None      # index 0 = first month-end; M needs 7 prior
    # first quarterly rebalance: first calendar-quarter-end month-end >= first_signal
    first_reb = None
    for me in rows:
        if first_signal and me >= first_signal and me.month in (3, 6, 9, 12):
            first_reb = me; break

    report = {
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'rows': {'raw': n_raw, 'panel': n_panel, 'dropped': n_raw - n_panel,
                 'unmapped_distinct_tickers': unmapped_tickers,
                 'duplicate_permaticker_dates': dups},
        'null_or_nonpositive': {'closeadj': nulls[0], 'openadj': nulls[1], 'closeunadj': nulls[2]},
        'split_invariance_qc': {'factor_break_days': qc[0], 'splits_absorbed_by_closeadj': qc[1],
                                'extreme_adj_moves_gt_50pct': qc[2],
                                'note': 'factor breaks ~ corporate action days; extreme adj moves feed the tail audit worklist'},
        'openadj_rule': 'open * closeadj / close per R2 ruling (b002 review)',
        'calendar': {'months': len(rows), 'first_month_end': str(rows[0]), 'last_month_end': str(rows[-1])},
        'f005_mechanical_derivation': {
            'first_computable_signal_month_end': str(first_signal),
            'first_computable_quarterly_rebalance': str(first_reb),
            'rule': 'signal at M requires month-ends at M-1 and M-7; rebalance months = {3,6,9,12}',
        },
        'outputs_sha256': {
            'sep_prices.parquet (NOT COMMITTED - deterministic rebuild)': sha256(Path('data/clean/sep_prices.parquet')),
            'month_end_calendar.parquet': sha256(Path('data/clean/month_end_calendar.parquet')),
        },
    }
    ok = (dups == 0 and nulls[0] == 0)
    report['overall'] = 'PASS' if ok else 'FAIL'
    Path('results/phaseB/price_panel_report.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
    print(('PASS' if ok else 'FAIL') + ' price panel')
    print(json.dumps({k: report[k] for k in ['rows','null_or_nonpositive','split_invariance_qc','f005_mechanical_derivation']}, indent=2, default=str))
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
