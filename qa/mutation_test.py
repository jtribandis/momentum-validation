#!/usr/bin/env python3
"""G10 mutation testing: deliberately break the reference engine 8 ways; the golden gate must
kill EVERY mutant (comparator FAIL). A surviving mutant means the fixture lacks teeth."""
import json, subprocess, sys, shutil, datetime
from pathlib import Path

MUTS = [
 ('M1_tiebreak_desc',        'key=lambda p: (-sig[p], p)',                'key=lambda p: (-sig[p], -p)'),
 ('M2_skip_month_dropped',   'sig = {p: px[p][m1]/px[p][m7] - 1',         'sig = {p: px[p][fdate]/px[p][m7] - 1'),
 ('M3_entry_cost_dropped',   'shares = alloc / (o * (1 + COST))',         'shares = alloc / o'),
 ('M4_exit_cost_sign',       "op[p][ext] * (1 - COST)",                   "op[p][ext] * (1 + COST)"),
 ('M5_terminal_uses_close',  'exit_val = shares * term[p][1];',           'exit_val = shares * px[p][sorted(px[p])[-1]];'),
 ('M6_f3_alloc_not_chained', 'allocs = {p: sleeveA_F1_proceeds/3',        'allocs = {p: 150000.0/3'),
 ('M7_rank_ascending',       'key=lambda p: (-sig[p], p)',                'key=lambda p: (sig[p], p)'),
 ('M8_nav_drops_term_cash',  "nav += L['exit_val']                    # terminal cash held at 0%", 'nav += 0.0  # MUTANT'),
]

def main() -> int:
    src = Path('engine/momentum_engine_py.py').read_text()
    results = []
    tmp = Path('/tmp/mutants'); tmp.mkdir(exist_ok=True)
    for name, old, new in MUTS:
        assert old in src, f'mutation anchor missing: {name}'
        mp = tmp / f'{name}.py'
        mp.write_text(src.replace(old, new, 1))
        out = tmp / f'{name}_out.csv'
        r1 = subprocess.run([sys.executable, str(mp), str(out)], capture_output=True, text=True)
        if r1.returncode != 0:
            results.append({'mutant': name, 'result': 'KILLED_CRASH'}); continue
        r2 = subprocess.run([sys.executable, 'qa/golden_compare.py', str(out)], capture_output=True, text=True)
        results.append({'mutant': name, 'result': 'KILLED' if r2.returncode != 0 else 'SURVIVED',
                        'detail': r2.stdout.strip().splitlines()[0] if r2.stdout else ''})
    survived = [r for r in results if r['result'] == 'SURVIVED']
    # baseline must still pass
    b1 = subprocess.run([sys.executable, 'engine/momentum_engine_py.py'], capture_output=True)
    b2 = subprocess.run([sys.executable, 'qa/golden_compare.py'], capture_output=True)
    baseline_ok = b1.returncode == 0 and b2.returncode == 0
    rep = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'mutants': results, 'killed': len(results) - len(survived), 'total': len(results),
           'baseline_passes': baseline_ok,
           'overall': 'PASS' if not survived and baseline_ok else 'FAIL'}
    Path('results/phaseE/mutation_report.json').write_text(json.dumps(rep, indent=2) + '\n')
    print(rep['overall'] + f" mutation: {rep['killed']}/{rep['total']} killed, baseline={'PASS' if baseline_ok else 'FAIL'}")
    for r in results: print(' ', r['mutant'], '->', r['result'])
    return 0 if rep['overall'] == 'PASS' else 1

if __name__ == '__main__':
    sys.exit(main())
