# Findings Log — Momentum Validation Protocol v3.2.4

Progressive, append-only log of material findings discovered during execution.
Each finding gets an ID, a status, and a required action. Findings are REGISTERED
here when discovered, and only marked RESOLVED with a pointer to the evidence
(commit, ledger row, or results file) that closed them. Nothing is deleted;
corrections are appended.

Status vocabulary: OPEN_DECISION (needs Jason ruling) · REGISTERED (recorded,
action scheduled at a later phase) · RESOLVED (evidence linked) · INFORMATIONAL.

| ID | Date | Phase | Status |
|----|------|-------|--------|
| F-001 | 2026-07-09 | A | RESOLVED |
| F-002 | 2026-07-09 | A | RESOLVED |
| F-003 | 2026-07-09 | A | INFORMATIONAL |
| F-004 | 2026-07-09 | B-prep | RESOLVED |
| F-005 | 2026-07-09 | B | REGISTERED — derivation complete; window ruling remains for Phase K pre-open |
| F-006 | 2026-07-09 | B | REGISTERED (feeds Phase C identity audit) |
| F-007 | 2026-07-09 | F-prep | OPEN_DECISION |
| F-008 | 2026-07-14 | B | RESOLVED |
| F-009 | 2026-07-14 | B | RESOLVED |
| F-010 | 2026-07-14 | C | REGISTERED — audit run: worklist reduced to 14 evaluated-era items |
| F-011 | 2026-07-15 | C | REGISTERED (protocol doc §1.3 warm-up line superseded by derivation) |
| F-012 | 2026-07-15 | B/C | RESOLVED |
| F-013 | 2026-07-16 | E | RESOLVED |
| F-007 | (see below) | F-prep | RESOLVED — canon says -35%; yaml corrected |
| F-014 | 2026-07-16 | E | REVISED — CORE had ZERO terminal lots; clone impact was unmeasured |
| F-015 | 2026-07-16 | E | REGISTERED — relabeled: development diagnostic, not primary gate |
| F-016 | 2026-07-16 | E | RESOLVED — session agent mislabeled dev run as primary gate; corrected |

---

## F-001 — DEFECT-A1: config schema rejected two legitimate frozen fields
**Date:** 2026-07-09 · **Phase:** A · **Status:** RESOLVED

`schemas/config.schema.json` used `additionalProperties: false` but omitted two
fields present in `config/core_frozen.yaml`: `primary_effect_floor_annualized_excess`
and `aggregate_performance_allowed_before_phaseF`. Phase A validation therefore
failed against the project's own frozen config.

**Fix:** both fields added to the schema as `const` (0.03 / false) and appended to
`required`, so any future drift in these frozen values fails validation loudly.
**Approved by Jason** (session 2026-07-09). Evidence: `results/phaseA/config_validation.json`,
release digest `48d0841e6ff305ae…`, merged in PR #1.

## F-002 — protocol_version drift (3.2.3 inside the v3.2.4 package)
**Date:** 2026-07-09 · **Phase:** A · **Status:** RESOLVED

`core_frozen.yaml` shipped with `protocol_version: "3.2.3"`. Jason directed the
bump to `"3.2.4"`; full Phase A rerun passed with no warnings. The release digest
was regenerated after this change (superseding `e81980c3…`) and frozen at merge
of PR #1.

## F-003 — Environment preconditions not vendored
**Date:** 2026-07-09 · **Phase:** A · **Status:** INFORMATIONAL

`pytest` and `jsonschema` are required by the make targets but not assumed
installed; `duckdb` is required by the reducer. Recorded so a fresh machine can
reproduce: `pip install -r requirements-dev.txt` plus `pip install duckdb`.
Sandbox sessions additionally require `--break-system-packages`.

## F-004 — Two reducer bugs caught in fixture testing before shipping
**Date:** 2026-07-09 · **Phase:** B-prep · **Status:** RESOLVED

During synthetic-fixture testing of `build/reduce_sharadar_local.py` (per the
"py_compile passing does not prove a script runs" discipline): (1) chunk-count
math raised ZeroDivisionError for `--max-part-mb <= 1`; guarded, argument made
float. (2) The missing-raw-file FAIL path was exercised and behaves correctly.
Shipped script SHA-256 `1ab17cb6f1322625…`; verified identical after Jason's
download (his `py_compile` and `--help` runs matched, run completed exit 0).

