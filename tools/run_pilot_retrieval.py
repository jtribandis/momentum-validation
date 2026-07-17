#!/usr/bin/env python3
"""Drive primary-evidence retrieval for the ten pilot events.

Every SEC URL below was derived in-session from data.sec.gov submissions
metadata (accession numbers and primary documents as reported by SEC).
FDIC URLs were taken from FDIC's own failed-bank-list index page.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_sec_transaction_evidence import fetch_source

REPO = Path(__file__).resolve().parents[1]
EV = REPO / "evidence/transactions"


def sec_url(cik: str, accession: str, doc: str) -> str:
    return (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            f"{accession.replace('-', '')}/{doc}")


SOURCES = [
    # event_id, filename_stem, role, type, filer, cik, accession, filing_date, url
    ("EV-7cd9261757a99227", "primary_filing", "PRIMARY_COMPLETION_EVIDENCE",
     "SEC_8K_ITEM_2_01", "Cameron International Corp", "941548",
     "0001104659-16-109460", "2016-04-04",
     sec_url("941548", "0001104659-16-109460", "a16-6473_28k.htm")),
    ("EV-efbc596e6618fd16", "primary_filing", "PRIMARY_COMPLETION_EVIDENCE",
     "SEC_8K_ITEM_2_01", "ADT Corp", "1546640",
     "0001193125-16-582209", "2016-05-06",
     sec_url("1546640", "0001193125-16-582209", "d177489d8k.htm")),
    ("EV-bbf5f41350ffa266", "primary_filing", "PRIMARY_COMPLETION_EVIDENCE",
     "SEC_8K_ITEM_2_01", "Coca-Cola Enterprises Inc / Coca-Cola European Partners US LLC",
     "1491675", "0001193125-16-610069", "2016-06-01",
     sec_url("1491675", "0001193125-16-610069", "d201852d8k.htm")),
    ("EV-a07ce31608a09185", "primary_filing", "PRIMARY_COMPLETION_EVIDENCE",
     "SEC_8K_ITEM_2_01", "FMC Technologies Inc", "1135152",
     "0001193125-17-010427", "2017-01-17",
     sec_url("1135152", "0001193125-17-010427", "d326621d8k.htm")),
    ("EV-833e074c17a3eeb2", "primary_filing", "PRIMARY_COMPLETION_EVIDENCE",
     "SEC_8K_ITEM_2_01", "Twenty-First Century Fox Inc", "1308161",
     "0000950157-19-000308", "2019-03-20",
     sec_url("1308161", "0000950157-19-000308", "form8k.htm")),
    ("EV-601b44ecacfcae66", "primary_filing", "PRIMARY_COMPLETION_EVIDENCE",
     "SEC_8K_ITEM_2_01", "Warner Bros. Discovery Inc (fka Discovery Inc)", "1437107",
     "0001193125-22-103051", "2022-04-12",
     sec_url("1437107", "0001193125-22-103051", "d328161d8k.htm")),
    ("EV-1d435e7cfe772a3d", "primary_filing", "PRIMARY_COMPLETION_EVIDENCE",
     "SEC_8K_ITEM_2_01", "Nielsen Holdings plc", "1492633",
     "0001193125-22-260583", "2022-10-11",
     sec_url("1492633", "0001193125-22-260583", "d407513d8k.htm")),
    ("EV-efb5e4fee43d06e5", "primary_filing", "PRIMARY_BANKRUPTCY_EVIDENCE",
     "SEC_8K_ITEM_1_03", "SVB Financial Group", "719739",
     "0001193125-23-073665", "2023-03-17",
     sec_url("719739", "0001193125-23-073665", "d485308d8k.htm")),
    ("EV-efb5e4fee43d06e5", "additional_primary_source", "PLAN_EFFECTIVENESS_EVIDENCE",
     "SEC_8K_PLAN_EFFECTIVE", "SVB Financial Group", "719739",
     "0001193125-24-254186", "2024-11-08",
     sec_url("719739", "0001193125-24-254186", "d904756d8k.htm")),
    ("EV-a42cca6e6f5c3c76", "primary_filing", "PRIMARY_RESOLUTION_EVIDENCE",
     "FDIC_FAILED_BANK_PAGE", "FDIC (receiver for Signature Bank)", "NOT_APPLICABLE",
     "NOT_APPLICABLE", "NOT_APPLICABLE",
     "https://www.fdic.gov/resources/resolutions/bank-failures/failed-bank-list/signature-ny.html"),
    ("EV-130c8b20c0203051", "primary_filing", "PRIMARY_RESOLUTION_EVIDENCE",
     "FDIC_FAILED_BANK_PAGE", "FDIC (receiver for First Republic Bank)", "NOT_APPLICABLE",
     "NOT_APPLICABLE", "NOT_APPLICABLE",
     "https://www.fdic.gov/resources/resolutions/bank-failures/failed-bank-list/first-republic.html"),
]


def main() -> int:
    log = []
    for (event_id, stem, role, stype, filer, cik, accession, fdate, url) in SOURCES:
        dest = EV / event_id / f"{stem}.html"
        rec = fetch_source(url, dest, verify_repeat=True)
        rec.update({
            "event_id": event_id, "source_role": role, "source_type": stype,
            "issuer_or_filer": filer, "cik": cik,
            "SEC_accession_number": accession, "filing_date": fdate,
            "authoritative_YN": "Y",
        })
        log.append(rec)
        print(f"{event_id} {stem}: {rec['byte_count']}b sha={rec['byte_sha256'][:16]} "
              f"repeat={rec['repeat_retrieval_verified_YN']}")
    (REPO / "results/phaseE/_pilot_retrieval_log.json").write_text(
        json.dumps(log, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
