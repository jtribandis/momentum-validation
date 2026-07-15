#!/usr/bin/env python3
"""
build_sp500_membership.py — Phase C: point-in-time S&P 500 membership (protocol v3.2.4)

Inputs (reduced upload, vintage-pinned):
  data/compact_upload/sp500_membership_raw.parquet   (date, action, ticker, ...)
  data/compact_upload/tickers_universe.parquet       (permaticker, ticker, firstpricedate, lastpricedate, ...)

Outputs:
  data/clean/membership_snapshots.parquet   (snapshot_date, ticker, permaticker)  -- from 'historical'+'current' rows
  data/clean/membership_intervals.parquet   (ticker, permaticker, start_date, end_date) -- from added/removed events
  results/phaseC/membership_build_report.json  -- QC, unmapped identities, snapshot-vs-interval cross-validation

Identity rule (data fidelity contract): all joins keyed by permaticker. Ticker strings are
mapped to permaticker via TICKERS rows; when one ticker string maps to multiple permatickers
(Sharadar reuses ticker strings), the permaticker whose [firstpricedate, lastpricedate] covers
the membership date wins. Rows with zero or ambiguous coverage are NOT guessed: they are
emitted to the unmapped list for the Phase C membership audit (B0-04).

Interval semantics: 'added' opens membership ON the event date (inclusive); 'removed' closes
it the day BEFORE the event date. An 'added' with no subsequent 'removed' stays open through
the data vintage horizon. Convention recorded here; if the Phase C audit contradicts it
against snapshots, the audit wins and this file gets amended with a finding ID.
"""
import json, sys, datetime, hashlib
from pathlib import Path
import duckdb

SEP_COVERAGE_FLOOR = '1997-12-31'   # F-005: earliest SEP row in vintage SHARADAR_20260620

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()

