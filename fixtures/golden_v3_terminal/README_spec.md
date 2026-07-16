# Golden fixture v3 — terminal-event cases (extends golden_v2; G6 discipline unchanged)

Purpose: prove the terminal_policy.yaml branches are implemented correctly. Same anti-
circularity rule as golden_v2: **Jason hand-derives every expected value**; no engine output
may be copied in. Same Google Sheets method (docs/golden_derivation_google_sheets_guide.md).

Six single-lot cases, deliberately minimal so each isolates ONE branch. Every case: one lot,
$30,000 allocation, 10bps entry cost, deploy 2020-07-01, scheduled maturity exit 2021-01-04.

| case | branch | event | inputs |
|------|--------|-------|--------|
| T1 | cash_acquisition | cash-out $88.00/sh at legal completion 2020-11-16 | entry open 60.00 |
| T2 | stock_acquisition | 0.75 successor shares/sh on 2020-11-16; successor trades to maturity | entry open 60.00; successor opens 2021-01-04 at 95.00 |
| T3 | mixed_acquisition | $20.00 cash + 0.40 successor shares/sh on 2020-11-16 | entry open 60.00; successor open 2021-01-04 = 95.00 |
| T4 | verified_bankruptcy_zero_recovery | confirmed plan, no equity recovery, 2020-11-16 | entry open 60.00 |
| T5 | identity_continuation | ticker change 2020-11-16, same permaticker | entry open 60.00; maturity open 71.00 |
| T6 | unverified_ma | delisting, no evidence: freeze last tradable closeadj 57.50 | entry open 60.00 |

## Rules to apply (from config/terminal_policy.yaml — read it, do not infer)
- shares = 30000 / (entry_open x 1.001) for every case.
- T1: proceeds = shares x 88.00, NO exit cost (involuntary corporate action).
- T2: successor_shares = shares x 0.75; NO conversion cost; exit at maturity =
  successor_shares x 95.00 x 0.999 (scheduled maturity IS a market trade -> 10bps).
- T3: cash leg = shares x 20.00 (no cost, held at 0% to maturity);
  stock leg = shares x 0.40 x 95.00 x 0.999. Total = both legs.
- T4: terminal value = 0.00; lot_return = -1.000000 exactly.
- T5: NOT an exit. Lot continues; exit at maturity = shares x 71.00 x 0.999.
- T6: proceeds = shares x 57.50, no cost. (Canon fallback.)
- lot_return = terminal_or_exit_value / 30000 - 1 in every case.
- REQUIRED SENSITIVITY ROW: T6 recomputed at -100% (terminal value 0) per S3.6.

Fill fixtures/golden_v3_terminal/expected_outputs_TEMPLATE.csv, export as
expected_outputs_SIGNED.csv, commit it yourself stating the values are hand-derived.
