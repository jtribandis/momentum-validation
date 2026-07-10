# Momentum validation solo executable package v3.2.4

This package is a **minimal executable scaffold**, not a completed backtest. It exists to make the manual operational without weakening the scientific design. It separates:

- **Scaffold checks**: the package shape, schemas, contracts, dashboard, and task graph exist.
- **Blocking gate checks**: unresolved blockers, missing implementation scripts, header-only fixtures, unverified source claims, and unreviewed holdouts prevent higher claim tiers.
- **Result-bearing targets**: backtests, clone nulls, stress tests, forward holdouts, and LNO diagnostics are disabled until Phase A-E gates pass.

Start here:

```bash
make scaffold-check       # should pass for the package itself
make status               # regenerates status_dashboard.md and status_dashboard.csv
make blocker-check        # intentionally fails while B0 blockers remain OPEN
make phaseA               # first implementation phase after B0-01 inputs are filled
```

Current allowed claim tier is controlled by `status_dashboard.csv`, not by narrative text. Scientific design is frozen in `protocol_contracts/` and implementation scripts must read contract/config files rather than hard-coding economic rules.
