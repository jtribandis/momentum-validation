DEVELOPMENT TRANSACTION EVIDENCE — TEN-EVENT PILOT
DIRECTIVE VERSION: DEV_TERMINAL_EVIDENCE_PILOT_V1

BASELINE

Repository:
jtribandis/momentum-validation

Public repository status:
INTENTIONAL_AND_ACCEPTED

Accepted main merge commit:
f4225cb3b013da5cc509b1e7014aa11a946df5e4

Accepted queue code commit:
0c61781dec51e63b6d8c93376855e6221eb486bb

Accepted attestation commit:
af66eabdb726e39755143eed61ac566cf53b6f41

Accepted development queue:
results/phaseE/dev_transaction_events.csv

Accepted queue byte SHA-256:
51a97f53b213564f6f54e7f445f93c0fb4935f3c8b6eff71a2bc1e0ee69e9ec1

Accepted counts:
- 61 unique development events
- 91 development exposure pairs
- 0 CORE terminal-event exposures
- 105 Phase F possible events remain out of scope
- 176 Phase F possible exposure pairs remain out of scope

CURRENT GOVERNANCE STATUS

- B0-05 = PARTIAL_OPEN
- Sharadar ACTIONS semantics = RESOLVED
- transaction-specific consideration/recovery evidence = PENDING
- terminal_policy.yaml = UNSIGNED
- effective_before_rerun = false
- accounting engine = SCAFFOLD_NOT_CERTIFIED
- golden_v3 = UNSIGNED
- Phase F = BLOCKED
- permitted work = development-period evidence collection only

SEC ACCESS

SEC EDGAR byte-level access has been verified through:

- www.sec.gov
- data.sec.gov
- efts.sec.gov

Use direct SEC retrieval to disk with the working SEC-compliant User-Agent.

Do not use web_fetch text, AI summaries, search-result snippets, news reports,
Wikipedia, or transaction databases as final evidence.

The saved files must be the actual bytes returned by SEC or another identified
primary issuer/exchange source.

Do not fabricate or infer:

- accession numbers
- filing sections
- transaction consideration
- exchange ratios
- completion dates
- bankruptcy recoveries
- counterparties

PUBLIC REPOSITORY AND WRITE PATH

The repository being public is deliberate and is not a blocker.

Do not request, receive, print, store, or use a GitHub PAT.

Do not push from this environment.

Create a local branch:

session/2026-07-17-sec-evidence-pilot

At completion, create a local commit and produce a handoff package for Jason to
apply and push manually.

No credentials, cookies, authorization headers, environment variables, email
addresses used in the SEC User-Agent, or other secrets may appear in committed
files or the handoff package.

PRESERVE THIS DIRECTIVE

Before beginning retrieval, save this exact directive as:

protocol/prompt_packages/dev_transaction_evidence_pilot_v1.md

Record its SHA-256 in the pilot manifest.

The saved directive is a provenance artifact and must not be edited after
retrieval begins.

PRE-FLIGHT CHECKS

Before creating pilot outputs:

1. Confirm HEAD equals:
   f4225cb3b013da5cc509b1e7014aa11a946df5e4

2. Confirm the working tree is clean.

3. Confirm the accepted development queue byte hash exactly equals:
   51a97f53b213564f6f54e7f445f93c0fb4935f3c8b6eff71a2bc1e0ee69e9ec1

4. Confirm terminal_policy.yaml remains unsigned and:
   effective_before_rerun: false

5. Confirm B0-05 remains PARTIAL_OPEN.

6. Confirm no Phase F, selected-stress, forward-holdout, performance, NAV, CAGR,
   alpha, clone-percentile, or drawdown job is invoked.

Stop immediately if any pre-flight check fails.

PURPOSE

Validate the primary-source transaction-evidence workflow on ten difficult
development-period terminal events before processing the remaining 51 events.

This session may collect, preserve, transcribe, classify, and manually review
primary evidence.

This session may not:

- calculate terminal proceeds in the strategy
- alter the accounting engine
- change economic policy
- activate terminal_policy.yaml
- close B0-05
- regenerate queues
- rerun development performance
- access Phase F results

PILOT SELECTION — EXACTLY TEN EVENTS

Select from:

results/phaseE/dev_transaction_events.csv

Selection must be mechanical and completed before transaction evidence is read.

Include:

A. Every development event where:

manual_review_priority = P1_ZERO_RECOVERY_CLAIM

