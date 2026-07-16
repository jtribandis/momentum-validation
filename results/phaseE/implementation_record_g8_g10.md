# Implementation record — G8/G9/G10 (session 2026-07-16)

## G8 — triple reconstruction: COMPLETE, 77/77 x 3
- Python (engine/momentum_engine_py.py), JavaScript/node22 (momentum_engine_js.mjs), and
  DuckDB-SQL (momentum_engine_duckdb.py, ALL arithmetic in SQL) each independently reproduce
  Jason's hand-derived golden truth exactly at the declared precisions. Zero mismatches in any leg.
- One artifact-class fix: JS selection field used unquoted commas inside CSV -> semicolons (spec delimiter).
- Cross-language note: at the declared fixed-dp precisions all three legs agree EXACTLY;
  the FD-04 tolerance allowance was not needed at fixture scale.

## G9 — property tests + provenance: PASS
- qa/test_engine_properties.py (Hypothesis, 90 randomized fixtures): selection cardinality/
  ordering/tie-break, shares identity at emitted precision, NAV(t0)=300000.00 exact,
  permutation invariance of input order, terminal-cash identity when the victim is selected.
- CAUGHT F-013 on first run: hardcoded permaticker 900005 in the engine (invisible to the
  golden gate). Removed; 77/77 re-verified.
- One test-side calibration: shares reconstruction tolerance set to abs 1e-3 to respect the
  6dp emitted precision (FD-04 recorded-precision principle).
- Provenance: manifests/engine_run_manifest_phaseE.json (schema-valid, commit+release-digest pinned).

## G10 — mutation testing: 8/8 KILLED, baseline PASS
Mutants: tie-break inverted; skip-month dropped; entry cost dropped; exit cost sign flipped;
terminal uses last close instead of deal cash; F3 alloc not chained to F1 proceeds; ranking
ascending; NAV drops terminal cash. Every mutant fails the golden gate -> the fixture has teeth
on all economically meaningful failure modes it was designed to cover.
