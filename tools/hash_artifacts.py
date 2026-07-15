#!/usr/bin/env python3
"""hash_artifacts.py — Phase D: verify the run manifest against disk (companion gate to
build_compact_bundle). Fails on any missing artifact or hash drift."""
import json, sys, hashlib
from pathlib import Path

def sha256(p):
    h = hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()

def main() -> int:
    man = json.load(open('manifests/run_manifest_phaseD.json'))
    bad = []
    for o in man['outputs']:
        p = Path(o['path'])
        if not p.exists(): bad.append((o['path'], 'MISSING'))
        elif sha256(p) != o['content_hash']: bad.append((o['path'], 'DRIFT'))
    print(('PASS' if not bad else 'FAIL') + f" hash_artifacts: {len(man['outputs'])} checked" + (f'; {bad}' if bad else ''))
    return 0 if not bad else 1

if __name__ == '__main__':
    sys.exit(main())
