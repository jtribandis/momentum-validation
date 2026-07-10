#!/usr/bin/env python3
import csv
rows=list(csv.DictReader(open('evidence/source_verification/source_claim_map.csv', newline='')))
not_ready=[r for r in rows if r['publication_ready_YN'].upper()!='YES']
if not_ready:
    print('SOURCE CLAIMS NOT PUBLICATION-READY:')
    for r in not_ready:
        print(f"- {r['ref_id']}: {r['link_status']} | {r['unresolved_limitation']}")
    raise SystemExit(1)
print('PASS all source claims marked publication-ready')
