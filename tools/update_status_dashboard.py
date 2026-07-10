#!/usr/bin/env python3
import csv
from pathlib import Path

rows = list(csv.DictReader(open('blocker_ledger.csv', newline='')))
open_rows = [r for r in rows if r['status'] not in ('RESOLVED', 'DOWNGRADED', 'NOT_APPLICABLE')]

allowed = 'T3_DEPLOYMENT_FACING_EVIDENCE_PACKAGE'
if any(r['blocker_id'] in [f'B0-{i:02d}' for i in range(1, 9)] and r['status'] == 'OPEN' for r in rows):
    allowed = 'T0_EXECUTABLE_SCAFFOLD'
elif any(r['blocker_id'] in ['B0-10', 'B0-11'] and r['status'] == 'OPEN' for r in rows):
    allowed = 'T1_SELF_REVIEWED_CORE_IMPLEMENTATION'
elif any(r['blocker_id'] == 'B0-09' and r['status'] == 'OPEN' for r in rows):
    allowed = 'T1_SELF_REVIEWED_CORE_IMPLEMENTATION_CORE_ONLY'

with open('status_dashboard.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['gate_id', 'status', 'claim_tier_allowed', 'fix_next', 'evidence_file'])
    for r in rows:
        status = 'PASS' if r['status'] in ('RESOLVED', 'DOWNGRADED', 'NOT_APPLICABLE') else 'OPEN'
        w.writerow([r['blocker_id'], status, allowed, r['fix_instruction'], r['evidence_file']])

lines = ['# Status dashboard', '', f'Current allowed claim tier: `{allowed}`', '', '## Next fixes', '']
for r in open_rows[:5]:
    lines.append(f"1. **{r['blocker_id']} - {r['description']}**: {r['fix_instruction']} Evidence: `{r['evidence_file']}`. If unresolved, downgrade to `{r['downgrade_if_unresolved']}`.")
if not open_rows:
    lines.append('No unresolved blockers.')
lines += [
    '', '## Full gate table', '',
    '| Gate | Status | Phase | Claim tier affected | Fix | Evidence | Downgrade if unresolved |',
    '|---|---:|---|---|---|---|---|'
]
for r in rows:
    lines.append(f"| {r['blocker_id']} - {r['description']} | {r['status']} | {r['affected_phase']} | {r['affected_claim_tier']} | {r['fix_instruction']} | {r['evidence_file']} | {r['downgrade_if_unresolved']} |")
Path('status_dashboard.md').write_text('\n'.join(lines) + '\n')
print(f'Wrote status_dashboard.md and status_dashboard.csv; allowed claim tier: {allowed}')
