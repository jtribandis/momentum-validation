# Frozen design contract reference

This file is the implementation-facing reference derived from Sections 0-5 of the protocol manual. It must be frozen before Phase A exits.

Core economic specification:
- Universe: U.S. common stocks; PIT S&P 500 membership.
- Signal: trailing six-month total return with one-month skip: closeadj(M-1) / closeadj(M-7) - 1.
- Selection: top three eligible names each quarterly rebalance.
- Holding: six months; repeated selections create independent lots.
- Execution: first tradable openadj of M+1.
- Accounting: Track 1 time-weighted validation is the gate basis.
- Null: full-mechanical clone null shares the accounting engine; only selection operator differs.

Implementation rule: scripts must load this file hash into `protocol_release.json` and must not silently duplicate or mutate the economic rules.
