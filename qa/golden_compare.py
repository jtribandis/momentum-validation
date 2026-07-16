#!/usr/bin/env python3
"""golden_compare.py — G7 gate: engine outputs vs Jason's hand-derived golden truth.
Comparison rules (FD-04 tolerance contract): selections exact as ordered permaticker lists
(',' and ';' both accepted); numeric fields exact at their declared rounding (values are
already fixed-dp on both sides). Golden truth WINS by default: any mismatch is reported for
reconciliation with Jason — the engine is never presumed correct."""
import csv, json, sys, datetime
from pathlib import Path

def norm_sel(v): return [s.strip() for s in v.replace(';', ',').split(',') if s.strip()]

def key(r): return (r['section'], r['formation_or_date'], r['permaticker'], r['field'])

def main() -> int:
    golden = {key(r): r['value_JASON_FILLS'].strip() for r in csv.DictReader(open('fixtures/golden_v2/expected_outputs_SIGNED.csv'))}
    import sys as _s
    eng_path = _s.argv[1] if len(_s.argv) > 1 else 'results/phaseE/engine_outputs_py.csv'
    engine = {key(r): r['value'].strip() for r in csv.DictReader(open(eng_path))}
    mismatches, missing = [], []
    for k, gv in golden.items():
        if k not in engine:
            missing.append({'key': k, 'issue': 'ENGINE_MISSING'}); continue
        ev = engine[k]
        if k[3].startswith('top3'):
            ok = norm_sel(gv) == norm_sel(ev)
        else:
            try: ok = abs(float(gv) - float(ev)) < 5e-11 or f"{float(gv)}" == f"{float(ev)}"
            except ValueError: ok = gv == ev
        if not ok:
            mismatches.append({'key': list(k), 'golden': gv, 'engine': ev})
    extra = [list(k) for k in engine if k not in golden]
    rep = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'golden_rows': len(golden), 'engine_rows': len(engine),
           'mismatches': mismatches, 'engine_missing': missing, 'engine_extra_keys': extra,
           'overall': 'PASS' if not mismatches and not missing else 'FAIL'}
    Path('results/phaseE').mkdir(parents=True, exist_ok=True)
    Path('results/phaseE/golden_compare_' + Path(eng_path).stem.split('_')[-1] + '.json').write_text(json.dumps(rep, indent=2) + '\n')
    print(rep['overall'] + f" golden compare: {len(golden)} golden rows, {len(mismatches)} mismatches, {len(missing)} missing, {len(extra)} extra")
    for m in mismatches[:15]: print('  MISMATCH', m)
    return 0 if rep['overall'] == 'PASS' else 1

if __name__ == '__main__':
    sys.exit(main())
