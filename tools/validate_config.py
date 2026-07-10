#!/usr/bin/env python3
"""Phase A: validate frozen config YAMLs; emit results/phaseA/config_validation.json."""
import json, sys, datetime
from pathlib import Path
import yaml, jsonschema

def main() -> int:
    report = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'checks': [], 'warnings': []}
    ok = True

    cfg = yaml.safe_load(open('config/core_frozen.yaml'))
    schema = json.load(open('schemas/config.schema.json'))
    try:
        jsonschema.validate(cfg, schema)
        report['checks'].append({'file': 'config/core_frozen.yaml', 'schema': 'schemas/config.schema.json', 'result': 'PASS'})
    except jsonschema.ValidationError as e:
        ok = False
        report['checks'].append({'file': 'config/core_frozen.yaml', 'schema': 'schemas/config.schema.json', 'result': 'FAIL', 'error': e.message})

    # Presence + parse of the other frozen configs
    for f in ('config/modules_frozen.yaml', 'config/tolerance_contract.yaml', 'config/risk_limits.yaml'):
        try:
            data = yaml.safe_load(open(f))
            assert isinstance(data, dict) and data, 'empty or non-mapping'
            report['checks'].append({'file': f, 'result': 'PASS_PARSED'})
        except Exception as e:
            ok = False
            report['checks'].append({'file': f, 'result': 'FAIL', 'error': str(e)})

    # Frozen-value invariants (must match Sections 0-5)
    invariants = {
        'signal': 'TRAIL_6_SKIP_1', 'selection_count': 3, 'holding_months': 6,
        'rebalance_frequency': 'QUARTERLY', 'transaction_cost_bps_primary': 10,
        'clone_count': 10000, 'primary_effect_floor_annualized_excess': 0.03,
    }
    for k, v in invariants.items():
        if cfg.get(k) != v:
            ok = False
            report['checks'].append({'invariant': k, 'expected': v, 'actual': cfg.get(k), 'result': 'FAIL'})
    if all(cfg.get(k) == v for k, v in invariants.items()):
        report['checks'].append({'invariant_set': 'core_frozen_values', 'result': 'PASS'})

    if cfg.get('protocol_version') != '3.2.4':
        report['warnings'].append(f"protocol_version is '{cfg.get('protocol_version')}' but package is 3.2.4 — operator decision required (do not auto-edit a frozen field).")

    report['overall'] = 'PASS' if ok else 'FAIL'
    Path('results/phaseA').mkdir(parents=True, exist_ok=True)
    Path('results/phaseA/config_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(('PASS' if ok else 'FAIL') + ' config validation; report at results/phaseA/config_validation.json')
    for w in report['warnings']:
        print('WARN:', w)
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
