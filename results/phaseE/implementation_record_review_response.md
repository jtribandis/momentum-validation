# Implementation record — external review response (session 2026-07-16/17)

## 1. Exact clone draws PRESERVED (was: hash only) — F-018 DEFECT FIXED
- REAL BUG: eligible-universe SQL had no ORDER BY. Seeded `random.sample` is order-dependent,
  so the "deterministic" draws were NOT reproducible in principle. ORDER BY permaticker added
  to every sampling universe.
- results/phaseE/clone_draws.parquet: 630,000 rows (10,000 clones x 21 formations x 3 ranks),
  all 9 required columns, canonically sorted by clone_id, formation_date, rank_position.
- Two clean regenerations: content hash IDENTICAL (9c33cd48f8543ded...); parquet bytes identical.
- No returns computed.

## 2. Old-111 reconciliation with EXPLICIT denominators
Prior report placed 111/61/91/5451 adjacent without stating they use different units. Corrected:
  111  = unique terminal EVENTS (permaticker,last_trade_date), name-level proximity
  61   = unique terminal EVENTS actually inside a lot window for a drawn name
  91   = FORMATION-PERMATICKER exposure pairs (different unit; one name, several formations)
  5451 = total clone LOT HITS (counts lots, not events)
Set comparison (50 FP / 0 FN / 61 agree) is valid ONLY on the unique-event sets.
Artifacts: old_vs_new_terminal_worklist_diff.csv, old_vs_new_terminal_worklist_report.json.

## 3. Phase F evidence-preparation governance — plus F-019 DEFECT FOUND AND FIXED
- period_provenance.csv: 2006-2015 row records access_type=CORPORATE_ACTION_EVIDENCE_PREPARATION_ONLY,
  all *_viewed=N, spent_YN=N, plus an explicit "not confirmation execution" statement.
- holdout_guard.py: new --evidence-prep mode permits ONLY formation dates, eligible identities,
  lot-calendar windows, terminal-event identities; REFUSES signals, ranks, selections, clone
  performance, NAV, returns, aggregate performance.
- **F-019 (self-caught):** filling the provenance row made `--period 2006-2015` return PERMIT —
  evidence-prep access would have unlocked the confirmation gate. Added access_type column;
  check_period now REQUIRES access_type=CONFIRMATION_EXECUTION. Two regression cases added.
  Guard self-test: 12/12 PASS; 2006-2015 and 2024-2026 both correctly BLOCK.

## 4. Enriched, SEPARATED queues (combined queue deleted)
- dev_clone_transaction_review_queue.csv: 91 rows / 61 unique permatickers
  (ACQUIRED 83, DELISTED_OTHER 6, BANKRUPTCY 2), all 26 required fields, priority-ranked.
- phaseF_possible_transaction_review_queue.csv: 176 rows / 105 unique permatickers
  (ACQUIRED 164, DELISTED_OTHER 10, BANKRUPTCY 2), all P4_CONTINGENT_SEALED_PERIOD.
- cik is NOT in vendor data -> field present, marked NOT_IN_VENDOR_DATA_REQUIRES_SEC_LOOKUP.

## 5. Common accounting engine — IMPLEMENTED, PARTIALLY CERTIFIED
- engine/accounting_engine.py: independent overlapping lots, sleeve cash, entry/exit costs,
  involuntary terminal cash (no exit cost), successor conversion, monthly marks, NAV,
  lot lineage (parent_lot_ids), cash reconciliation. CORE and clones differ ONLY in the
  `select` callable passed to run().
- Tests: 10/10 PASS (qa/test_accounting_engine.py) — golden_v2 lot reproduction against
  Jason's hand-derived values, terminal-cash/market-exit cost asymmetry, bankruptcy = -1.0,
  successor conversion, overlapping-lot independence, redeploy lineage, reconciliation identity,
  and a test proving CORE/clone differ only by selection operator.
- **HONEST STATUS: NOT fully certified.** Terminal BRANCH values cannot be certified until Jason
  hand-derives golden_v3 expected_outputs_SIGNED.csv. A test documents this block explicitly.
  run_core_backtest.py / run_clone_null.py are NOT yet migrated to this engine — that migration
  must happen before any rerun, and is deliberately not done in the same session as a rerun.

## 6. Status synchronized
terminal_policy.yaml evidence_status=VENDOR_SEMANTICS_COMPLETE_TRANSACTION_EVIDENCE_PENDING,
effective_before_rerun=false (unsigned). B0-05 = PARTIAL_OPEN in blocker_ledger + dashboard.
No performance, CAGR, clone null, or sealed-period result was run.
