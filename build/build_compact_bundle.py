#!/usr/bin/env python3
"""build_compact_bundle.py — Phase D: run manifest for the clean data bundle (protocol v3.2.4).
Emits manifests/run_manifest_phaseD.json conforming to schemas/run_manifest.schema.json:
protocol version, exact code commit (+dirty flag), frozen-config hash (release digest),
data vintage, and content hashes for every clean artifact."""
import json, sys, hashlib, subprocess
from pathlib import Path
import jsonschema

def sha256(p):
    h = hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()

def main() -> int:
    commit = subprocess.run(['git','rev-parse','HEAD'], capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(['git','status','--porcelain'], capture_output=True, text=True).stdout.strip())
    release = json.load(open('protocol_release.json'))
    vintage = json.load(open('manifests/raw_archive_manifest.json'))['data_vintage_id']
    outputs = []
    for p in sorted(Path('data/clean').glob('*.parquet')):
        outputs.append({'path': str(p), 'content_hash': sha256(p), 'file_hash': sha256(p), 'schema_version': 'clean_v1'})
    man = {'protocol_version': '3.2.4', 'code_commit': commit, 'dirty_state': dirty,
           'config_hash': release['release_digest_sha256'], 'data_vintage_id': vintage, 'outputs': outputs}
    jsonschema.validate(man, json.load(open('schemas/run_manifest.schema.json')))
    Path('manifests/run_manifest_phaseD.json').write_text(json.dumps(man, indent=2) + '\n')
    print(f'PASS compact bundle manifest: {len(outputs)} artifacts, commit {commit[:8]}, dirty={dirty}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
