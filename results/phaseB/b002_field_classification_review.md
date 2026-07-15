# B0-02 Field Classification Review — vintage SHARADAR_20260620
Prepared for Jason's ruling (session 2026-07-15). B0-02 closes when every ruling below is
answered and this file's status line is flipped by Jason in a commit.

STATUS: RULINGS_COMPLETE_2026-07-15 — R1/R2/R3/R5 ruled, R4 acknowledged. B0-02 closes at merge.

## Summary of live headers vs expectations
- SEP: 10/10 expected fields present, zero unknowns. CLASSIFIED.
- TICKERS: 28 live fields; 1 unknown (`figi`); 1 expected-but-absent (`famasector`, unused by CORE — no impact).
- SP500: 7/7 expected. Observed action vocabulary in the actual data: {historical, current, added, removed}. CLASSIFIED pending R3.
- ACTIONS: 7/7 expected. `value` units remain UNVERIFIED (existing B0-05, unchanged).
- SF1: 112 live fields, none pre-classified by design (M3-only table).

## Rulings requested

**R1 — TICKERS.figi (VARCHAR).** I am confident this is the Financial Instrument Global
Identifier (OpenFIGI). It is not used by any protocol computation; permaticker remains the
sole identity key per the data fidelity contract.
RECOMMENDATION: classify QUARANTINED_UNUSED. → Jason: **RULED 2026-07-15: QUARANTINED_UNUSED.**

**R2 — SEP.closeadj adjustment basis (OV-01).** My belief — flagged as unverified: Sharadar's
closeadj is adjusted for BOTH splits and dividends, closeunadj is fully raw, and close is
split-adjusted only. This must be confirmed by you against the Sharadar SEP documentation in
your NASDAQ Data Link account before Phase B sign-off; the trail-6/skip-1 signal and total-
return accounting both depend on it. Do not take my belief as the record.
RECOMMENDATION: Jason reads vendor doc, records confirmed semantics here with a quote/pointer. → Jason: **RULED 2026-07-15. Verbatim vendor documentation as provided by Jason:**
> "The following corporate adjustments are applied to the fields listed below:
> Open, High, Low, Close and Volume — The above fields are adjusted for stock splits and
> stock dividends. They are not adjusted for cash dividends or spinoffs.
> CloseAdj — The above field is adjusted for stock splits, stock dividends, cash dividends
> and spinoffs.
> CloseUnadj — This field is unadjusted and does not apply corporate adjustments for stock
> splits, stock dividends, cash dividends or spinoffs."

**Recorded implications (binding on downstream builders):**
1. openadj = open x closeadj / close is VALID: open and close share the split/stock-dividend
   basis, so the ratio applies exactly the cash-dividend + spinoff factor. This corrects the
   pre-ruling belief that close was split-adjusted-only in a stricter sense; the derivation
   outcome is unchanged.
2. Signal closeadj(M-1)/closeadj(M-7) is total-return momentum (splits, stock+cash dividends,
   spinoffs) — consistent with the frozen signal definition.
3. Volume is split-adjusted; any share-count arithmetic must NOT re-apply split factors.
4. closeunadj is the only fully raw price; split-invariance QC checks must use it.
OV-01 (SEP price-field semantics) is SATISFIED by this ruling.

**R3 — SP500.action vocabulary.** Observed values in the real table: added, removed, current,
historical (counts: 1,232 / 735 / 503 / 56,690). The membership builder treats
historical+current as PIT snapshots and added/removed as the event stream.
RECOMMENDATION: confirm this treatment. → Jason: ____ (pending)

**Evidence issued 2026-07-15 for this ruling — what to look at:**
(a) Plain-words treatment: 'historical' and 'current' rows are the vendor's direct statements
    of index composition on a date -> used as the PIT source of truth at rebalance gates.
    'added'/'removed' rows are the change log -> reconstructed into intervals used ONLY as a
    consistency check, never as the gate.
(b) Code: build/build_sp500_membership.py — docstring (treatment + interval convention) and
    the 'snaps' / 'events' sections.
(c) Report: results/phaseC/membership_build_report.json — snapshot_member_counts (499-505,
    avg 501.6: matches true index size) and cross_validation block.
(d) Spot checks against public record, run on the real data:
    - TSLA: vendor event added 2020-12-21 (matches its publicly known S&P inclusion date);
      NOT in the 2020-09-30 snapshot, IS in the 2020-12-31 snapshot; interval opens 2020-12-21.
    - ALK (Alaska Air): vendor event removed 2023-12-18; present in the 2023-09-30 snapshot,
      absent from the next; interval closes 2023-12-17 (day-before convention).
To rule: confirm (a) matches your intent. If yes, write RULED next to R3.

**RULED per Jason's instruction 2026-07-15: treatment confirmed (snapshots gate, intervals check).**

**R4 — ACTIONS.value units.** No new information; stays UNVERIFIED under B0-05 with terminal
events at the Shumway baseline until you verify units against vendor docs. No ruling needed
here — listed for completeness. → acknowledged: **YES — Jason 2026-07-15; B0-05 remains the open verification item.**

**R5 — SF1 (all 112 fields).** Only relevant if module M3 (quality/value) activates.
RECOMMENDATION: classify the entire table QUARANTINED_UNUSED_UNTIL_M3, with the five key
fields (ticker, dimension, calendardate, datekey, reportperiod) getting full PIT-semantics
review at the M3 gate — in particular whether `datekey` is the filing-availability date,
which is the point-in-time-critical question. → Jason: **RULED 2026-07-15: QUARANTINED_UNUSED_UNTIL_M3, with PIT review of the five key fields (esp. datekey) at the M3 gate.**

## Non-ruling notes
- `openadj` does not exist in SEP; derivation rule openadj = open x closeadj / close is
  recorded in reduced_manifest.json and will be implemented in build_price_panel.py, contingent on R2.
- famasector absent from this vintage's TICKERS; famaindustry present. No protocol impact.
