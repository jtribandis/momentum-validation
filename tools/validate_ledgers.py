#!/usr/bin/env python3
"""Phase A: validate blocker/provenance/decision/task ledgers; emit results/phaseA/ledger_validation.json."""
import csv, json, sys, datetime
from pathlib import Path

EXPECTED = {
    'blocker_ledger.csv': ['blocker_id','description','affected_phase','affected_claim_tier','status','fix_instruction','evidence_file','fix_command_or_manual_step','residual_limitation_if_unresolved','downgrade_if_unresolved'],
    'protocol/period_provenance.csv': ['period','first_inspection_date','what_was_viewed','decision_made_after','project_source','code_commit','data_vintage_id','spent_YN','attestor','timestamp'],
    'protocol/research_decisions.csv': ['decision_id','date','variant_or_decision','reason','affected_periods','result_viewed_YN','evidence_file'],
    'protocol/open_tasks.csv': ['task_id','description','affected_phase','status','evidence_file'],
}
VALID_STATUS = {'OPEN','RESOLVED','DOWNGRADED','NOT_APPLICABLE'}
REQUIRED_PERIODS = {'2006-2015','2024-2026','1998-2005'}

def main() -> int:
    report = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'checks': []}
    ok = True
    for path, cols in EXPECTED.items():
        try:
            with open(path, newline='') as f:
                rdr = csv.DictReader(f)
                header = rdr.fieldnames or []
                rows = list(rdr)
            if header != cols:
                ok = False
                report['checks'].append({'file': path, 'result': 'FAIL', 'error': f'header mismatch: {header}'})
                continue
            entry = {'file': path, 'result': 'PASS', 'rows': len(rows)}
            if path == 'blocker_ledger.csv':
                bad = [r['blocker_id'] for r in rows if r['status'] not in VALID_STATUS]
                if bad:
                    ok = False; entry['result'] = 'FAIL'; entry['error'] = f'invalid status values: {bad}'
                entry['open_blockers'] = [r['blocker_id'] for r in rows if r['status'] == 'OPEN']
            if path == 'protocol/period_provenance.csv':
                periods = {r['period'] for r in rows}
                missing = REQUIRED_PERIODS - periods
                if missing:
                    ok = False; entry['result'] = 'FAIL'; entry['error'] = f'missing holdout rows: {sorted(missing)}'
                entry['unattested_periods'] = sorted(r['period'] for r in rows if not r['attestor'].strip())
            report['checks'].append(entry)
        except FileNotFoundError:
            ok = False
            report['checks'].append({'file': path, 'result': 'FAIL', 'error': 'missing file'})
    report['overall'] = 'PASS' if ok else 'FAIL'
    Path('results/phaseA').mkdir(parents=True, exist_ok=True)
    Path('results/phaseA/ledger_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(('PASS' if ok else 'FAIL') + ' ledger validation; report at results/phaseA/ledger_validation.json')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
