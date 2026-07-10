# Operator runbook - solo executable path v3.2.4

## 1. Blockers before build

Run:

```bash
make status
make blocker-check
```

If `make blocker-check` fails, open `status_dashboard.md`. Fix the first OPEN blocker whose affected phase is equal to or earlier than the phase you want to run. Do not start result-bearing computation while B0-01 through B0-08 are OPEN.

## 2. Claim tiers

- `T0_DESIGN_ONLY`: manual and package scaffold exist; no implementation claim.
- `T0_EXECUTABLE_SCAFFOLD`: package layout, contracts, schemas, task graph, dashboard, and failing blocker gates exist.
- `T1_SELF_REVIEWED_CORE_IMPLEMENTATION`: Phase A-F implemented, self-reviewed, and all blocking B0 items resolved or downgraded with explicit limitations.
- `T2_EXTERNAL_REVIEW_READY`: source claim map and external spot checks complete for publication-facing statements.
- `T3_DEPLOYMENT_FACING_EVIDENCE_PACKAGE`: external review, terminal-event verification, holdout attestations, tail audit, and final narrative review complete.

The current tier is emitted by `tools/update_status_dashboard.py`.

## 3. Command sequence

```bash
make scaffold-check
make status
make phaseA
make phaseB
make phaseC
make phaseD
make phaseE
make phaseF
make phaseG
make phaseJ
make phaseK
make phaseL
make package-results
```

M3/M4 module targets remain disabled unless `config/module_inventory.yaml` exists, is frozen, and passes module-contract checks.

## 4. Failure-to-fix index

- Missing scaffold file: create the listed file or restore from the ZIP.
- OPEN blocker: update evidence file, set status to `RESOLVED`, `DOWNGRADED`, or `NOT_APPLICABLE`, and document residual limitation.
- Header-only golden fixture: populate at least one approved fixture row and preserve approval notes in `fixtures/golden_v1/README.md`.
- NOT IMPLEMENTED script: implement the named script, make it read contract/config files, emit the expected artifact, and add tests before rerunning the phase target.
- Source not verified: update `evidence/source_verification/source_claim_map.csv` or remove/soften the corresponding public claim.

## 5. Runtime notes

Expected first-pass solo workload is CPU-bound and disk-bound, not GPU-bound. Use DuckDB/Parquet streaming for raw/clean tables. Treat 10,000 clones, LNO reruns, and M3/M4 walk-forward as heavy jobs; if runtime is excessive, reduce only for mechanics smoke tests and label outputs `SMOKE_ONLY`, never decision-grade.
