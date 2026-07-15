# B0-02 Field Classification Review — vintage SHARADAR_20260620
Prepared for Jason's ruling (session 2026-07-15). B0-02 closes when every ruling below is
answered and this file's status line is flipped by Jason in a commit.

STATUS: AWAITING_JASON_RULINGS

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
RECOMMENDATION: classify QUARANTINED_UNUSED. → Jason: ____

**R2 — SEP.closeadj adjustment basis (OV-01).** My belief — flagged as unverified: Sharadar's
closeadj is adjusted for BOTH splits and dividends, closeunadj is fully raw, and close is
split-adjusted only. This must be confirmed by you against the Sharadar SEP documentation in
your NASDAQ Data Link account before Phase B sign-off; the trail-6/skip-1 signal and total-
return accounting both depend on it. Do not take my belief as the record.
RECOMMENDATION: Jason reads vendor doc, records confirmed semantics here with a quote/pointer. → Jason: ____

**R3 — SP500.action vocabulary.** Observed values in the real table: added, removed, current,
historical (counts: 1,232 / 735 / 503 / 56,690). The membership builder treats
historical+current as PIT snapshots and added/removed as the event stream.
RECOMMENDATION: confirm this treatment. → Jason: ____

**R4 — ACTIONS.value units.** No new information; stays UNVERIFIED under B0-05 with terminal
events at the Shumway baseline until you verify units against vendor docs. No ruling needed
here — listed for completeness. → acknowledged: ____

**R5 — SF1 (all 112 fields).** Only relevant if module M3 (quality/value) activates.
RECOMMENDATION: classify the entire table QUARANTINED_UNUSED_UNTIL_M3, with the five key
fields (ticker, dimension, calendardate, datekey, reportperiod) getting full PIT-semantics
review at the M3 gate — in particular whether `datekey` is the filing-availability date,
which is the point-in-time-critical question. → Jason: ____

## Non-ruling notes
- `openadj` does not exist in SEP; derivation rule openadj = open x closeadj / close is
  recorded in reduced_manifest.json and will be implemented in build_price_panel.py, contingent on R2.
- famasector absent from this vintage's TICKERS; famaindustry present. No protocol impact.
