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

# Evidence-preparation mode (added 2026-07-16 per external review item 3).
# Permits ONLY corporate-action evidence preparation on a governed period. It does NOT spend
# the period and must never be reinterpreted as clean confirmation execution.
EVIDENCE_PREP_ALLOWED = {'formation_dates', 'eligible_identities', 'lot_calendar_windows', 'terminal_event_identities'}
EVIDENCE_PREP_FORBIDDEN = {'signals', 'ranks', 'core_selections', 'clone_performance', 'nav', 'returns',
                           'aggregate_performance', 'lot_pnl', 'cagr'}

def check_evidence_prep(period, requested_artifacts):
    """Return (allowed, reason). Rejects any request touching a forbidden artifact class."""
    bad = sorted(set(requested_artifacts) & EVIDENCE_PREP_FORBIDDEN)
    if bad:
        return False, f'EVIDENCE_PREP_REFUSED for {period}: forbidden artifacts requested {bad}'
    unknown = sorted(set(requested_artifacts) - EVIDENCE_PREP_ALLOWED)
    if unknown:
        return False, f'EVIDENCE_PREP_REFUSED for {period}: unrecognized artifacts {unknown} (allowlist only)'
    return True, (f'EVIDENCE_PREP_PERMITTED for {period}: {sorted(requested_artifacts)}. '
                  'Period NOT spent; this is not confirmation execution.')
REQUIRED_FIELDS = ['first_inspection_date','what_was_viewed','decision_made_after','data_vintage_id','attestor','timestamp']
CONFIRMATION_ACCESS_TYPE = 'CONFIRMATION_EXECUTION'   # only this unlocks a governed period

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
    # F-019: an evidence-preparation row must NEVER satisfy the confirmation gate.
    conf = [r for r in matches if (r.get('access_type') or '').strip().upper() == CONFIRMATION_ACCESS_TYPE]
    if not conf:
        kinds = sorted({(r.get('access_type') or 'UNSPECIFIED').strip() for r in matches})
        return False, (f'{period} has provenance rows but none with access_type={CONFIRMATION_ACCESS_TYPE} '
                       f'(found: {kinds}). Evidence-preparation access does NOT unlock confirmation execution.')
    r = conf[-1]
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

    hdr = 'period,first_inspection_date,what_was_viewed,decision_made_after,project_source,code_commit,data_vintage_id,spent_YN,attestor,timestamp,access_type\n'
    ok = True
    ok &= case('empty attestation blocks', False, '2006-2015', hdr + '2006-2015,,,,,,,,,,\n')
    ok &= case('missing row blocks', False, '2024-2026', hdr + '2006-2015,,,,,,,,,,\n')
    ok &= case('complete CONFIRMATION attestation permits', True, '2006-2015',
               hdr + '2006-2015,2026-07-09,confirmation run,primary gate decision,repo,abc123,V20260709,N,Jason,2026-07-09T00:00:00Z,CONFIRMATION_EXECUTION\n')
    ok &= case('spent period blocks', False, '1998-2005',
               hdr + '1998-2005,2026-07-09,stress run,veto check,repo,abc123,V20260709,Y,Jason,2026-07-09T00:00:00Z,CONFIRMATION_EXECUTION\n')
    ok &= case('partial attestation blocks', False, '2024-2026',
               hdr + '2024-2026,2026-07-09,,,,abc123,V20260709,N,Jason,,CONFIRMATION_EXECUTION\n')
    ok &= case('F-019: EVIDENCE-PREP row does NOT unlock confirmation', False, '2006-2015',
               hdr + '2006-2015,2026-07-16,evidence prep,no decision,repo,abc,SHARADAR_20260620,N,Jason,2026-07-16T00:00:00Z,CORPORATE_ACTION_EVIDENCE_PREPARATION_ONLY\n')
    ok &= case('F-019: unspecified access_type does NOT unlock', False, '2024-2026',
               hdr + '2024-2026,2026-07-16,something,none,repo,abc,SHARADAR_20260620,N,Jason,2026-07-16T00:00:00Z,\n')
    ok &= case('non-governed period passes through', True, '2016-2023', hdr)

    # evidence-preparation mode cases
    def epcase(name, expect, period, emits):
        got, why = check_evidence_prep(period, emits)
        passed = got == expect
        results.append({'case': name, 'expect_allowed': expect, 'got_allowed': got, 'reason': why,
                        'result': 'PASS' if passed else 'FAIL'})
        return passed
    ok &= epcase('evidence-prep permits identities/calendar', True, '2006-2015',
                 ['formation_dates','eligible_identities','lot_calendar_windows','terminal_event_identities'])
    ok &= epcase('evidence-prep REFUSES signals', False, '2006-2015', ['formation_dates','signals'])
    ok &= epcase('evidence-prep REFUSES core selections', False, '2006-2015', ['core_selections'])
    ok &= epcase('evidence-prep REFUSES returns/NAV', False, '2006-2015', ['returns','nav'])
    ok &= epcase('evidence-prep REFUSES aggregate performance', False, '2006-2015', ['aggregate_performance'])
    ok &= epcase('evidence-prep REFUSES clone performance', False, '2006-2015', ['clone_performance'])

    # evidence-preparation mode cases
    def ecase(name, expect, period, arts):
        allowed, reason = check_evidence_prep(period, arts)
        passed = allowed == expect
        results.append({'case': name, 'expect_allowed': expect, 'got_allowed': allowed, 'reason': reason,
                        'result': 'PASS' if passed else 'FAIL'})
        return passed
    ok &= ecase('evprep permits identities+calendar', True, '2006-2015',
                {'formation_dates', 'eligible_identities', 'lot_calendar_windows', 'terminal_event_identities'})
    ok &= ecase('evprep REFUSES returns', False, '2006-2015', {'eligible_identities', 'returns'})
    ok &= ecase('evprep REFUSES core selections', False, '2006-2015', {'core_selections'})
    ok &= ecase('evprep REFUSES nav/aggregate', False, '2006-2015', {'nav', 'aggregate_performance'})
    ok &= ecase('evprep REFUSES unknown artifact', False, '2006-2015', {'something_else'})

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