Expected count:
2

B. Every development event where:

manual_review_priority = P3_DELISTING_TERMS

Expected count:
5

C. The one development event where:

permaticker = 192873
last_trade_date = 2022-10-10
same_date_conflicting_rows = YES

Expected count:
1

D. Add the first TWO ACQUIRED events not already selected, sorted strictly by:

1. last_trade_date ascending
2. permaticker ascending
3. event_id ascending

Do not apply a subjective “straightforward” filter and do not inspect transaction
outcomes before selecting them.

Based on the accepted queue, the expected two fill events are:

- EV-7cd9261757a99227
  permaticker 197286
  CAM2 / Cameron International Corp
  last trade date 2016-04-01

- EV-efbc596e6618fd16
  permaticker 191948
  ADT1 / ADT Corp
  last trade date 2016-04-29

Hard-fail if the accepted queue and prescribed sort do not produce these two
events.

The final pilot must contain:

- exactly 10 rows
- exactly 10 unique event_ids
- no Phase F events
- no substitution of a difficult event with an easier event

Create and freeze:

results/phaseE/dev_transaction_evidence_pilot_selection.csv

Required columns:

pilot_sequence
event_id
permaticker
historical_ticker
company_name
cik
last_trade_date
event_type
manual_review_priority
same_date_conflicting_rows
selection_reason
queue_content_hash
queue_source_commit
directive_sha256
selection_content_hash

PRIMARY-EVIDENCE HIERARCHY

Use primary evidence in this order:

1. SEC Form 8-K reporting transaction completion, normally Item 2.01 or Item 8.01
2. Definitive merger, acquisition, or reorganization agreement and amendments
3. DEFM14A, S-4, Schedule TO, Schedule 14D-9, or equivalent tender materials
4. Bankruptcy Form 8-K Item 1.03 and confirmed plan or liquidation documents
5. Exchange delisting notice or issuer filing explaining the delisting
6. Issuer or acquirer completion announcement when SEC evidence is unavailable
   or incomplete

An issuer announcement may supplement SEC evidence but may not silently override
a conflicting SEC document.

RETRIEVAL CONTROLS

Create a retrieval tool or script under:

tools/fetch_sec_transaction_evidence.py

The retrieval process must:

- require an SEC-compliant User-Agent supplied through the environment;
- refuse to run when that User-Agent is absent;
- not write the actual User-Agent value into committed artifacts;
- use conservative request pacing and retry logic;
- save original response bytes without transcription;
- save response headers separately;
- record source URL, retrieval timestamp, HTTP status, content type, accession
  number, local path, byte count, and SHA-256;
- refuse to label an HTTP error page as a filing;
- refuse to overwrite a previously saved source;
- verify repeat retrieval byte identity when the same URL is fetched twice;
- identify any non-identical repeat response as a provenance exception.

Do not save only browser-rendered text when the original filing or exhibit is
available.

EVENT-BY-EVENT REQUIRED FIELDS

Create one evidence summary per unique event containing:

event_id
permaticker
historical_ticker
company_name
cik
event_class

sharadar_action
sharadar_action_date
sharadar_value
sharadar_contraticker
sharadar_contraname
sharadar_conflict_flag
sharadar_conflicting_rows_preserved

announcement_date
definitive_agreement_date
shareholder_approval_date
legal_completion_date
last_trade_date
delisting_date
effective_cancellation_date

consideration_type
cash_per_target_share
successor_shares_per_target_share
successor_legal_name
successor_ticker
successor_cik
successor_permaticker

fractional_share_treatment
election_terms
proration_terms
contingent_value_right
other_security_or_rights

common_stock_cancelled_YN
common_equity_recovery_per_share
continued_OTC_trading_YN
final_common_equity_outcome

terminal_policy_candidate_branch
terminal_value_inputs_complete_YN
owner_judgment_required_YN

primary_filing_type
SEC_accession_number
filing_item_or_section
source_url
source_filename
source_sha256

additional_source_type
additional_source_accession
additional_source_section
additional_source_url
additional_source_filename
additional_source_sha256

review_status
reviewer
review_date
discrepancy_classification
notes

ALLOWED UNKNOWN AND MISSING CODES

Do not use speculative values or unexplained blanks.

Use only:

