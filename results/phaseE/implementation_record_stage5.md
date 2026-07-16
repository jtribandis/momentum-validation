# Implementation record — FD freeze + Stage 5 CORE backtest (session 2026-07-16)

## FD-01/FD-02/F-007 — frozen, cross-referenced, BEFORE any result viewed
- Cross-referenced canon (§5.2/§5.4/§10.1) + web consensus on MC permutation gates and ruin
  bounds. FD-01 (99th pct + 3% floor) and FD-02 (-80% veto, 20% HWM floor, -35% gap flags)
  both consistent with canon and consensus; SAFE, frozen.
- F-007 RESOLVED: canon FD-02 = -35%; risk_limits.yaml corrected from -25%; missing canon flags
  added. New release digest 4cb6602e63251b6e.

## Stage 5 CORE backtest (2016-2023 development) — PRELIMINARY, primary gate FAILS
- run_core_backtest.py: 21 formations, 63 lots, unlevered CORE CAGR 18.03%.
- run_clone_null.py: 10,000 exchangeable clones, deterministic seed from blotter hash.
  CORE at 32.2nd percentile; clone median 23.16%, p99 54.33%. FD-01 primary gate = FAIL
  (both percentile and 3% floor).

## HONEST STATUS: this is NOT a decision-grade result. Registered F-014 and F-015.
Three unresolved factors bias or weaken the comparison, all directionally relevant:
1. F-014: terminal-return placeholder (last close) pending B0-05 + citation; penalizes CORE if
   momentum over-selects future delistings.
2. Clone universe is full ~500-name index (very high random-draw variance, demanding null).
3. Leveraged-ETF deployment layer (confirmed ablation value-add) NOT in unlevered CORE return.
No holdout opened or touched. FD freeze predates the result, so the gate is not post-hoc.

## For Jason (rulings before Stage 5 can be decision-grade)
- Close B0-05 + Nasdaq citation -> freeze terminal-return policy -> re-run (F-014).
- Decide clone-null refinement per S5.3 (block/stationary bootstrap; regime-matched clones).
- Decide whether the deployment layer enters the primary comparison or stays a separate track.