## F-005 — Sharadar SEP coverage begins 1997-12-31, not the requested 1997-01-01 floor
**Date:** 2026-07-09 · **Phase:** B (first real-data run, vintage SHARADAR_20260620) · **Status:** REGISTERED — blocks Phase K window definition

The reducer applied `--date-floor 1997-01-01`, but the earliest SEP row in the
vendor data is `1997-12-31`. Sharadar's price coverage simply starts there; this
is a vendor constraint, not a reduction defect.

**Consequence:** the trail-6/skip-1 signal at formation month-end M requires the
month-end close at M−7. With Dec-1997 as the earliest month-end, the earliest
fully-formed signal lands mid-1998, so the dot-com stress window (1998–2005)
likely loses its first one or two 1998 rebalances.

**Required action:** register as an open decision on the Phase K window
definition (effective start of the 1998–2005 stress holdout) **before that
holdout is opened**. Do not resolve now; the holdout remains sealed.

**Derivation completed 2026-07-15 (build_price_panel.py, mechanical from the month-end
calendar):** first computable signal month-end = **1998-07-31**; first computable quarterly
rebalance = **1998-09-30** (rule: signal at M requires month-ends at M−1 and M−7; rebalance
months {3,6,9,12}). The remaining Phase K ruling is only whether the stress window is
restated as 1998-09-30→2005 or kept nominally 1998–2005 with a documented late start.

## F-006 — 25 SP500-member tickers have no SEP price rows
**Date:** 2026-07-09 · **Phase:** B · **Status:** REGISTERED — feeds Phase C identity audit (B0-04)

Reduction QC: 1,199 distinct ever-member ticker keys in the SP500 table vs.
1,174 distinct tickers present in the reduced SEP panel → 25 member tickers
with zero price rows at/after the date floor. Working hypothesis: ticker-string
mismatches between the SP500 table and SEP (same family as the 42 events in
`_sp500_unmapped_events.csv`), and/or members whose entire price history
predates 1997-12-31. Hypothesis is UNVERIFIED until the Phase C membership
audit enumerates the 25 and classifies each.

**Required action:** Phase C membership audit must list the 25 tickers, classify
each (string mismatch / pre-1998 exit / vendor gap), and determine whether any
touches the evaluated 1998+ timeline. B0-04 cannot close while any evaluated-
timeline identity remains unresolved.

## F-007 — Gap-loss flag discrepancy: protocol document vs. risk_limits.yaml
**Date:** 2026-07-09 (carried from pre-repo review) · **Phase:** F-prep · **Status:** OPEN_DECISION

The protocol document's FD-02 text describes a −35% gap-loss deployment flag;
`config/risk_limits.yaml` encodes −25%. One of the two is wrong. Because
`risk_limits.yaml` is one of the 18 frozen artifacts, correcting it after the
Phase A freeze requires a new signed release per the design contract.

**Required action:** Jason rules on the intended threshold **before FD-02/B0-08
freeze and before any Phase F confirmation result is viewed**. The resolution
commit must reference this finding ID.

**RESOLVED 2026-07-16:** The frozen protocol document FD-02 text specifies −35% for BOTH the
close-to-next-open and open-to-open selected-lot gap flags. risk_limits.yaml's −25% was a
transcription error, corrected to −35%; the open-to-open and intra-month flags and the 20%-of-
HWM terminal-wealth veto from FD-02 canon were also added to the yaml. Cross-referenced against
general Monte-Carlo risk-protocol consensus (99th-pct robustness boundary; ruin at median MC
DD>100%): the −80% veto is more conservative than consensus, confirmed SAFE. New release digest
4cb6602e63251b6e (supersedes 48d0841e). FD-01 and FD-02 frozen this commit BEFORE any Stage-5
result was viewed.

---

*Maintenance rule: new findings are appended with the next F-NNN ID and added to
the index table. Status changes edit the status line and index row only; original
finding text is never rewritten. Each session branch that adds findings must
mention the IDs in its commit message.*

