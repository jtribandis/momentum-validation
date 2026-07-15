#!/usr/bin/env python3
"""deterministic_reducer_check.py — Phase D: double-build determinism gate (protocol v3.2.4).
Snapshots hashes of every data/clean parquet, reruns the full builder chain from the same
committed inputs, and requires byte-identical outputs. Reports (JSON with timestamps) are
excluded by design; the gate is on data artifacts."""
import json, sys, hashlib, subprocess, datetime
from pathlib import Path

CHAIN = ['build/build_sp500_membership.py', 'build/build_security_master.py',
         'build/build_price_panel.py', 'build/build_actions.py',
         'build/build_terminal_events.py', 'build/build_eligible_snapshots.py']

def hashes():
    out = {}
    for p in sorted(Path('data/clean').glob('*.parquet')):
        h = hashlib.sha256()
        with open(p,'rb') as f:
            for c in iter(lambda: f.read(1<<20), b''): h.update(c)
        out[str(p)] = h.hexdigest()
    return out

def main() -> int:
    before = hashes()
    for s in CHAIN:
        r = subprocess.run([sys.executable, s], capture_output=True, text=True)
        if r.returncode != 0:
            print(f'FAIL: {s} exited {r.returncode}\n{r.stderr[-500:]}'); return 1
    after = hashes()
    diffs = sorted(set(before) ^ set(after)) + [k for k in before if k in after and before[k] != after[k]]
    rep = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'artifacts_checked': len(after), 'nondeterministic': diffs,
           'overall': 'PASS' if not diffs else 'FAIL'}
    Path('results/phaseD').mkdir(parents=True, exist_ok=True)
    Path('results/phaseD/determinism_check.json').write_text(json.dumps(rep, indent=2) + '\n')
    print(('PASS' if not diffs else 'FAIL') + f' determinism: {len(after)} artifacts, {len(diffs)} diffs')
    if diffs: print(' nondeterministic:', diffs)
    return 0 if not diffs else 1

if __name__ == '__main__':
    sys.exit(main())