EVIDENCE_PREP_ALLOWED = {'formation_dates', 'eligible_identities', 'lot_calendar_windows', 'terminal_event_identities'}
EVIDENCE_PREP_FORBIDDEN = {'signals', 'ranks', 'core_selections', 'clone_selections', 'clone_performance',
                           'nav', 'returns', 'aggregate_performance', 'cagr', 'percentile'}

def check_evidence_prep(period, emits):
    """Evidence-preparation mode: permits identity/calendar facts ONLY for a sealed period.
    Any attempt to emit a signal, rank, selection, NAV, return, or aggregate is REFUSED.
    Never marks a period spent and never constitutes confirmation execution."""
    bad = sorted(set(e.lower() for e in emits) & EVIDENCE_PREP_FORBIDDEN)
    unknown = sorted(set(e.lower() for e in emits) - EVIDENCE_PREP_ALLOWED - EVIDENCE_PREP_FORBIDDEN)
    if bad:
        return False, f'REFUSED: evidence-preparation mode forbids emitting {bad} for sealed period {period}'
    if unknown:
        return False, f'REFUSED: unrecognized emission {unknown}; evidence-prep allows only {sorted(EVIDENCE_PREP_ALLOWED)}'
    return True, (f'PERMITTED (evidence-preparation only) for {period}: {sorted(set(emits))}. '
                  'Period NOT spent; this is not confirmation execution.')

def main() -> int:
    args = sys.argv[1:]
    if args[:1] == ['--evidence-prep'] and len(args) >= 3:
        ok, why = check_evidence_prep(args[1], args[2].split(','))
        print(('PERMIT: ' if ok else 'BLOCK: ') + why)
        return 0 if ok else 1
    if args[:1] == ['--self-test']:
        return self_test()
    if args[:1] == ['--period'] and len(args) >= 2:
        allowed, reason = check_period(args[1], load_rows())
        print(('PERMIT: ' if allowed else 'BLOCK: ') + reason)
        return 0 if allowed else 1
    print(__doc__); return 2

if __name__ == '__main__':
    sys.exit(main())
