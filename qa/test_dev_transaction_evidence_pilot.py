"""Tests for the ten-event transaction-evidence pilot (DEV_TERMINAL_EVIDENCE_PILOT_V1)."""
import csv
import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results/phaseE"
EVD = REPO / "evidence/transactions"
QUEUE = RES / "dev_transaction_events.csv"
ACCEPTED_QUEUE_SHA = "51a97f53b213564f6f54e7f445f93c0fb4935f3c8b6eff71a2bc1e0ee69e9ec1"
ALLOWED_CODES = {"NOT_APPLICABLE", "NOT_FOUND", "NOT_DISCLOSED_IN_PRIMARY_EVIDENCE",
                 "AMBIGUOUS_PRIMARY_EVIDENCE", "CONFLICTING_PRIMARY_EVIDENCE",
                 "REQUIRES_OWNER_REVIEW"}
EXPECTED_FILL = ["EV-7cd9261757a99227", "EV-efbc596e6618fd16"]


def _selection():
    return list(csv.DictReader((RES / "dev_transaction_evidence_pilot_selection.csv").open(newline="")))


def _pilot():
    return list(csv.DictReader((RES / "dev_transaction_evidence_pilot.csv").open(newline="")))


def _queue():
    return {r["event_id"]: r for r in csv.DictReader(QUEUE.open(newline=""))}


def test_exactly_ten_events_selected():
    sel = _selection()
    assert len(sel) == 10
    assert len({r["event_id"] for r in sel}) == 10


def test_fill_events_are_prescribed_earliest_acquired():
    sel = _selection()
    fill = [r["event_id"] for r in sel if r["selection_reason"].startswith("RULE_D")]
    assert sorted(fill) == sorted(EXPECTED_FILL)
    q = _queue()
    chosen_other = {r["event_id"] for r in sel if not r["selection_reason"].startswith("RULE_D")}
    acquired = sorted((r for r in q.values() if r["event_type"] == "ACQUIRED"
                       and r["event_id"] not in chosen_other),
                      key=lambda r: (r["last_trade_date"], int(r["permaticker"]), r["event_id"]))
    assert [r["event_id"] for r in acquired[:2]] == EXPECTED_FILL


def test_no_phase_f_rows_selected_or_accessed():
    for r in _selection():
        assert "PHASEF" not in r["event_id"].upper()
    q = _queue()
    for r in _selection():
        assert "PHASEF" not in q[r["event_id"]]["evaluation_window"].upper()
    manifest = json.loads((RES / "dev_transaction_evidence_pilot_manifest.json").read_text())
    assert manifest["phaseF_accessed_YN"] == "N"


def test_every_event_id_resolves_to_accepted_queue():
    q = _queue()
    for r in _selection():
        assert r["event_id"] in q
    for r in _pilot():
        assert r["event_id"] in q


def test_accepted_queue_hash_unchanged():
    assert hashlib.sha256(QUEUE.read_bytes()).hexdigest() == ACCEPTED_QUEUE_SHA


def test_evidence_files_match_saved_sha256():
    dirs = list(EVD.iterdir())
    assert dirs, "no evidence directories"
    for d in dirs:
        manifest = (d / "sha256_manifest.txt").read_text().splitlines()
        assert manifest
        for line in manifest:
            digest, name = line.split("  ", 1)
            assert hashlib.sha256((d / name).read_bytes()).hexdigest() == digest, f"{d.name}/{name}"


def test_saved_sec_files_are_not_error_pages():
    for d in EVD.iterdir():
        for f in d.glob("*.html"):
            head = f.read_bytes()[:8192]
            assert b"Undeclared Automated Tool" not in head
            assert b"Request Rate Threshold Exceeded" not in head
        for h in d.glob("*_headers.txt"):
            status = [l for l in h.read_text().splitlines() if l.startswith("http_status:")]
            assert status and status[0].split(": ")[1] == "200", h


