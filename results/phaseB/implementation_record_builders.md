# Implementation record — security master + price panel (session 2026-07-15)

## Executed
- build_security_master.py: PASS. 21,859 permatickers, 0 duplicates, 0 ETF/ETN among
  ever-members (leveraged-ETF exclusion verified vacuous under the S&P membership gate).
- build_price_panel.py: PASS. 5,468,910 rows, 100% permaticker-mapped (0 dropped, 0 unmapped
  tickers, 0 duplicate permaticker-dates, 0 null/nonpositive closeadj/openadj/closeunadj).
- openadj derived per R2 ruling: open * closeadj / close.
- Month-end calendar built: 343 month-ends, 1997-12 .. 2026-06.

## F-005 derivation (mechanical)
First computable signal month-end 1998-07-31; first computable quarterly rebalance 1998-09-30.
Findings log updated; the Phase K window *ruling* stays open by design.

## QC calibration note (bug-class: threshold, caught in first run)
Split-invariance factor-break detector at 1e-6 relative tolerance fired on 74% of rows —
float rounding jitter in stored prices, not real breaks. Recalibrated to 1e-3 (above rounding
noise, below real dividend factors): 65,540 break-days vs 65,321 ACTIONS rows for the same
universe — near one-to-one corroboration of R2 semantics. 859 extreme adjusted moves (>50%
daily) recorded as the tail-audit worklist input.

## Repo storage decision (stated)
data/clean/sep_prices.parquet (150MB) is NOT committed: exceeds GitHub's 100MB hard limit and
is a deterministic rebuild from committed inputs (make phaseB). Its SHA-256 is recorded in
results/phaseB/price_panel_report.json each build; reproducibility is hash-verified, not
storage-verified. Small clean artifacts (security master 0.4MB, calendar 3KB, membership
parquets) ARE committed.
