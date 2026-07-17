# Status dashboard

Current allowed claim tier: `T0_EXECUTABLE_SCAFFOLD`

## Next fixes

1. **B0-02 - Vendor semantics verification**: Print live Sharadar headers and classify fields; quarantine unknown PIT fields Evidence: `results/phaseB/vendor_semantics_report.json`. If unresolved, downgrade to `T0_EXECUTABLE_SCAFFOLD`.
1. **B0-03 - Raw-source archive**: Save retrieval command, timestamp, row count, byte hash, schema hash, and vintage ID Evidence: `manifests/raw_archive_manifest.json`. If unresolved, downgrade to `T0_EXECUTABLE_SCAFFOLD`.
1. **B0-05 - Terminal-event semantics**: Vendor semantics RESOLVED 2026-07-16 (evidence/vendor_semantics/, sha256 52ef6da7). Transaction-specific evidence still required per event class: SEC 8-K Item 2.01/1.03, merger agreement consideration, exchange ratios, equity recovery. Queues: results/phaseE/dev_clone_transaction_review_queue.csv (91), phaseF_possible_transaction_review_queue.csv (176). Evidence: `results/phaseB/terminal_event_semantics.json`. If unresolved, downgrade to `T0_EXECUTABLE_SCAFFOLD`.
1. **B0-06 - Holdout attestations**: Record prior viewing status before opening 2006-2015 or 2024-2026 Evidence: `protocol/period_provenance.csv`. If unresolved, downgrade to `T0_EXECUTABLE_SCAFFOLD`.
1. **B0-07 - Golden-v1 fixture approval**: Approve expected selections by executable and human-readable methods Evidence: `results/phaseE/golden_report.json`. If unresolved, downgrade to `T0_EXECUTABLE_SCAFFOLD`.

## Full gate table

| Gate | Status | Phase | Claim tier affected | Fix | Evidence | Downgrade if unresolved |
|---|---:|---|---|---|---|---|
| B0-01 - Protocol/config freeze | RESOLVED | Phase A | T0+ | Create protocol_release.json and frozen YAML/config schemas before data access | results/phaseA/config_validation.json | T0_DESIGN_ONLY |
| B0-02 - Vendor semantics verification | OPEN | Phase B | T1+ | Print live Sharadar headers and classify fields; quarantine unknown PIT fields | results/phaseB/vendor_semantics_report.json | T0_EXECUTABLE_SCAFFOLD |
| B0-03 - Raw-source archive | OPEN | Phase B | T1+ | Save retrieval command, timestamp, row count, byte hash, schema hash, and vintage ID | manifests/raw_archive_manifest.json | T0_EXECUTABLE_SCAFFOLD |
| B0-04 - PIT S&P 500 identity resolution | RESOLVED | Phase C | T1+ | Resolve residual identities touching evaluated 1998+ members, selections, clones, terminal events, or review samples | results/phaseC/membership_audit.json | T0_EXECUTABLE_SCAFFOLD |
| B0-05 - Terminal-event semantics | PARTIAL_OPEN | Phase B/F | T1+ | Vendor semantics RESOLVED 2026-07-16 (evidence/vendor_semantics/, sha256 52ef6da7). Transaction-specific evidence still required per event class: SEC 8-K Item 2.01/1.03, merger agreement consideration, exchange ratios, equity recovery. Queues: results/phaseE/dev_clone_transaction_review_queue.csv (91), phaseF_possible_transaction_review_queue.csv (176). | results/phaseB/terminal_event_semantics.json | T0_EXECUTABLE_SCAFFOLD |
| B0-06 - Holdout attestations | OPEN | Phase F/K | T1+ | Record prior viewing status before opening 2006-2015 or 2024-2026 | protocol/period_provenance.csv | T0_EXECUTABLE_SCAFFOLD |
| B0-07 - Golden-v1 fixture approval | OPEN | Phase E | T1+ | Approve expected selections by executable and human-readable methods | results/phaseE/golden_report.json | T0_EXECUTABLE_SCAFFOLD |
| B0-08 - Numerical tail rule freeze | OPEN | Phase F | T1+ | Freeze validation vetoes and deployment-risk flags before confirmation results | config/risk_limits.yaml | T0_EXECUTABLE_SCAFFOLD |
| B0-09 - M3/M4 module inventory | OPEN | Phase H/I | T2+ | Freeze module_inventory.yaml or keep modules disabled for CORE | config/module_inventory.yaml | T1_SELF_REVIEWED_CORE_IMPLEMENTATION |
| B0-10 - Source-verification ledger | OPEN | Publication | T2+ | Verify source links and source-claim map before public claims | evidence/source_verification/source_claim_map.csv | T1_SELF_REVIEWED_CORE_IMPLEMENTATION |
| B0-11 - External spot-check review | OPEN | Publication/Deployment | T2+ | Obtain external review for golden fixture, terminal events, holdout attestations, and final narrative | evidence/external_review/ | T1_SELF_REVIEWED_CORE_IMPLEMENTATION |
