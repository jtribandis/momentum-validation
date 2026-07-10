# Implementation DAG

The controlling dependency chain is:

```text
B0 blockers
  -> Phase A protocol/config/ledger freeze
  -> Phase B raw archive
  -> Phase B cleaned Sharadar outputs
  -> Phase C PIT membership intervals and eligible snapshots
  -> Phase D immutable compact bundle
  -> Phase E golden_v1 fixture and software assurance
  -> Phase E accounting engine gate
  -> Phase F CORE backtest and 10,000-clone null
  -> Phase G factor attribution and diagnostic reports
  -> Phase H/I module work only if module_inventory.yaml is frozen
  -> Phase J selected stress
  -> Phase K forward holdout
  -> Phase L leave-name-out influence diagnostic
  -> Phase M final dashboard, evidence package, and allowed claim language
```

No target may skip an upstream blocker. If a blocker is unresolved, either resolve it, downgrade the claim tier in `blocker_ledger.csv`, or stop before the affected phase.
