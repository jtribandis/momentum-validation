#!/usr/bin/env python3
"""Phase B (venue-split mode): verify the operator-reduced upload instead of fetching.
Replaces fetch_sharadar_raw.py + archive_raw.py in the Makefile because raw Sharadar data
lives only on the operator machine; B0-03 hashing happened there via reduce_sharadar_local.py.
Checks: raw manifest schema-valid; every parquet hash matches reduced_manifest.json;
manifest cross-hash matches (CRLF-tolerant, see F-009). Emits results/phaseB/reduced_upload_verification.json."""
import json, hashlib, sys, datetime
from pathlib import Path
import jsonschema

def h(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def hf(p: Path) -> str: return h(open(p,'rb').read())

def main() -> int:
    ok, checks = True, []
    raw = json.load(open('manifests/raw_archive_manifest.json'))
    jsonschema.validate(raw, json.load(open('schemas/raw_archive_manifest.schema.json')))
    checks.append({'check': 'raw_archive_manifest schema', 'result': 'PASS', 'vintage': raw['data_vintage_id']})
    rm = json.load(open('data/compact_upload/reduced_manifest.json'))
    if rm['data_vintage_id'] != raw['data_vintage_id']:
        ok = False; checks.append({'check': 'vintage match', 'result': 'FAIL', 'raw': raw['data_vintage_id'], 'reduced': rm['data_vintage_id']})
    else:
        checks.append({'check': 'vintage match', 'result': 'PASS'})
    for f in rm['files']:
        p = Path('data/compact_upload') / f['file']
        if not p.exists(): ok = False; checks.append({'file': f['file'], 'result': 'MISSING'}); continue
        got = hf(p)
        checks.append({'file': f['file'], 'result': 'PASS' if got == f['sha256'] else 'HASH_MISMATCH'})
        ok &= (got == f['sha256'])
    mb = open('manifests/raw_archive_manifest.json','rb').read()
    xh = rm['raw_archive_manifest_sha256']
    crlf_ok = h(mb) == xh or h(mb.replace(b'\n', b'\r\n')) == xh
    checks.append({'check': 'manifest cross-hash (CRLF-tolerant, F-009)', 'result': 'PASS' if crlf_ok else 'FAIL'})
    ok &= crlf_ok
    rep = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'overall': 'PASS' if ok else 'FAIL', 'checks': checks}
    Path('results/phaseB').mkdir(parents=True, exist_ok=True)
    Path('results/phaseB/reduced_upload_verification.json').write_text(json.dumps(rep, indent=2) + '\n')
    print(('PASS' if ok else 'FAIL') + ' reduced upload verification')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
