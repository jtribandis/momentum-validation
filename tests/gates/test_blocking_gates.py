from pathlib import Path
import csv


def test_blockers_prevent_decision_grade_claims():
    rows = list(csv.DictReader(open('blocker_ledger.csv', newline='')))
    unresolved = [r['blocker_id'] for r in rows if r['status'] not in ('RESOLVED', 'DOWNGRADED', 'NOT_APPLICABLE')]
    assert not unresolved, 'Unresolved blockers remain: ' + ', '.join(unresolved) + '. Current allowed tier is limited by status_dashboard.md.'


def test_golden_fixture_is_not_only_smoke_before_phase_e():
    rows = Path('fixtures/golden_v1/expected/selected_names.csv').read_text().strip().splitlines()
    assert len(rows) > 1, 'golden_v1 expected selections are missing rows.'
    assert 'SMOKE_NOT_APPROVED' not in '\n'.join(rows), 'golden_v1 is still a smoke fixture; approve by two methods before Phase E.'


def test_source_claims_publication_ready_before_publication():
    rows = list(csv.DictReader(open('evidence/source_verification/source_claim_map.csv', newline='')))
    not_ready = [r['ref_id'] for r in rows if r['publication_ready_YN'].upper() != 'YES']
    assert not not_ready, 'Source claims not publication-ready: ' + ', '.join(not_ready)
