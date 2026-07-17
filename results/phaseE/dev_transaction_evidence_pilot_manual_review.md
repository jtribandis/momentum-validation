# Ten-Event Pilot - Manual Review Record

Reviewer: AI transcription (Claude) - owner attestation pending
Timestamp: 2026-07-17T16:09:10+00:00

## 1. EV-a42cca6e6f5c3c76 - SBNY (SIGNATURE BANK CORP)

- Queue row content_hash: 7b35428ea842e193
- Expected classification (queue): BANKRUPTCY_LIQUIDATION / P1_ZERO_RECOVERY_CLAIM
- Evidence classification: BANK_FAILURE_FDIC_RECEIVERSHIP
- Primary source: FDIC_FAILED_BANK_PAGE NOT_APPLICABLE
- Filing item/section: FDIC failed-bank resolution page (Signature Bank, closed 2023-03-12)
- Transcribed terms: REQUIRES_OWNER_REVIEW
- Cash/share: NOT_APPLICABLE; successor shares/share: NOT_APPLICABLE
- Sharadar comparison: SHARADAR_BANKRUPTCY_LIQUIDATION_RECLASSIFIED_AS_FDIC_RECEIVERSHIP
- Candidate branch: REQUIRES_OWNER_REVIEW
- Pass/fail: PASS_WITH_OWNER_REVIEW
- Notes: Signature Bank was FDIC-insured and reported under Exchange Act s.12(i) to the FDIC, not the SEC (CIK 1288784 holds only third-party 13D/G filings). FDIC page: closed by NYDFS 2023-03-12, FDIC receiver, deposits and substantially all assets to Signature Bridge Bank N.A. No primary statement of common-equity recovery found; zero recovery NOT confirmed - P1 claim remains unverified. REQUIRES_OWNER_REVIEW.

## 2. EV-efb5e4fee43d06e5 - SIVBQ (SVB FINANCIAL GROUP)

- Queue row content_hash: bac3cd27be3faca5
- Expected classification (queue): BANKRUPTCY_LIQUIDATION / P1_ZERO_RECOVERY_CLAIM
- Evidence classification: BANKRUPTCY_CHAPTER_11
- Primary source: 8-K 0001193125-23-073665
- Filing item/section: Item 1.03 (Ch.11 petition 2023-03-17, Case 23-10367 SDNY)
- Transcribed terms: verified_bankruptcy_zero_recovery
- Cash/share: NOT_APPLICABLE; successor shares/share: NOT_APPLICABLE
- Sharadar comparison: SHARADAR_VALUE_23_7_NOT_A_RECOVERY_FIGURE
- Candidate branch: verified_bankruptcy_zero_recovery
- Pass/fail: PASS
- Notes: Affirmative zero-recovery evidence, plan-effectiveness 8-K: 'No holders of Common Equity Interests or 510(b) Claims received any distributions ... All Common Equity Interests ... were canceled on the Effective Date' (2024-11-07). Common traded OTC as SIVBQ between NASDAQ delisting (Form 25 2023-05-02) and cancellation - owner judgment needed on strategy exit timing vs zero terminal value convention.

## 3. EV-bbf5f41350ffa266 - CCE1 (COCA-COLA ENTERPRISES INC)

- Queue row content_hash: bc75f3cf3689f22e
- Expected classification (queue): DELISTED_OTHER / P3_DELISTING_TERMS
- Evidence classification: MIXED_CASH_STOCK_ACQUISITION
- Primary source: 8-K 0001193125-16-610069
- Filing item/section: Item 2.01 (Effective Time 12:30 AM EDT 2016-05-28)
- Transcribed terms: CONVERTED_TO_ONE_CCEP_SHARE_PLUS_14_50_CASH
- Cash/share: 14.50; successor shares/share: 1.0
- Sharadar comparison: SHARADAR_DELISTED_RECLASSIFIED_AS_MIXED_ACQUISITION
- Candidate branch: mixed_acquisition
- Pass/fail: PASS
- Notes: Each CCE share converted into one Coca-Cola European Partners plc share plus $14.50 cash. Filing internally states the Merger Agreement is 'dated as of August 6, 2016' - AFTER the 2016-05-28 completion; transcribed verbatim and flagged as an internal inconsistency in the primary document (agreement year likely 2015; not corrected here).

