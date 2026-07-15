# Google Sheets guide — golden fixture hand-derivation (G6)

Sheets IS allowed: building your own formulas from the spec is "hand derivation." What is
prohibited is importing numbers produced by any engine I wrote. You build every formula
yourself from README_spec.md; spot-check a few cells on a calculator.

## Setup (10 min)
1. New spreadsheet "golden_v2_derivation". File > Import each CSV from
   fixtures/golden_v2/inputs/ into its own tab: Prices, Opens, Membership, Terminal, Config.
2. In Prices, Insert > Pivot table (new tab "PriceGrid"): Rows = month_end_date,
   Columns = permaticker, Values = closeadj. Now every price is a cell you can point at.

## Tab "Signals" (15 min)
Grid: 8 columns (permatickers) x 3 rows (formations). Each cell:
  = PriceGrid[M-1 close] / PriceGrid[M-7 close] - 1
For F1 (2020-03-31): M-1 = 2020-02-28 row, M-7 = 2019-08-30 row. Format 6 decimals.
Sanity: GA at F1 should be a clean 0.240000 — if not, your row references are off.

## Tab "Selection" (10 min)
Under each formation, sort the 8 signals descending (=SORT(TRANSPOSE(...), 1, FALSE) or
manually). Identify top 3. F1 HAS AN EXACT TIE at 3rd — the spec says lower permaticker
wins. Write the three permatickers in rank order.

## Tab "Lots" (30-40 min — the core work)
One row per lot (9 lots). Columns: sleeve, formation, permaticker, deploy_date,
entry_open, alloc, shares, entry_cost, exit_date, exit_open_or_deal, exit_proceeds, lot_return.
  shares      = alloc / (entry_open * 1.001)
  entry_cost  = shares * entry_open * 0.001
  exit_proceeds = shares * exit_open * 0.999          (market exits)
  terminal_cash = shares * 90.00                      (GE lots only, no cost)
  lot_return  = exit_value / alloc - 1
F1/F2 allocs are 50,000 each. F3 allocs = (sum of the three F1 exit_proceeds) / 3 — chain
the cell references so a change upstream flows through.

## Tab "NAV" (20-30 min)
Rows = the 14 dates in the template. Columns = one per lot + sleeve-cash columns + total.
Active lot mark = shares * that month-end closeadj (point at PriceGrid). Rules:
- A lot appears from its deploy month-end through the month-end BEFORE its exit date.
- GE lots: marked at closeadj through 2020-10-30; from 2020-11-30 onward replaced by
  terminal cash (constant, 0% rate) inside their sleeve until the sleeve's next event.
- 2020-03-31 total must be exactly 300,000.00. 2021-04-01 row: everything is cash.
Cross-check: NAV should never jump on a deploy day (open = prior close by construction),
except by exactly the 10bps costs.

## Tab "Export"
Recreate the template's 4 columns, point each value_JASON_FILLS at your computed cell with
ROUND(...,6) or ROUND(...,2) per the field name. Download as CSV ->
expected_outputs_SIGNED.csv -> commit to fixtures/golden_v2/ with a message stating the
values are hand-derived. Your merge freezes golden truth.

Budget: ~90 minutes. If any number feels surprising, that is the fixture doing its job —
resolve it on paper before exporting.
