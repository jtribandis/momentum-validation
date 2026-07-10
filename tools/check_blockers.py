#!/usr/bin/env python3
import csv
rows=list(csv.DictReader(open('blocker_ledger.csv', newline='')))
open_rows=[r for r in rows if r['status'] not in ('RESOLVED','DOWNGRADED','NOT_APPLICABLE')]
if open_rows:
    print('BLOCKED: unresolved blockers prevent higher claim tiers:')
    for r in open_rows:
        print(f"- {r['blocker_id']} {r['description']} | fix: {r['fix_instruction']} | evidence: {r['evidence_file']} | downgrade: {r['downgrade_if_unresolved']}")
    raise SystemExit(1)
print('PASS all blockers resolved/downgraded/not applicable')