def main() -> int:
    con = duckdb.connect()
    Path('data/clean').mkdir(parents=True, exist_ok=True)
    Path('results/phaseC').mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    con.execute("CREATE VIEW sp AS SELECT * FROM read_parquet('data/compact_upload/sp500_membership_raw.parquet')")
    con.execute("""CREATE VIEW tk AS
        SELECT permaticker, ticker,
               MIN(COALESCE(firstpricedate, DATE '1900-01-01')) fp,
               MAX(COALESCE(lastpricedate,  DATE '2999-12-31')) + INTERVAL 30 DAY lp
        FROM read_parquet('data/compact_upload/tickers_universe.parquet')
        WHERE ticker IS NOT NULL
        GROUP BY permaticker, ticker
        -- lp grace: +30 days. Membership/corporate events (removals, delistings, 'current'
        -- snapshot stamps) postdate the final trade by days-to-weeks; without grace the
        -- 2026-06-20 'current' snapshot and ~200 evaluated-era removals fail mapping (F-012).""")

    con.execute("""CREATE TABLE mapped AS
        SELECT s.date, s.action, s.ticker, t.permaticker,
               COUNT(DISTINCT t.permaticker) OVER (PARTITION BY s.date, s.action, s.ticker) AS n_candidates
        FROM sp s LEFT JOIN tk t
          ON s.ticker = t.ticker AND s.date BETWEEN t.fp AND t.lp""")
    con.execute("""CREATE TABLE unmapped AS
        SELECT DISTINCT date, action, ticker,
               CASE WHEN n_candidates = 0 OR permaticker IS NULL THEN 'NO_COVERING_PERMATICKER'
                    ELSE 'AMBIGUOUS_MULTIPLE_PERMATICKERS' END AS reason
        FROM mapped WHERE permaticker IS NULL OR n_candidates > 1""")
    con.execute("""CREATE TABLE ok AS
        SELECT date, action, ticker, permaticker FROM mapped
        WHERE permaticker IS NOT NULL AND n_candidates = 1""")

    con.execute("""CREATE TABLE snaps AS
        SELECT DISTINCT date AS snapshot_date, ticker, permaticker
        FROM ok WHERE action IN ('historical','current')""")
    con.execute("COPY (SELECT * FROM snaps ORDER BY snapshot_date, permaticker) TO 'data/clean/membership_snapshots.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)")

    rows = con.execute("""SELECT permaticker, ticker, date, action FROM ok
        WHERE action IN ('added','removed')
        ORDER BY permaticker, date, CASE action WHEN 'removed' THEN 0 ELSE 1 END""").fetchall()
    intervals, anomalies = [], []
    open_by_pt = {}
    for pt, tic, d, act in rows:
        if act == 'added':
            if pt in open_by_pt:
                anomalies.append({'permaticker': pt, 'ticker': tic, 'date': str(d), 'issue': 'ADDED_WHILE_OPEN'})
                continue
            open_by_pt[pt] = (tic, d)
        else:
            if pt not in open_by_pt:
                anomalies.append({'permaticker': pt, 'ticker': tic, 'date': str(d), 'issue': 'REMOVED_WITHOUT_OPEN'})
                continue
            tic0, d0 = open_by_pt.pop(pt)
            intervals.append((tic0, pt, d0, d - datetime.timedelta(days=1)))
    horizon = con.execute("SELECT MAX(date) FROM sp").fetchone()[0]
    for pt, (tic0, d0) in open_by_pt.items():
        intervals.append((tic0, pt, d0, horizon))

    con.execute("CREATE TABLE iv (ticker VARCHAR, permaticker BIGINT, start_date DATE, end_date DATE)")
    con.executemany("INSERT INTO iv VALUES (?,?,?,?)", intervals)
    con.execute("COPY (SELECT * FROM iv ORDER BY permaticker, start_date) TO 'data/clean/membership_intervals.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)")

    xv = con.execute(f"""
        WITH snap_dates AS (SELECT DISTINCT snapshot_date FROM snaps WHERE snapshot_date >= DATE '{SEP_COVERAGE_FLOOR}'),
        snap_sets AS (SELECT snapshot_date, permaticker FROM snaps WHERE snapshot_date >= DATE '{SEP_COVERAGE_FLOOR}'),
        iv_sets AS (
            SELECT d.snapshot_date, i.permaticker
            FROM snap_dates d JOIN iv i
              ON d.snapshot_date BETWEEN i.start_date AND i.end_date)
        SELECT
          (SELECT COUNT(*) FROM snap_dates),
          (SELECT COUNT(*) FROM (SELECT * FROM snap_sets EXCEPT SELECT * FROM iv_sets)),
          (SELECT COUNT(*) FROM (SELECT * FROM iv_sets EXCEPT SELECT * FROM snap_sets)),
          (SELECT COUNT(*) FROM (SELECT * FROM snap_sets INTERSECT SELECT * FROM iv_sets))
    """).fetchone()

    counts = con.execute("""SELECT MIN(c), MAX(c), AVG(c) FROM
        (SELECT snapshot_date, COUNT(*) c FROM snaps GROUP BY snapshot_date)""").fetchone()

    unmapped_rows = con.execute("SELECT date, action, ticker, reason FROM unmapped ORDER BY date").fetchall()
    report = {
        'created_utc': ts,
        'inputs_sha256': {
            'sp500_membership_raw.parquet': sha256(Path('data/compact_upload/sp500_membership_raw.parquet')),
            'tickers_universe.parquet': sha256(Path('data/compact_upload/tickers_universe.parquet')),
        },
        'row_counts': {
            'membership_rows_total': con.execute('SELECT COUNT(*) FROM sp').fetchone()[0],
            'mapped_unique': con.execute('SELECT COUNT(*) FROM ok').fetchone()[0],
            'snapshots_rows': con.execute('SELECT COUNT(*) FROM snaps').fetchone()[0],
            'intervals': len(intervals),
            'event_anomalies': len(anomalies),
            'unmapped_membership_rows': len(unmapped_rows),
            'unmapped_distinct_tickers': con.execute('SELECT COUNT(DISTINCT ticker) FROM unmapped').fetchone()[0],
        },
        'snapshot_member_counts': {'min': counts[0], 'max': counts[1], 'avg': round(counts[2], 1)},
        'cross_validation_snapshot_vs_intervals': {
            'snapshot_dates_checked': xv[0], 'agree_pairs': xv[3],
            'in_snapshot_not_intervals': xv[1], 'in_intervals_not_snapshot': xv[2],
            'note': 'Disagreements EXPECTED nonzero (event reconstruction vs vendor snapshots); Phase C audit classifies them. Snapshots are the PIT source of truth for the rebalance gate; intervals are the consistency check.',
        },
        'interval_convention': 'added inclusive on event date; removed effective day-before event date; open intervals closed at vendor horizon',
        'sep_coverage_floor_applied_to_xval': SEP_COVERAGE_FLOOR,
        'event_anomalies': anomalies[:50],
        'unmapped': [{'date': str(r[0]), 'action': r[1], 'ticker': r[2], 'reason': r[3]} for r in unmapped_rows[:200]],
        'outputs_sha256': {
            'membership_snapshots.parquet': sha256(Path('data/clean/membership_snapshots.parquet')),
            'membership_intervals.parquet': sha256(Path('data/clean/membership_intervals.parquet')),
        },
        'b004_status': 'AUDIT_INPUT_READY - unmapped + anomalies + xval disagreements are the Phase C audit worklist; B0-04 remains OPEN until each evaluated-timeline identity is classified.',
    }
    Path('results/phaseC/membership_build_report.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
    print('PASS build_sp500_membership; report at results/phaseC/membership_build_report.json')
    print(json.dumps({k: report[k] for k in ['row_counts','snapshot_member_counts','cross_validation_snapshot_vs_intervals']}, indent=2, default=str))
    return 0

if __name__ == '__main__':
    sys.exit(main())
