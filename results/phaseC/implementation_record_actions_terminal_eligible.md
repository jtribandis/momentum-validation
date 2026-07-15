# Implementation record — actions, terminal events, eligibility, audit (session 2026-07-15)

## Executed (all against vintage SHARADAR_20260620)
- F-012 grace fix to membership mapping, membership rebuilt: 114 snapshots (2026-06-20 now included), counts 499-505.
- build_actions.py: 65,226/65,321 mapped; value carried with value_units_unverified=TRUE (B0-05 untouched).
- build_terminal_events.py: 520 terminated ever-members, 100% action-evidenced
  (443 ACQUIRED, 56 BANKRUPTCY_LIQUIDATION, 12 DELISTED_OTHER, 9 MERGER, 0 NO_ACTION_EVIDENCE).
  Classification only — numeric Shumway-baseline returns deliberately deferred to engine config
  (Phase D/E) gated on B0-05 + the outstanding Nasdaq-figure citation confirmation.
- build_eligible_snapshots.py: 79 formations 1998-09-30..2026-03-31 (E1 snapshot member,
  E2 closeadj at M-1 & M-7, E3 openadj within 5 trading days of M+1); eligible 496-505/formation.
- qa/audit_membership.py: B0-04 worklist reduced 883 tickers -> 14 evaluated-era items
  (9 added-events, 4 snapshot rows over 4 dates, 1 absent ticker string); 387 pre-coverage no-impact.
- sep_prices chunked to 2 committed parts (74.6/75.1 MB) per Jason decision; chunk row-count
  invariant asserted in-build; dependents repointed to glob.

## For Jason (B0-04 ruling)
results/phaseC/membership_audit.json -> 'evaluated_era_worklist' (14 rows). Classify each or
approve bulk classification; then B0-04 can close.