## 4. EV-a07ce31608a09185 - FTI1 (FMC TECHNOLOGIES INC)

- Queue row content_hash: fee80694da6e9511
- Expected classification (queue): DELISTED_OTHER / P3_DELISTING_TERMS
- Evidence classification: STOCK_ACQUISITION
- Primary source: 8-K 0001193125-17-010427
- Filing item/section: Item 2.01
- Transcribed terms: EXCHANGED_ONE_FOR_ONE_INTO_TECHNIPFMC_ORDINARY_SHARES
- Cash/share: NOT_APPLICABLE; successor shares/share: 1.0
- Sharadar comparison: SHARADAR_DELISTED_RECLASSIFIED_AS_STOCK_ACQUISITION
- Candidate branch: stock_acquisition
- Pass/fail: PASS
- Notes: Each FMCTI share automatically exchanged for one TechnipFMC Ordinary Share; each Technip ordinary share exchanged for two. Earliest event 2017-01-16 per cover page.

## 5. EV-833e074c17a3eeb2 - TFCFA (TWENTY-FIRST CENTURY FOX INC)

- Queue row content_hash: c77fec0736e956f5
- Expected classification (queue): DELISTED_OTHER / P3_DELISTING_TERMS
- Evidence classification: MIXED_ELECTION_ACQUISITION_WITH_SPINOFF
- Primary source: 8-K 0000950157-19-000308
- Filing item/section: Items 1.01, 1.02, 2.01, 3.01, 3.03 (Merger Effective Date 2019-03-20)
- Transcribed terms: FOX_SPINOFF_SHARES_PLUS_ELECTED_PRORATED_MIX_OF_51_572626_CASH_OR_0_4517_DIS
- Cash/share: 51.572626; successor shares/share: 0.4517
- Sharadar comparison: SHARADAR_DELISTED_RECLASSIFIED_AS_MIXED_ELECTION_ACQUISITION
- Candidate branch: mixed_acquisition
- Pass/fail: PASS_WITH_OWNER_REVIEW
- Notes: Terms fully transcribed, but the per-holder outcome depends on election and proration allocation (announced post-closing) plus the FOX Distribution; a passive-holder default rule is an owner policy decision. REQUIRES_OWNER_REVIEW for terminal-value convention.

## 6. EV-601b44ecacfcae66 - DISCK (WARNER BROS DISCOVERY INC)

- Queue row content_hash: 6bea7def50999402
- Expected classification (queue): DELISTED_OTHER / P3_DELISTING_TERMS
- Evidence classification: STOCK_RECLASSIFICATION_MERGER
- Primary source: 8-K 0001193125-22-103051
- Filing item/section: Item 2.01 + Exhibit 3.1 (Restated Charter, Series C Common Reclassification)
- Transcribed terms: SERIES_C_RECLASSIFIED_ONE_FOR_ONE_INTO_WBD_COMMON
- Cash/share: NOT_APPLICABLE; successor shares/share: 1.0
- Sharadar comparison: SHARADAR_DELISTED_RECLASSIFIED_AS_ONE_FOR_ONE_RECLASSIFICATION
- Candidate branch: stock_acquisition
- Pass/fail: PASS
- Notes: Charter Exhibit 3.1: Series A, B and C common each reclassified into one (1) share of WBD common stock at Effective Time; Closing Date 2022-04-08. Same legal registrant/CIK continued - owner to choose stock_acquisition vs identity_continuation branch mapping.

## 7. EV-130c8b20c0203051 - FRCB (FIRST REPUBLIC BANK)

