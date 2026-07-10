# Implementation record — Phase A (executed 2026-07-09, sandbox session)

## What was executed
`make scaffold-check` PASS · `make status` PASS (tier T0_EXECUTABLE_SCAFFOLD) · `make blocker-check` FAIL-by-design (11 OPEN) · `make gate-test` 3 FAIL-by-design · `make phaseA` PASS after fix below.

## Scripts implemented (were NOT-IMPLEMENTED stubs)
- tools/create_protocol_release.py — SHA-256 per frozen artifact (18 files: design contract, 4 protocol contracts, 4 configs, 9 schemas) + run-level digest; writes protocol_release.json. Final digest: e81980c3be10398c... (full value in file).
- tools/validate_config.py — jsonschema validation of core_frozen.yaml + parse checks on modules/tolerance/risk configs + frozen-value invariant checks (signal, top-3, 6m hold, quarterly, 10bps, 10,000 clones, 3% floor). Emits config_validation.json.
- tools/validate_ledgers.py — header + status-vocabulary + required-holdout-row checks on blocker_ledger, period_provenance, research_decisions, open_tasks. Emits ledger_validation.json.
- tools/holdout_guard.py — attestation-gated period access; self-test covers 6 cases (empty/missing/complete/spent/partial/non-governed) all PASS; live ledger correctly BLOCKS all three governed periods.

## Defect found and fixed (needs Jason sign-off)
- **DEFECT-A1**: schemas/config.schema.json (additionalProperties:false) rejected two fields present in config/core_frozen.yaml: primary_effect_floor_annualized_excess, aggregate_performance_allowed_before_phaseF. Fix applied: added both to schema as `const` (0.03 / false) and to `required`. Rationale: both are frozen protocol values (§ primary gate floor is immutable pre-holdout), so pinning as const is the conservative fix. Schema edit is explicitly permitted by Phase A fix rules ("edit only config, schemas, ledgers, or guard code").

## Open decisions for Jason (NOT resolved unilaterally)
1. **protocol_version drift**: core_frozen.yaml says "3.2.3"; package is v3.2.4. Left unchanged; validate_config emits a WARN. Decide: bump to 3.2.4 (and note in changelog) or keep.
2. **B0-01 status**: evidence file results/phaseA/config_validation.json now exists and PASSes. Marking B0-01 RESOLVED in blocker_ledger.csv is a human sign-off step — left OPEN pending your review of the schema fix above.
3. protocol_release.json regenerated AFTER the schema fix (Makefile ordering handles this automatically on rerun) — confirm digest e81980c3... is the one you freeze.

## Environment preconditions discovered
- pytest and jsonschema are not vendored; `pip install -r requirements-dev.txt` (or pytest+jsonschema+pyyaml) required before make targets run. PyYAML was already present in this environment.
- Note: __pycache__/.pytest_cache dirs shipped inside the ZIP; harmless, but `make clean` removes them.

## Constraint for Phase B
This sandbox has no Sharadar network access. build/fetch_sharadar_raw.py must run on the operator machine against the licensed Sharadar files; scripts can be written and fixture-tested here, then executed there against real data.

## Amendment 1 (same session, per Jason)
- protocol_version bumped 3.2.3 -> 3.2.4 in core_frozen.yaml (Jason-directed). Full phaseA rerun: PASS, no warnings.
- Release digest superseded: e81980c3... -> 48d0841e6ff305ae... (pending freeze sign-off together with DEFECT-A1 schema change).
- B0-01 remains OPEN pending Jason review of the A1 schema diff (two const fields added to config.schema.json).

## Amendment 2 — Phase B reducer built and fixture-tested (same session)
- build/reduce_sharadar_local.py v1.0 written for OPERATOR-machine execution. SHA-256 of shipped script: 1ab17cb6f1322625d02d7f613bb2fba54cc3fc5db01e9f01ee53d60df794a2b7
- Tested on synthetic 5-ticker/3-member Sharadar fixture, all paths: missing-file FAIL path, default run, chunking path (row-count invariant verified 5217=5217), --include-sf1 path (member+AR filter verified), raw_archive_manifest schema conformance verified with jsonschema.
- Two bugs found and fixed during fixture testing before shipping: (1) chunk-count ZeroDivisionError on max-part-mb<=1 (guarded, arg now float); (2) n/a to script — synthetic generator defect only.
- DESIGN NOTES needing Jason awareness: (a) Sharadar SEP has no openadj column; rule recorded as openadj = open*closeadj/close, applied downstream, uploaded data stays raw-faithful. (b) SP500 join key auto-detected (ticker vs permaticker) and recorded in reduced_manifest.json — feeds B0-04. (c) SF1 skipped by default (M3 disabled); rerun with --include-sf1 when module inventory freezes.
- A1 schema fix APPROVED by Jason this session; B0-01 flip to RESOLVED deferred until digest freeze after GitHub migration decision.