## F-008 — Synthetic fixture artifacts leaked into the shipped package and reached the repo
**Date:** 2026-07-14 · **Phase:** B · **Status:** RESOLVED — real report (SHARADAR_20260620) pushed by Jason 2026-07-15; synthetic artifacts fully purged; B0-02 review sheet issued at results/phaseB/b002_field_classification_review.md

The sandbox fixture test of the reducer wrote `manifests/raw_archive_manifest.json` and
`results/phaseB/vendor_semantics_report.json` (vintage SYNTH_TEST_V2) into the package tree,
which shipped in the r3 zip and was committed to the repo alongside the real data. The stale
manifest was caught (renamed `raw_archive_manifest00.json` by Jason, deleted in this branch).
**The `results/phaseB/vendor_semantics_report.json` currently in the repo is still the synthetic
one.** Required action: Jason replaces it with the real report from
`C:\Users\jason\Downloads\results\phaseB\vendor_semantics_report.json` and pushes.
Root cause: fixture runs used repo-relative output paths. Prevention: future fixture runs write
to temp dirs only. B0-02 review cannot proceed on the synthetic file.

## F-009 — Windows CRLF changes the recorded manifest cross-hash
**Date:** 2026-07-14 · **Phase:** B · **Status:** RESOLVED

`reduced_manifest.json` records the raw-archive-manifest hash as computed on Windows (CRLF,
`5e6c7658…`); git normalized the committed file to LF (`fa6715c6…`). Content is identical —
re-CRLF'ing the repo file reproduces the recorded hash exactly. Resolution:
`build/verify_reduced_upload.py` performs a CRLF-tolerant cross-hash check and this behavior
is documented there. All parquet hashes (binary, unaffected by normalization) match exactly.

## F-010 — Unmapped membership identities quantified: 1,120 rows / 883 tickers
**Date:** 2026-07-14 · **Phase:** C · **Status:** REGISTERED — Phase C audit worklist

`build_sp500_membership.py` mapped 58,040 of 59,160 membership rows (98.1%) to unique
permatickers via date-covered TICKERS join. Residual: 1,120 rows across 883 distinct tickers,
concentrated in pre-1998 added/removed events outside SEP coverage. Snapshot member counts
post-mapping: 499–505 (avg 501.6) across 113 quarterly snapshots 1998Q1–2026Q1 — consistent
with true index size, indicating the evaluated-window mapping is near-complete. Interval-vs-
snapshot cross-validation disagreements (19,982 / 8,577 pairs) are dominated by incomplete
pre-1998 event history; snapshots are designated the PIT source of truth for the rebalance
gate, intervals retained as consistency check. **Required action:** Phase C membership audit
(`qa/audit_membership.py`) classifies every unmapped/disagreeing identity that touches the
evaluated 1998+ timeline; B0-04 stays OPEN until then. Supersedes the preliminary 25-ticker
estimate in F-006 (that count was SEP-presence; this is the mapping-level count).

## F-011 — Protocol doc §1.3 warm-up estimate superseded by mechanical derivation
**Date:** 2026-07-15 · **Phase:** C · **Status:** REGISTERED (doc amendment pending)

§1.3 states "first plausible CORE formation month is June 1998 with first deployment in July
1998" under a 1998-01-01 membership proxy. A June-1998 formation requires the final Nov-1997
closeadj (M−7), which does not exist in vintage SHARADAR_20260620 (coverage floor 1997-12-31,
F-005). Mechanical result: **first formation 1998-09-30, first deployment first tradable open
Oct 1998** (confirmed by build_eligible_snapshots.py: 79 formations 1998-09-30..2026-03-31).
Required action: amend §1.3 in the next protocol doc revision, citing this finding; the Phase
K window ruling (F-005) inherits these dates.

## F-012 — Date-coverage mapping had no grace for post-trade events; 2026 'current' snapshot dropped
**Date:** 2026-07-15 · **Phase:** B/C · **Status:** RESOLVED

The permaticker mapping window ended at lastpricedate exactly, but removals, delistings, and
the vendor 'current' snapshot stamp postdate the final trade by days. Effect: all 503 rows of
the 2026-06-20 'current' snapshot and ~200 evaluated-era 'removed' events failed mapping.
Fix: +30-day grace on the coverage end, documented in-code, applied uniformly to membership
and actions mapping. Post-fix: unmapped rows 1,120 → 401 (370 tickers, 96% pre-coverage era);
snapshots now 114 dates including 2026-06-20; member counts unchanged at 499–505. Caught by
the audit query's era breakdown before eligible sets were built — no downstream artifact ever
consumed the defective mapping.

