# Implementation record — Phase B verify + membership builder (session 2026-07-14)

## Protocol changes made this session (per Jason's authorization to state-and-change)
1. Makefile phaseB: `fetch_sharadar_raw.py` + `archive_raw.py` replaced by `verify_reduced_upload.py`
   (venue split: raw data + B0-03 hashing live on operator machine via reduce_sharadar_local.py).
   The fetch/archive stubs remain in build/ but are superseded; delete or keep as reference at Jason's option.
2. build/build_sp500_membership.py implemented (Jason's "build_universe.py"): permaticker-keyed
   PIT membership from vendor snapshots + event intervals with cross-validation.
3. manifests/raw_archive_manifest00.json (synthetic leak) deleted. Real vendor semantics report
   still pending Jason re-upload (F-008).

## Verified this session
- All 6 uploaded parquets hash-match reduced_manifest.json (binary-exact).
- raw_archive_manifest.json schema-valid; vintage SHARADAR_20260620; SEP raw = 46,079,831 rows.
- Manifest cross-hash mismatch explained and resolved as CRLF normalization (F-009).

## Bug caught by own QC before commit
First run of the membership builder mapped only 261/59,160 rows: TICKERS carries one row per
(table, permaticker) so the ambiguity check counted duplicate rows as multiple candidates.
Fix: dedupe to distinct (permaticker, ticker) with min/max price-date coverage and count
DISTINCT permatickers. Post-fix: 98.1% mapped, snapshot counts 499-505 = index-consistent.

## Outputs (hashes in results/phaseC/membership_build_report.json)
- data/clean/membership_snapshots.parquet (56,682 rows, 113 quarterly snapshots)
- data/clean/membership_intervals.parquet (868 intervals, 147 event anomalies logged)