NOT_APPLICABLE
NOT_FOUND
NOT_DISCLOSED_IN_PRIMARY_EVIDENCE
AMBIGUOUS_PRIMARY_EVIDENCE
CONFLICTING_PRIMARY_EVIDENCE
REQUIRES_OWNER_REVIEW

EVENT-TYPE RULES

CASH ACQUISITION

Establish:

- exact cash consideration per target common share
- legal completion date
- relevant election or proration provisions
- contingent consideration
- treatment of common shares at completion

Candidate branch:

cash_acquisition

Never interpret Sharadar ACTIONS.value as cash per share.

STOCK ACQUISITION OR MERGER

Establish:

- successor shares received per target common share
- successor legal entity
- successor security identity
- legal completion date
- fractional-share treatment
- any cash component
- any temporary trading delay

Candidate branch:

stock_acquisition

MIXED CASH-AND-STOCK ACQUISITION

Record separately:

- cash per target share
- successor shares per target share
- election alternatives
- proration
- contingent-value rights
- fractional-share cash treatment

Candidate branch:

mixed_acquisition

BANKRUPTCY OR LIQUIDATION

Do not infer zero recovery merely from a bankruptcy filing or delisting.

Require affirmative primary evidence for:

- cancellation of existing common stock
- common-equity recovery, including zero recovery
- plan effective date or liquidation date
- continued OTC trading
- surviving warrants, trusts, claims, litigation rights, or contingent interests

Use:

verified_bankruptcy_zero_recovery

only when zero common-equity recovery is explicitly supported.

Otherwise use:

REQUIRES_OWNER_REVIEW

DELISTING

Determine whether the event was:

- acquisition
- merger or reorganization
- exchange migration
- ticker continuation
- OTC continuation
- voluntary going-private transaction
- regulatory delisting
- bankruptcy
- liquidation
- actual worthlessness
- unresolved terminal event

A missing exchange quote, delisted flag, or missing price is not evidence of zero
value.

CONFLICTED SHARADAR EVENT

For:

permaticker = 192873
last_trade_date = 2022-10-10

Preserve every conflicting Sharadar row verbatim.

Do not assume that BBU or N/A is the correct counterparty.

Resolve from primary evidence:

- legal acquirer or counterparty
- transaction type
- consideration
- legal completion date
- whether the vendor conflict affects accounting

Add:

vendor_conflict_resolution

Allowed values:

RESOLVED_FROM_PRIMARY_EVIDENCE
CONFLICT_DOES_NOT_AFFECT_ACCOUNTING
CONFLICT_AFFECTS_ACCOUNTING_REQUIRES_OWNER_REVIEW
UNRESOLVED

EVIDENCE DIRECTORY STRUCTURE

For each event create:

evidence/transactions/<event_id>/
    evidence_summary.json
    source_manifest.json
    primary_filing.html
    primary_filing_headers.txt
    primary_transaction_exhibit.html
    primary_transaction_exhibit_headers.txt
    additional_primary_source.html
    additional_primary_source_headers.txt
    sha256_manifest.txt
    reviewer_notes.md

Create only the source files actually needed.

Do not create empty fake filing files.

When a source is unavailable, record the missing-source status in the source
manifest and exceptions output.

SOURCE-MANIFEST FIELDS

For every saved source record:

source_role
source_type
issuer_or_filer
cik
SEC_accession_number
filing_date
retrieval_date_utc
source_url
local_filename
byte_count
byte_sha256
content_type
http_status
supporting_fields
authoritative_YN
repeat_retrieval_verified_YN
notes

PILOT OUTPUTS

Create:

results/phaseE/dev_transaction_evidence_pilot_selection.csv
results/phaseE/dev_transaction_evidence_pilot.csv
results/phaseE/dev_transaction_evidence_pilot_report.json
results/phaseE/dev_transaction_evidence_pilot_exceptions.csv
results/phaseE/dev_transaction_evidence_pilot_manifest.json
results/phaseE/dev_transaction_evidence_pilot_manual_review.md

The pilot manifest must include:

schema_version
directive_path
directive_sha256
source_queue_path
source_queue_byte_sha256
source_queue_code_commit
pilot_selection_hash
retrieval_script_path
retrieval_script_sha256
code_commit
working_tree_dirty_YN
environment_digest
retrieval_start_utc
retrieval_end_utc
event_count
source_count
output_paths
output_row_counts
output_byte_sha256
output_logical_content_sha256
returns_computed_YN
phaseF_accessed_YN
performance_files_modified_YN

