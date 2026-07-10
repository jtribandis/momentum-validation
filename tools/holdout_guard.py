#!/usr/bin/env python3
"""Holdout guard: refuse access to a governed period unless period_provenance.csv carries
a complete attestation row for it and the period is not already spent (spent_YN != 'Y'
blocks reruns only when combined with rerun governance; a spent period requires an
explicit new attestation row, which this guard does not create).

Usage:
  holdout_guard.py --self-test          # verify guard logic on in-memory fixtures
  holdout_guard.py --period 2006-2015   # gate a real run; exit 1 if blocked
"""
import csv, json, sys, datetime, io
from pathlib import Path

LEDGER = 'protocol/period_provenance.csv'
GOVERNED = {'2006-2015', '2024-2026', '1998-2005'}
REQUIRED_FIELDS = ['first_inspection_date','what_was_viewed','decision_made_after','data_vintage_id','attestor','timestamp']

def load_rows(text=None):
    if text is not None:
        return list(csv.DictReader(io.StringIO(text)))
    with open(LEDGER, newline='') as f:
        return list(csv.DictReader(f))

def check_period(period, rows):
    """Return (allowed: bool, reason: str)."""
    if period not in GOVERNED:
        return True, f'{period} is not a governed holdout period'
    matches = [r for r in rows if r['period'] == period]
    if not matches:
        return False, f'no provenance row for {period}'
    r = matches[-1]  # most recent attestation row wins
    missing = [k for k in REQUIRED_FIELDS if not (r.get(k) or '').strip()]
    if missing:
        return False, f'attestation incomplete for {period}: missing {missing}'
    if (r.get('spent_YN') or '').strip().upper() == 'Y':
        return False, f'{period} already SPENT; rerun requires new signed attestation row under rerun governance'
    return True, f'{period} attested by {r["attestor"]} on {r["timestamp"]}, vintage {r["data_vintage_id"]}'

def self_test():
    results = []
    def case(name, expect_allowed, period, rows_text):
        allowed, reason = check_period(period, load_rows(rows_text))
        passed = (allowed == expect_allowed)
        results.append({'case': name, 'expect_allowed': expect_allowed, 'got_allowed': allowed, 'reason': reason, 'result': 'PASS' if passed else 'FAIL'})
        return passed

    hdr = 'period,first_inspection_date,what_was_viewed,decision_made_after,project_source,code_commit,data_vintage_id,spent_YN,attestor,timestamp\n'
    ok = True
    ok &= case('empty attestation blocks', False, '2006-2015', hdr + '2006-2015,,,,,,,,,\n')
    ok &= case('missing row blocks', False, '2024-2026', hdr + '2006-2015,,,,,,,,,\n')
    ok &= case('complete attestation permits', True, '2006-2015',
               hdr + '2006-2015,2026-07-09,confirmation run,primary gate decision,repo,abc123,V20260709,N,Jason,2026-07-09T00:00:00Z\n')
    ok &= case('spent period blocks', False, '1998-2005',
               hdr + '1998-2005,2026-07-09,stress run,veto check,repo,abc123,V20260709,Y,Jason,2026-07-09T00:00:00Z\n')
    ok &= case('partial attestation blocks', False, '2024-2026',
               hdr + '2024-2026,2026-07-09,,,,abc123,V20260709,N,Jason,\n')
    ok &= case('non-governed period passes through', True, '2016-2023', hdr)

    # Also verify the live ledger currently blocks all governed periods (expected pre-Phase-F state)
    live = load_rows()
    for p in sorted(GOVERNED):
        allowed, reason = check_period(p, live)
        results.append({'case': f'live ledger {p}', 'got_allowed': allowed, 'reason': reason,
                        'result': 'INFO_BLOCKED_AS_EXPECTED' if not allowed else 'INFO_PERMITTED'})

    report = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'overall': 'PASS' if ok else 'FAIL', 'cases': results}
    Path('results/phaseA').mkdir(parents=True, exist_ok=True)
    Path('results/phaseA/holdout_guard_selftest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(('PASS' if ok else 'FAIL') + ' holdout guard self-test; report at results/phaseA/holdout_guard_selftest.json')
    return 0 if ok else 1

def main() -> int:
    args = sys.argv[1:]
    if args[:1] == ['--self-test']:
        return self_test()
    if args[:1] == ['--period'] and len(args) >= 2:
        allowed, reason = check_period(args[1], load_rows())
        print(('PERMIT: ' if allowed else 'BLOCK: ') + reason)
        return 0 if allowed else 1
    print(__doc__); return 2

if __name__ == '__main__':
    sys.exit(main())
