#!/usr/bin/env python3
"""Mechanical ten-event pilot selection per DEV_TERMINAL_EVIDENCE_PILOT_V1.

Rules (applied in order, no outcome inspection, no subjective filtering):
  A. every row with manual_review_priority == P1_ZERO_RECOVERY_CLAIM (expect 2)
  B. every row with manual_review_priority == P3_DELISTING_TERMS (expect 5)
  C. the row with permaticker == 192873, last_trade_date == 2022-10-10,
     same_date_conflicting_rows == YES (expect 1)
  D. first TWO ACQUIRED rows not already selected, sorted by
     (last_trade_date asc, permaticker asc, event_id asc)
Hard-fails if D does not yield EV-7cd9261757a99227 then EV-efbc596e6618fd16.
"""
import csv, hashlib, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
QUEUE = REPO / "results/phaseE/dev_transaction_events.csv"
DIRECTIVE = REPO / "protocol/prompt_packages/dev_transaction_evidence_pilot_v1.md"
OUT = REPO / "results/phaseE/dev_transaction_evidence_pilot_selection.csv"

EXPECTED_QUEUE_SHA = "51a97f53b213564f6f54e7f445f93c0fb4935f3c8b6eff71a2bc1e0ee69e9ec1"
EXPECTED_FILL = ["EV-7cd9261757a99227", "EV-efbc596e6618fd16"]
QUEUE_CODE_COMMIT = "0c61781dec51e63b6d8c93376855e6221eb486bb"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    queue_sha = sha256_file(QUEUE)
    if queue_sha != EXPECTED_QUEUE_SHA:
        print(f"HARD FAIL: queue hash {queue_sha} != accepted {EXPECTED_QUEUE_SHA}")
        return 1
    directive_sha = sha256_file(DIRECTIVE)

    rows = list(csv.DictReader(QUEUE.open(newline="")))
    if len(rows) != 61:
        print(f"HARD FAIL: expected 61 dev events, found {len(rows)}")
        return 1

    selected, reasons = [], {}

    a = [r for r in rows if r["manual_review_priority"] == "P1_ZERO_RECOVERY_CLAIM"]
    if len(a) != 2:
        print(f"HARD FAIL: rule A expected 2, found {len(a)}")
        return 1
    for r in a:
        selected.append(r); reasons[r["event_id"]] = "RULE_A_P1_ZERO_RECOVERY_CLAIM"

    b = [r for r in rows if r["manual_review_priority"] == "P3_DELISTING_TERMS"]
    if len(b) != 5:
        print(f"HARD FAIL: rule B expected 5, found {len(b)}")
        return 1
    for r in b:
        selected.append(r); reasons[r["event_id"]] = "RULE_B_P3_DELISTING_TERMS"

    c = [r for r in rows if r["permaticker"] == "192873"
         and r["last_trade_date"] == "2022-10-10"
         and r["same_date_conflicting_rows"] == "YES"]
    if len(c) != 1:
        print(f"HARD FAIL: rule C expected 1, found {len(c)}")
        return 1
    selected.append(c[0]); reasons[c[0]["event_id"]] = "RULE_C_CONFLICTED_SHARADAR_ROWS"

    chosen_ids = {r["event_id"] for r in selected}
    acquired = sorted(
        (r for r in rows if r["event_type"] == "ACQUIRED" and r["event_id"] not in chosen_ids),
        key=lambda r: (r["last_trade_date"], int(r["permaticker"]), r["event_id"]),
    )
    fill = acquired[:2]
    fill_ids = [r["event_id"] for r in fill]
    if fill_ids != EXPECTED_FILL:
        print(f"HARD FAIL: rule D produced {fill_ids}, directive prescribes {EXPECTED_FILL}")
        return 1
    for r in fill:
        selected.append(r); reasons[r["event_id"]] = "RULE_D_EARLIEST_UNSELECTED_ACQUIRED"

    ids = [r["event_id"] for r in selected]
    if len(ids) != 10 or len(set(ids)) != 10:
        print(f"HARD FAIL: expected 10 unique events, got {len(ids)} ({len(set(ids))} unique)")
        return 1
    if any(r["evaluation_window"].startswith("PHASEF") for r in selected):
        print("HARD FAIL: Phase F row selected")
        return 1

    cols = ["pilot_sequence", "event_id", "permaticker", "historical_ticker",
            "company_name", "cik", "last_trade_date", "event_type",
            "manual_review_priority", "same_date_conflicting_rows",
            "selection_reason", "queue_content_hash", "queue_source_commit",
            "directive_sha256", "selection_content_hash"]
    body_rows = []
    for i, r in enumerate(selected, 1):
        body_rows.append([str(i), r["event_id"], r["permaticker"],
                          r["historical_ticker"], r["company_name"], r["cik"],
                          r["last_trade_date"], r["event_type"],
                          r["manual_review_priority"], r["same_date_conflicting_rows"],
                          reasons[r["event_id"]], queue_sha, QUEUE_CODE_COMMIT,
                          directive_sha, ""])
    logical = "\n".join("|".join(row[:-1]) for row in body_rows)
    sel_hash = hashlib.sha256(logical.encode()).hexdigest()
    for row in body_rows:
        row[-1] = sel_hash

    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(body_rows)

    print(f"OK: 10 events selected; selection_content_hash={sel_hash}")
    for row in body_rows:
        print(f"  {row[0]:>2}. {row[1]}  {row[3]:<6} {row[4][:40]:<40} {row[6]}  {row[10]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
