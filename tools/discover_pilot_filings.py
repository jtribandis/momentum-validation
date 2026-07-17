#!/usr/bin/env python3
"""List candidate SEC filings near each pilot event window from data.sec.gov
submissions metadata. Metadata only; evidence bytes are saved separately by
fetch_sec_transaction_evidence.fetch_source."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_sec_transaction_evidence import fetch_json

FORMS_OF_INTEREST = {"8-K", "8-K/A", "25", "25-NSE", "15-12B", "S-4", "DEFM14A",
                     "SC 14D9", "SC TO-T", "DEF 14A", "424B3"}


def submissions_all(cik: str):
    padded = cik.zfill(10)
    sub = fetch_json(f"https://data.sec.gov/submissions/CIK{padded}.json")
    batches = [sub["filings"]["recent"]]
    for extra in sub["filings"].get("files", []):
        batches.append(fetch_json(f"https://data.sec.gov/submissions/{extra['name']}"))
    name = sub.get("name", "?")
    rows = []
    for b in batches:
        n = len(b["accessionNumber"])
        for i in range(n):
            rows.append({
                "form": b["form"][i],
                "filingDate": b["filingDate"][i],
                "accession": b["accessionNumber"][i],
                "primaryDocument": b["primaryDocument"][i],
                "items": b.get("items", [""] * n)[i],
            })
    return name, rows


def main():
    cik, start, end = sys.argv[1], sys.argv[2], sys.argv[3]
    name, rows = submissions_all(cik)
    print(f"CIK {cik} — {name}: {len(rows)} total filings")
    hits = [r for r in rows
            if start <= r["filingDate"] <= end and r["form"] in FORMS_OF_INTEREST]
    for r in sorted(hits, key=lambda r: r["filingDate"]):
        print(f"  {r['filingDate']}  {r['form']:<9} {r['accession']}  items={r['items']}  doc={r['primaryDocument']}")


if __name__ == "__main__":
    main()