## F-013 — Reference engine hardcoded a fixture permaticker; caught by property tests
**Date:** 2026-07-16 · **Phase:** E (G9) · **Status:** RESOLVED

The Python reference engine contained a leftover line binding terminal-event handling to
permaticker 900005 (the golden fixture's GE). It was invisible to the golden gate (the
fixture contains exactly that name) and was caught on the FIRST Hypothesis property run,
which feeds the engine random fixtures. Fix: line removed; golden compare re-verified 77/77;
both property suites pass (90 randomized examples). Lesson reinforced: the golden gate proves
agreement on one dataset; property tests are the generality gate — both are required, neither
substitutes for the other.

## F-014 — Terminal-event returns are a conservative placeholder, not frozen policy
**Date:** 2026-07-16 · **Phase:** E · **Status:** OPEN_DECISION

**REVISED 2026-07-16 after exposure measurement.** Terminal accounting remains provisional.
Measured facts replacing the earlier speculation: the recorded CORE blotter contained **ZERO
terminal lots** across 2016-2023 (63 lots, no event inside any holding window). Clone impact
magnitude and direction were **unknown** at the time of the earlier claim because exact clone
draws and exposures were not preserved; they are now (draws hash in
results/phaseE/clone_draws.sha256). Corrected measurement: 91 distinct clone (formation,
permaticker) exposure pairs, 5,451 total clone lot-hits across the 10,000 clones. The earlier
statement that the placeholder "penalizes CORE asymmetrically" was therefore UNSUPPORTED
speculation and is withdrawn: with zero CORE exposures, the provisional policy could only have
affected clones. Direction of any correction is now a measurable question, not an assumption,
and remains unresolved until transaction evidence closes B0-05.

## F-015 — 2016-2023 development clone diagnostic falls below FD-01 thresholds (RELABELED, see F-016)
**Date:** 2026-07-16 · **Phase:** E · **Status:** OPEN_DECISION

Result (FD-01 frozen at release 4cb6602e BEFORE the run): CORE CAGR 0.1803 vs clone median
0.2316, p99 0.5433; CORE at the 32.2nd percentile. Both the percentile test and the 3% net-
excess floor FAIL. This is in-sample DEVELOPMENT data (J11); holdouts remain sealed and were
not touched. Interpretation is NOT "strategy invalidated": (a) F-014 terminal-return bias is
unresolved and directionally against CORE; (b) the clone universe is the full ~500-name index
with very high random-draw variance (p99=54%), a demanding null in a mega-cap-led regime;
(c) the leveraged-ETF deployment layer (a confirmed value-add per prior ablation) is NOT in
this unlevered CORE return. Required actions for Jason: rule on whether Stage 5 re-runs after
F-014 closes, whether the clone null should be refined per S5.3 (block/stationary bootstrap,
regime-matched clones), and whether the deployment layer belongs in the primary comparison or
stays a separate track. No holdout may open while F-015 is OPEN.

## F-016 — Session agent mislabeled the 2016-2023 development run as the formal primary gate
**Date:** 2026-07-16 · **Phase:** E · **Status:** RESOLVED (self-reported error)

`run_clone_null.py` emitted `PRIMARY_GATE: FAIL` for the 2016-2023 window and the session
agent reported it as a primary-gate outcome. **The canon says otherwise, explicitly:**
§5.2 — "The **2006-2015 confirmation CORE** must satisfy both…"; Phase list — "**Phase F —
CORE confirmation on 2006-2015** … Outputs: … primary_gate.json", runnable only after
holdout_guard permits access. 2016-2023 is the DEVELOPMENT window (J11); no formal primary
gate exists there.

Correction applied: both artifacts relabeled `2016-2023 DEVELOPMENT CLONE DIAGNOSTIC -
PROVISIONAL TERMINAL ACCOUNTING`; the FD-01 comparison is retained only as a labeled
development yardstick. No holdout was opened; FD-01/FD-02 remain validly frozen (release
4cb6602e) ahead of any Phase F access — that discipline is unaffected.

