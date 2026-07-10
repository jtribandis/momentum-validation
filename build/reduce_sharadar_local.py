#!/usr/bin/env python3
"""
reduce_sharadar_local.py — Phase B local reducer (v1.0, protocol v3.2.4)

Runs on the OPERATOR machine where the raw Sharadar CSVs live. One pass produces:

  1. manifests/raw_archive_manifest.json     (B0-03: SHA-256, row count, schema hash, vintage ID)
  2. results/phaseB/vendor_semantics_report.json  (B0-02 DRAFT: live headers + field classification;
                                                   final classification sign-off remains a manual step)
  3. data/compact_upload/*.parquet           chunked, zstd-compressed, each part kept under
                                             --max-part-mb (default 85 MB, safe for GitHub's 100 MB limit)
  4. data/compact_upload/reduced_manifest.json    (SHA-256 of every emitted parquet + QC counts)

Reduction rules (recorded in reduced_manifest.json; protocol-relevant, review before running):
  - SP500 table: kept in full (it is small and is the PIT membership source).
  - TICKERS table: kept in full (identity resolution must not be pre-filtered).
  - SEP: rows for tickers that EVER appear in the SP500 table, date >= --date-floor
         (default 1997-01-01, giving >= 7 months of signal warm-up before the 1998 start).
         Columns kept: ticker,date,open,high,low,close,volume,closeadj,closeunadj,lastupdated.
         NOTE: Sharadar SEP has no openadj column; openadj is DERIVED downstream as
         open * closeadj / close. The derivation rule is recorded in the manifest, not applied here,
         so the uploaded data stays raw-faithful.
  - ACTIONS: rows for ever-member tickers, all dates (delisting/M&A terminal events).
  - SF1: SKIPPED by default (M3 disabled until module inventory). Enable with --include-sf1.

Membership join caveat (OV-01/B0-04): the SP500 table is keyed by ticker, not permaticker.
This script detects the actual columns at runtime, reports them in the vendor semantics draft,
and joins SEP on whichever key both tables share. Unmapped identities are the Phase C audit's job.

Usage (edit RAW_PATHS or pass --raw-dir):
  python build/reduce_sharadar_local.py --raw-dir /path/to/sharadar_csvs --vintage-id SHARADAR_20260709
  python build/reduce_sharadar_local.py --raw-dir ... --vintage-id ... --include-sf1

Dependencies: pip install duckdb   (tested on duckdb 1.5.4; no pandas required)
"""
import argparse, hashlib, json, os, sys, datetime, glob
from pathlib import Path

import duckdb

# Default raw filename patterns; the script globs these under --raw-dir.
RAW_PATTERNS = {
    'SEP':     ['SHARADAR_SEP*.csv', 'SEP*.csv', 'sep*.csv'],
    'TICKERS': ['SHARADAR_TICKERS*.csv', 'TICKERS*.csv', 'tickers*.csv'],
    'SP500':   ['SHARADAR_SP500*.csv', 'SP500*.csv', 'sp500*.csv'],
    'ACTIONS': ['SHARADAR_ACTIONS*.csv', 'ACTIONS*.csv', 'actions*.csv'],
    'SF1':     ['SHARADAR_SF1*.csv', 'SF1*.csv', 'sf1*.csv'],
}

SEP_KEEP_COLS = ['ticker','date','open','high','low','close','volume','closeadj','closeunadj','lastupdated']

# Fields we expect per table (for the B0-02 draft classification). Anything not listed
# is reported as UNKNOWN_REVIEW_REQUIRED, never silently used.
EXPECTED_FIELDS = {
    'SEP':     set(SEP_KEEP_COLS),
    'SP500':   {'date','action','ticker','name','contraticker','contraname','note'},
    'ACTIONS': {'date','action','ticker','name','value','contraticker','contraname'},
    'TICKERS': {'table','permaticker','ticker','name','exchange','isdelisted','category','cusips',
                'siccode','sicsector','sicindustry','famasector','famaindustry','sector','industry',
                'scalemarketcap','scalerevenue','relatedtickers','currency','location',
                'lastupdated','firstadded','firstpricedate','lastpricedate','firstquarter',
                'lastquarter','secfilings','companysite'},
    'SF1':     set(),  # classified in full only if included
}

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def find_raw(raw_dir: Path):
    found = {}
    for table, pats in RAW_PATTERNS.items():
        for pat in pats:
            hits = sorted(raw_dir.glob(pat))
            if hits:
                found[table] = hits[0]
                if len(hits) > 1:
                    print(f'WARN: multiple files match {table} pattern; using {hits[0].name}, ignoring {[h.name for h in hits[1:]]}')
                break
    return found

