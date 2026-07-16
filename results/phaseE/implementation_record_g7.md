# Implementation record — golden freeze + Python engine (session 2026-07-16)

## Golden freeze (G6) — COMPLETE
- Jason hand-derived all 77 values in Google Sheets per docs/golden_derivation_google_sheets_guide.md
  and committed fixtures/golden_v2/expected_outputs_SIGNED.csv from his own account
  (commit 98a0542, "Add files via upload") — that commit is the freeze attestation.
- Structural verification: 77/77 rows, 0 blanks, 0 spreadsheet error strings, NAV(2020-03-31)
  = 300000.00 exactly. Selection delimiter ',' accepted alongside spec's ';' (comparator norm).

## Python reference engine (first leg of the G8 triple)
- engine/momentum_engine_py.py: computes all values from fixture inputs ONLY; never reads the
  SIGNED file. qa/golden_compare.py does the diff; golden truth wins by default on mismatch.
- RESULT: 77/77 EXACT MATCH, zero mismatches, on the first comparator run.
- One pre-comparison fix: spec prose said F2 exit 2021-01-04 but opens.csv holds 2021-01-01
  (both are "first weekday" under different holiday assumptions); open VALUE identical by the
  open=prior-close construction, so no numeric impact — engine now reads dates from opens.csv
  as source of truth. Recorded here, not as a finding (zero value impact, label-only).

## Independence note
The hand derivation (Jason, Sheets, from spec) and the engine (session agent, Python, from
the same spec) were produced without either seeing the other's numbers; 77/77 agreement is
therefore meaningful two-sided evidence, not circular confirmation.

## Next gates
G8: JS engine + DuckDB/SQL engine against the same SIGNED file (triple reconstruction).
G9/G10: property-based tests + provenance hashing + mutation testing on the engine.
