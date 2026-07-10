#!/usr/bin/env python3
"""Phase A: freeze protocol/config/contract artifacts into protocol_release.json (SHA-256 per file)."""
import hashlib, json, sys, datetime
from pathlib import Path

FROZEN_GLOBS = [
    'protocol/design_contract.md',
    'protocol_contracts/*.md',
    'config/*.yaml',
    'schemas/*.json',
    'schemas/clean_outputs/*.json',
]

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    root = Path('.')
    files = sorted({f for g in FROZEN_GLOBS for f in root.glob(g) if f.is_file()})
    if not files:
        print('FAIL: no frozen artifacts found'); return 1
    entries = {str(f): sha256(f) for f in files}
    # run-level digest: hash of the sorted (path, hash) pairs
    run = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
    release = {
        'release_type': 'protocol_release',
        'package_version': '3.2.4',
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'file_hashes_sha256': entries,
        'release_digest_sha256': run,
        'note': 'Frozen at Phase A. Any hash change after Phase A exit requires a new release and ledger entry.',
    }
    Path('protocol_release.json').write_text(json.dumps(release, indent=2) + '\n')
    print(f'PASS protocol_release.json written: {len(entries)} artifacts, digest {run[:16]}...')
    return 0

if __name__ == '__main__':
    sys.exit(main())