- Queue row content_hash: 453a090d80685796
- Expected classification (queue): DELISTED_OTHER / P3_DELISTING_TERMS
- Evidence classification: BANK_FAILURE_FDIC_RECEIVERSHIP
- Primary source: FDIC_FAILED_BANK_PAGE NOT_APPLICABLE
- Filing item/section: FDIC failed-bank resolution page (First Republic Bank, closed 2023-05-01)
- Transcribed terms: REQUIRES_OWNER_REVIEW
- Cash/share: NOT_APPLICABLE; successor shares/share: NOT_APPLICABLE
- Sharadar comparison: SHARADAR_DELISTED_RECLASSIFIED_AS_FDIC_RECEIVERSHIP
- Candidate branch: REQUIRES_OWNER_REVIEW
- Pass/fail: PASS_WITH_OWNER_REVIEW
- Notes: First Republic Bank reported under s.12(i) to the FDIC (CIK 1132979 holds only third-party 13G filings). FDIC page: closed by California DFPI 2023-05-01, FDIC receiver, JPMorgan Chase Bank N.A. acquired deposits and substantially all assets. No primary statement of common-equity recovery; not evidence of zero value per directive delisting rule. REQUIRES_OWNER_REVIEW.

## 8. EV-1d435e7cfe772a3d - NLSN (NIELSEN HOLDINGS PLC)

- Queue row content_hash: 790fef8a53a086df
- Expected classification (queue): ACQUIRED / P2_CONSIDERATION_UNKNOWN
- Evidence classification: CASH_ACQUISITION_SCHEME_OF_ARRANGEMENT
- Primary source: 8-K 0001193125-22-260583
- Filing item/section: Introductory Note + Items 2.01, 3.01
- Transcribed terms: ACQUIRED_FOR_28_00_CASH_PER_ORDINARY_SHARE_VIA_UK_SCHEME
- Cash/share: 28.00; successor shares/share: NOT_APPLICABLE
- Sharadar comparison: VENDOR_CONFLICT_RESOLVED_CONSIDERATION_UNAFFECTED
- Candidate branch: cash_acquisition
- Pass/fail: PASS
- Notes: Sharadar shows 3 same-date conflicting rows (contra BBU vs N/A); primary evidence: legal Purchaser is Neptune BidCo US Inc. for a consortium including Brookfield Business Partners L.P. and Evergreen/Elliott. All-cash $28.00 regardless of counterparty naming, so the vendor conflict does not affect accounting. Conflicting rows remain preserved verbatim in the accepted queue row.

## 9. EV-7cd9261757a99227 - CAM2 (CAMERON INTERNATIONAL CORP)

- Queue row content_hash: d04961733c24178b
- Expected classification (queue): ACQUIRED / P2_CONSIDERATION_UNKNOWN
- Evidence classification: MIXED_CASH_STOCK_ACQUISITION
- Primary source: 8-K 0001104659-16-109460
- Filing item/section: Item 2.01 / Item 3.03
- Transcribed terms: CONVERTED_TO_14_44_CASH_PLUS_0_716_SLB_SHARES
- Cash/share: 14.44; successor shares/share: 0.716
- Sharadar comparison: MATCH_SHARADAR_COUNTERPARTY_AND_DATE
- Candidate branch: mixed_acquisition
- Pass/fail: PASS
- Notes: 8-K Item 3.03: each Cameron share converted into $14.44 cash plus 0.716 Schlumberger shares; merger completed 2016-04-01 per filing. Sharadar value 12647.5 is aggregate scale, never per-share.

## 10. EV-efbc596e6618fd16 - ADT1 (ADT CORP)

- Queue row content_hash: 979982f13a3d99ba
- Expected classification (queue): ACQUIRED / P2_CONSIDERATION_UNKNOWN
- Evidence classification: CASH_ACQUISITION
- Primary source: 8-K 0001193125-16-582209
- Filing item/section: Item 2.01
- Transcribed terms: CANCELLED_FOR_42_00_CASH_PER_SHARE
- Cash/share: 42.00; successor shares/share: NOT_APPLICABLE
- Sharadar comparison: DATE_OFFSET_LAST_TRADE_2016_04_29_VS_COMPLETION_2016_05_02
- Candidate branch: cash_acquisition
- Pass/fail: PASS
- Notes: Each ADT share cancelled and converted into the right to receive $42.00 cash on Closing Date 2016-05-02. Sharadar contra APO consistent with Apollo-managed Parent (Prime Security Services Borrower, LLC).
