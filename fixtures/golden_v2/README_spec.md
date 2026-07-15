# Golden fixture v2 — specification (protocol v3.2.4, FD-04/G6)

Purpose: Jason hand-derives every value in expected_outputs_TEMPLATE.csv from the input CSVs
alone. The completed file is frozen as golden truth; all three engines (Python, JS, DuckDB)
must reproduce it. AI-computed values may NOT be copied in — that is the circularity this
fixture exists to prevent.

## Inputs (fixtures/golden_v2/inputs/)
- month_end_prices.csv — closeadj per security per month-end, 2019-08..2021-04.
  GE (900005) has NO prices after 2020-10-30: it is acquired 2020-11-16.
- opens.csv — openadj on the five deploy/exit days. By construction each equals the prior
  month-end closeadj (rule recorded in fixture_config.csv).
- membership_snapshots.csv — all 8 names are members at every formation (GE drops out after
  its acquisition; no formation in this fixture is affected).
- terminal_events.csv — GE ACQUIRED_CASH at $90.00/share on 2020-11-16 (§3.6 tier 1:
  verified deal terms; no exit trading cost on a corporate cash-out).
- fixture_config.csv — all frozen parameters (10bps per side, tie-break, sleeves, 0% cash).

## Mechanics to derive (in order)
1. SIGNALS: at each formation M, signal = closeadj(M−1)/closeadj(M−7) − 1. 24 values.
2. SELECTION: rank descending; top 3. F1 contains a designed exact tie at 3rd place —
   resolve by permaticker ASCENDING. Record top-3 as "pt1;pt2;pt3" in rank order.
3. LOTS: sleeve A = $150,000 deploys at F1 (2020-04-01) split equally: $50,000 per name.
   shares = 50000 / (openadj × 1.001)   [10bps entry cost inside the fill]
   entry_cost = 50000 − shares × openadj  (equivalently shares × openadj × 0.001)
   Sleeve B = $150,000 deploys at F2 (2020-07-01) the same way.
   F1 lots exit 2020-10-01 at openadj × 0.999 (10bps exit): exit_proceeds = shares × openadj × 0.999.
   Sleeve A's total F1 proceeds redeploy at F3 (2020-10-01), split equally three ways.
   F2 lots exit 2021-01-04; F3 lots exit 2021-04-01.
   GE TERMINAL (both the F2-GE and F3-GE lots): terminal_cash = shares × 90.00 on 2020-11-16,
   NO exit cost; the cash sits at 0% inside its sleeve until that sleeve's next event.
   lot_return = (exit_proceeds or terminal_cash) / (shares × openadj_entry × 1.001) − 1.
4. NAV: at each month-end, NAV = Σ active lot marks (shares × that month-end closeadj)
   + sleeve cash (terminal cash after 2020-11-16; sleeves are all-cash before their first deploy).
   NAV(2020-03-31) = 300,000.00 exactly (nothing deployed yet).
   Final row: NAV on 2021-04-01 immediately after F3 exits (all cash).

## Freeze procedure
Fill value_JASON_FILLS for every row (respect the decimal precision in each field name),
export as CSV named expected_outputs_SIGNED.csv, commit to fixtures/golden_v2/ yourself,
and state in the commit message that every value was hand-derived. Merge = golden freeze.