PILOT REPORT

Report:

events_selected
events_attempted
events_fully_resolved
events_partially_resolved
events_unresolved

cash_acquisitions
stock_acquisitions
mixed_acquisitions
bankruptcies
delistings

zero_recovery_claims_confirmed
zero_recovery_claims_not_confirmed
delistings_reclassified_as_acquisitions
delistings_reclassified_as_other_events

vendor_conflicts_encountered
vendor_conflicts_resolved
vendor_conflicts_remaining

events_with_complete_terminal_value_inputs
events_requiring_owner_review
missing_primary_filings
ambiguous_primary_evidence
conflicting_primary_evidence

primary_source_files_saved
source_hashes_verified
repeat_retrieval_checks_passed
evidence_directories_complete
schema_validation_status
manual_review_status

MANUAL REVIEW

For each of the ten events, record:

- accepted queue row
- event_id
- expected event classification
- primary source
- exact filing item, exhibit section, or plan section
- independently transcribed transaction terms
- comparison against Sharadar
- discrepancy classification
- candidate terminal-policy branch
- pass/fail
- reviewer
- timestamp

Do not replace an unresolved event with another event.

TESTS

Add tests proving:

- exactly ten accepted development events were selected;
- the two fill events are the prescribed earliest two ACQUIRED events;
- no Phase F row or result was accessed;
- every event_id resolves to the accepted queue;
- the accepted queue byte hash remains unchanged;
- evidence files match saved SHA-256 values;
- saved SEC files are not HTTP error pages;
- repeat retrieval checks are recorded;
- Sharadar M&A value is never interpreted as per-share consideration;
- bankruptcy zero recovery requires affirmative primary evidence;
- unknown fields use the allowed codes;
- conflicted Sharadar rows remain preserved;
- exactly one evidence summary exists per pilot event;
- no performance-bearing file was created or modified;
- terminal_policy.yaml remains unsigned and inactive;
- B0-05 remains PARTIAL_OPEN.

LOCAL COMMIT AND HANDOFF

Do not push.

Commit only the pilot directive, retrieval tooling, evidence files, pilot outputs,
tests, and directly related documentation.

Use explicit file paths when staging. Do not use:

git add -A
git add .
git add --all

Create a local commit.

Then create:

handoff/dev_transaction_evidence_pilot.patch
handoff/dev_transaction_evidence_pilot.bundle
handoff/dev_transaction_evidence_pilot_manifest.json
handoff/sha256_manifest.txt

The patch must contain the complete binary-safe diff from:

f4225cb3b013da5cc509b1e7014aa11a946df5e4

to the local pilot commit.

The Git bundle must contain the local pilot branch and its required history.

The handoff manifest must record:

baseline_commit
pilot_commit
branch_name
patch_path
patch_sha256
bundle_path
bundle_sha256
included_file_paths
included_file_sha256
excluded_secret_patterns_checked_YN
credentials_included_YN
recommended_apply_commands

Assert:

credentials_included_YN = N

Do not include:

- .git/config
- environment files
- shell history
- GitHub tokens
- SEC User-Agent email
- authorization headers
- cookies
- credentials
- unrelated repository files

STOP CONDITIONS

Stop immediately and report if:

- a primary filing cannot be obtained;
- SEC returns inconsistent bytes for the same immutable filing URL;
- primary evidence conflicts materially;
- transaction consideration remains indeterminable;
- an event requires a previously undefined economic-policy branch;
- an accepted queue defect is found;
- a Phase F result or selection is accessed;
- a performance, NAV, CAGR, alpha, drawdown, or clone-null computation is
  triggered;
- the accepted queue or frozen artifact hash changes.

Do not:

- process the remaining 51 development events;
- process any Phase F event;
- implement terminal proceeds;
- modify the accounting engine;
- create or sign golden_v3;
- sign or activate terminal_policy.yaml;
- close B0-05;
- rerun development strategy or clones;
- run confirmation, selected stress, or forward holdout.

STOP AND REPORT with:

- local pilot commit SHA;
- selected ten event IDs;
- event-by-event evidence status;
- consideration or recovery terms found;
- evidence paths and SHA-256 values;
- unresolved or conflicting fields;
- owner-review questions;
- tests run and exact outcomes;
- handoff patch path and hash;
- handoff bundle path and hash;
- explicit confirmation that no credentials were included;
- explicit confirmation that no performance or sealed-period result was run.