def csv_header(con, path: Path):
    rows = con.execute(
        "SELECT column_name, column_type FROM (DESCRIBE SELECT * FROM read_csv_auto(?, sample_size=100000))",
        [str(path)]).fetchall()
    return [(r[0], r[1]) for r in rows]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw-dir', required=True)
    ap.add_argument('--vintage-id', required=True, help='e.g. SHARADAR_YYYYMMDD (date the CSVs were exported/downloaded)')
    ap.add_argument('--date-floor', default='1997-01-01')
    ap.add_argument('--max-part-mb', type=float, default=85.0)
    ap.add_argument('--include-sf1', action='store_true')
    ap.add_argument('--out-dir', default='data/compact_upload')
    args = ap.parse_args()

    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    Path('manifests').mkdir(exist_ok=True)
    Path('results/phaseB').mkdir(parents=True, exist_ok=True)

    found = find_raw(raw_dir)
    required = ['SEP','TICKERS','SP500','ACTIONS'] + (['SF1'] if args.include_sf1 else [])
    missing = [t for t in required if t not in found]
    if missing:
        print(f'FAIL: raw files not found for {missing} under {raw_dir}. Adjust RAW_PATTERNS or --raw-dir.')
        return 1

    con = duckdb.connect()
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # ---------- 1. Raw archive manifest (B0-03) ----------
    print('== B0-03: hashing raw files (streamed; large files take a while) ==')
    tables = []
    headers = {}
    for t in required:
        p = found[t]
        print(f'  {t}: {p.name} ({p.stat().st_size/1e6:.1f} MB) ...', flush=True)
        hdr = csv_header(con, p)
        headers[t] = hdr
        schema_hash = hashlib.sha256(json.dumps(hdr).encode()).hexdigest()
        row_count = con.execute("SELECT COUNT(*) FROM read_csv_auto(?, sample_size=100000)", [str(p)]).fetchone()[0]
        tables.append({'table': t, 'path': str(p), 'row_count': int(row_count),
                       'byte_hash': sha256_file(p), 'schema_hash': schema_hash})
    manifest = {'data_vintage_id': args.vintage_id, 'retrieval_timestamp_utc': ts, 'tables': tables}
    Path('manifests/raw_archive_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('  wrote manifests/raw_archive_manifest.json')

    # ---------- 2. Vendor semantics draft (B0-02) ----------
    semantics = {'created_utc': ts, 'data_vintage_id': args.vintage_id, 'status': 'DRAFT_MANUAL_REVIEW_REQUIRED', 'tables': {}}
    for t in required:
        expected = EXPECTED_FIELDS.get(t, set())
        cols = [c for c, _ in headers[t]]
        semantics['tables'][t] = {
            'live_header': headers[t],
            'expected_present': sorted(set(cols) & expected),
            'expected_missing': sorted(expected - set(cols)),
            'unknown_review_required': sorted(set(cols) - expected) if expected else ['ALL_FIELDS_REVIEW_REQUIRED'],
        }
    semantics['notes'] = [
        'openadj is not a Sharadar SEP column; downstream derivation rule: openadj = open * closeadj / close.',
        'closeadj dividend/split basis must be manually confirmed against Sharadar docs before Phase B sign-off (OV-01).',
        'SP500 table membership key and action vocabulary must be manually confirmed (feeds B0-04).',
    ]
    Path('results/phaseB/vendor_semantics_report.json').write_text(json.dumps(semantics, indent=2) + '\n')
    print('  wrote results/phaseB/vendor_semantics_report.json (DRAFT - manual classification still required)')

    # ---------- 3. Reduction ----------
    print('== reducing ==')
    sp500_cols = [c for c, _ in headers['SP500']]
    join_key = 'ticker' if 'ticker' in sp500_cols else ('permaticker' if 'permaticker' in sp500_cols else None)
    if join_key is None:
        print(f'FAIL: SP500 table has neither ticker nor permaticker column; live header: {sp500_cols}')
        return 1
    print(f'  SP500 membership key detected: {join_key}')

    con.execute(f"CREATE VIEW sp500_raw AS SELECT * FROM read_csv_auto('{found['SP500']}', sample_size=100000)")
    con.execute(f"CREATE VIEW tickers_raw AS SELECT * FROM read_csv_auto('{found['TICKERS']}', sample_size=100000)")
    con.execute(f"CREATE TABLE ever_members AS SELECT DISTINCT {join_key} AS mkey FROM sp500_raw WHERE {join_key} IS NOT NULL")
    n_members = con.execute('SELECT COUNT(*) FROM ever_members').fetchone()[0]
    print(f'  distinct ever-member keys: {n_members}')

    emitted = []

    def emit(table_name, query, base):
        con.execute(f"CREATE OR REPLACE TABLE _out AS {query}")
        n = con.execute('SELECT COUNT(*) FROM _out').fetchone()[0]
        tmp = out_dir / f'{base}.parquet'
        con.execute(f"COPY _out TO '{tmp}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        size_mb = tmp.stat().st_size / 1e6
        parts = [tmp]
        if size_mb > args.max_part_mb:
            # re-emit chunked by row ranges
            tmp.unlink()
            import math
            k = max(2, math.ceil(size_mb / max(args.max_part_mb, 0.001)))
            per = n // k + 1
            parts = []
            for i in range(k):
                pp = out_dir / f'{base}_part{i+1:02d}.parquet'
                con.execute(f"COPY (SELECT * FROM (SELECT *, row_number() OVER () rn FROM _out) WHERE rn > {i*per} AND rn <= {(i+1)*per}) TO '{pp}' (FORMAT PARQUET, COMPRESSION ZSTD)")
                parts.append(pp)
        for pp in parts:
            emitted.append({'table': table_name, 'file': pp.name, 'bytes': pp.stat().st_size,
                            'sha256': sha256_file(pp)})
        print(f'  {table_name}: {n} rows -> {len(parts)} file(s), {sum(p.stat().st_size for p in parts)/1e6:.1f} MB total')
        return n

    sep_cols_live = [c for c, _ in headers['SEP']]
    keep = [c for c in SEP_KEEP_COLS if c in sep_cols_live]
    dropped = [c for c in SEP_KEEP_COLS if c not in sep_cols_live]
    if dropped:
        print(f'  WARN: SEP is missing expected columns {dropped}; recorded in vendor semantics report')
    qc = {}
    qc['sep_rows'] = emit('sep_prices',
        f"SELECT {', '.join('s.'+c for c in keep)} FROM read_csv_auto('{found['SEP']}', sample_size=100000) s "
        f"JOIN ever_members m ON s.ticker = m.mkey WHERE s.date >= DATE '{args.date_floor}'",
        'sep_prices')
    qc['tickers_rows'] = emit('tickers_universe', "SELECT * FROM tickers_raw", 'tickers_universe')
    qc['sp500_rows'] = emit('sp500_membership_raw', "SELECT * FROM sp500_raw", 'sp500_membership_raw')
    qc['actions_rows'] = emit('actions_clean_raw',
        f"SELECT a.* FROM read_csv_auto('{found['ACTIONS']}', sample_size=100000) a JOIN ever_members m ON a.ticker = m.mkey",
        'actions')
    if args.include_sf1:
        qc['sf1_rows'] = emit('sf1_asreported_raw',
            f"SELECT f.* FROM read_csv_auto('{found['SF1']}', sample_size=100000) f JOIN ever_members m ON f.ticker = m.mkey "
            f"WHERE f.dimension IN ('ARQ','ART')", 'sf1_asreported')

    # QC extremes on the reduced SEP
    qs = con.execute(
        f"SELECT MIN(date), MAX(date), COUNT(DISTINCT ticker), "
        f"SUM(CASE WHEN closeadj IS NULL THEN 1 ELSE 0 END), "
        f"SUM(CASE WHEN open IS NULL OR open <= 0 THEN 1 ELSE 0 END) "
        f"FROM read_parquet('{out_dir}/sep_prices*.parquet')").fetchone()
    qc['sep_date_min'], qc['sep_date_max'] = str(qs[0]), str(qs[1])
    qc['sep_distinct_tickers'] = int(qs[2]); qc['sep_null_closeadj'] = int(qs[3]); qc['sep_bad_open'] = int(qs[4])

    reduced = {
        'data_vintage_id': args.vintage_id, 'created_utc': ts,
        'reduction_rules': {
            'sep_filter': f'ticker IN SP500-ever-members AND date >= {args.date_floor}',
            'sep_columns': keep, 'sep_columns_missing_at_source': dropped,
            'openadj_derivation_rule': 'openadj = open * closeadj / close (applied downstream, not here)',
            'sp500_join_key': join_key,
            'sf1_included': bool(args.include_sf1),
            'tables_kept_in_full': ['TICKERS', 'SP500'],
        },
        'qc': qc, 'files': emitted,
        'raw_archive_manifest_sha256': sha256_file(Path('manifests/raw_archive_manifest.json')),
    }
    Path(out_dir / 'reduced_manifest.json').write_text(json.dumps(reduced, indent=2) + '\n')
    print(f'== DONE. Upload the contents of {out_dir}/ plus manifests/raw_archive_manifest.json '
          f'and results/phaseB/vendor_semantics_report.json ==')
    print(json.dumps(qc, indent=2))
    return 0

if __name__ == '__main__':
    sys.exit(main())