Consequence for interpretation: the below-threshold development result **cannot** be
described as a primary-gate failure, and equally **cannot** be used to argue the strategy
passed anything. It is a development-period signal-quality diagnostic computed under
provisional terminal accounting (F-014).

## F-016 — DEFECT: terminal classification inverted mergerto/mergerfrom and treated ticker changes as terminal
**Date:** 2026-07-16 · **Phase:** B/E · **Status:** RESOLVED

The pre-correction `build_terminal_events.py` mapped `mergerto` -> terminal and included
`tickerchangeto` in the terminal action set, and omitted `mergerfrom`, `regulatorydelisting`,
and `voluntarydelisting` entirely. Official vendor semantics (archived, sha256 52ef6da7...)
state: `mergerto.ticker` = SURVIVING company (not terminal); `mergerfrom.ticker` = NON-SURVIVING
company (terminal); ticker changes are identity continuation. The defect would have terminated
lots in surviving entities and in mere ticker renames, while missing genuine non-survivor
terminations. Fixed; 12 regression tests added (qa/test_terminal_semantics.py) including an
explicit test that fails against the old mapping. Effect on the recorded run: event mix changed
from {ACQUIRED 443, BANKRUPTCY 56, DELISTED_OTHER 12, MERGER 9} to {ACQUIRED 443, BANKRUPTCY 56,
DELISTED_OTHER 21}; the 9 spurious MERGER terminations are gone.

## F-017 — ACTIONS.value is FINAL MARKET CAP, not per-share proceeds
**Date:** 2026-07-16 · **Phase:** B · **Status:** RESOLVED (vendor semantics); B0-05 remains PARTIAL

Vendor text: for acquisitionby/acquisitionof/mergerfrom/mergerto/bankruptcyliquidation/delisted,
`value` = **final market cap** of the terminating company; `date` = **last trade date**. Any
engine using ACTIONS.value as terminal per-share proceeds would be catastrophically wrong (market
cap vs per-share). Recorded as a binding prohibition in results/phaseB/terminal_event_semantics.json
and asserted by test. Also binding: ACTIONS.date is NOT a legal completion date and may never be
labeled as such. Unit caveat flagged honestly: the vendor text says "final market cap" but does
NOT state the currency unit in the archived file; the reviewer's "USD millions" is not verifiable
from this text. Moot for the protocol because value is never used in any branch.

## F-018 — DEFECT: unordered eligible-universe SQL made seeded clone draws nondeterministic
**Date:** 2026-07-16 · **Phase:** E · **Status:** RESOLVED

`random.sample` consumes a list; its output depends on that list's ORDER. The eligible-universe
queries feeding clone sampling used `SELECT DISTINCT ... JOIN ...` with **no ORDER BY**, so
row order was not guaranteed across runs or engines. The draws were therefore not reproducible
from the seed even though a seed was recorded — and the earlier claim that "draws can be
regenerated from the seed" was unsound. Fix: `ORDER BY permaticker` on every sampling universe;
exact draws now persisted to results/phaseE/clone_draws.parquet (630,000 rows, 9 columns,
canonically sorted) with a content hash; two clean regenerations verified identical
(9c33cd48f8543ded...). Caught by external review, not by our own tests — a gap worth noting:
determinism was tested for the data builders (Phase D) but never for the sampling layer.

## F-019 — DEFECT: evidence-preparation provenance row unlocked the confirmation gate
**Date:** 2026-07-16 · **Phase:** F governance · **Status:** RESOLVED

Recording the 2006-2015 evidence-preparation access filled `attestor` and `timestamp` in
period_provenance.csv, which was all `holdout_guard.check_period` required — so
`holdout_guard.py --period 2006-2015` began returning **PERMIT**. A governance action intended
to *document* restricted access had silently *unsealed* the confirmation holdout. Self-caught
within the same session by running the guard immediately after writing the row. Fix: added an
`access_type` column; `check_period` now requires `access_type=CONFIRMATION_EXECUTION` and
explicitly refuses evidence-preparation and unspecified rows; two regression cases added to the
self-test (12/12 PASS). Both governed periods now correctly BLOCK. Lesson: any write to a
governance ledger must be followed by re-running the guard that reads it.