def test_repeat_retrieval_checks_recorded():
    seen = 0
    for d in EVD.iterdir():
        for rec in json.loads((d / "source_manifest.json").read_text()):
            assert rec["repeat_retrieval_verified_YN"] in {"Y", "N"}
            seen += 1
    assert seen == 12
    exc = list(csv.DictReader((RES / "dev_transaction_evidence_pilot_exceptions.csv").open(newline="")))
    mismatched = {r["event_id"] for r in exc if r["exception_type"] == "REPEAT_RETRIEVAL_MISMATCH"}
    assert mismatched == {"EV-a42cca6e6f5c3c76", "EV-130c8b20c0203051"}


def test_sharadar_value_never_used_as_per_share_consideration():
    q = _queue()
    for r in _pilot():
        raw = q[r["event_id"]]["raw_value"]
        cash = r["cash_per_target_share"]
        if raw and cash not in ALLOWED_CODES:
            assert cash != raw, f"{r['event_id']}: Sharadar value echoed as per-share cash"


def test_bankruptcy_zero_recovery_requires_affirmative_evidence():
    rows = {r["event_id"]: r for r in _pilot()}
    sivb = rows["EV-efb5e4fee43d06e5"]
    assert sivb["final_common_equity_outcome"] == "verified_bankruptcy_zero_recovery"
    text = (EVD / "EV-efb5e4fee43d06e5/additional_primary_source.html").read_text(errors="replace")
    assert "No holders of Common Equity Interests" in text
    assert "canceled on the Effective Date" in text
    sbny = rows["EV-a42cca6e6f5c3c76"]
    assert sbny["final_common_equity_outcome"] == "REQUIRES_OWNER_REVIEW"
    assert sbny["common_equity_recovery_per_share"] == "REQUIRES_OWNER_REVIEW"


def test_unknown_fields_use_allowed_codes_only():
    known_code_like = {"NOT_APPLICABLE", "NOT_FOUND"} | ALLOWED_CODES
    for r in _pilot():
        for k, v in r.items():
            assert v != "", f"{r['event_id']}.{k} is an unexplained blank"
            if v.isupper() and v.startswith(("NOT_", "UNKNOWN", "MISSING", "TBD")):
                assert v in known_code_like, f"{r['event_id']}.{k}={v} not an allowed code"


def test_conflicted_sharadar_rows_remain_preserved():
    q = _queue()
    row = q["EV-1d435e7cfe772a3d"]
    assert row["same_date_conflicting_rows"] == "YES"
    assert int(row["conflicting_row_count"]) == 3
    preserved = json.loads(row["conflicting_rows_preserved"])
    assert len(preserved) == 3
    pilot = {r["event_id"]: r for r in _pilot()}["EV-1d435e7cfe772a3d"]
    assert pilot["vendor_conflict_resolution"] == "RESOLVED_FROM_PRIMARY_EVIDENCE"


def test_exactly_one_evidence_summary_per_pilot_event():
    ids = {r["event_id"] for r in _selection()}
    dirs = {d.name for d in EVD.iterdir() if d.is_dir()}
    assert dirs == ids
    for d in ids:
        assert (EVD / d / "evidence_summary.json").exists()


def test_no_performance_bearing_file_created_or_modified():
    diff = subprocess.check_output(
        ["git", "diff", "--name-only", "f4225cb3b013da5cc509b1e7014aa11a946df5e4", "--"],
        cwd=REPO).decode().splitlines()
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO).decode().splitlines()
    touched = set(diff) | {l[3:] for l in status}
    forbidden = ("nav", "cagr", "returns", "drawdown", "clone_null", "alpha",
                 "performance", "phaseF")
    for path in touched:
        lp = path.lower()
        assert not any(t in lp for t in forbidden), f"performance-bearing path touched: {path}"


def test_terminal_policy_remains_unsigned_and_inactive():
    text = (REPO / "config/terminal_policy.yaml").read_text()
    assert "effective_before_rerun: false" in text
    assert "signature" not in text.lower()


def test_b0_05_remains_partial_open():
    ledger = (REPO / "blocker_ledger.csv").read_text()
    assert "B0-05" in ledger
    row = [l for l in ledger.splitlines() if l.startswith("B0-05")][0]
    assert "PARTIAL_OPEN" in row
