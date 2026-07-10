#!/usr/bin/env python3
from pathlib import Path
required = [
 'operator_runbook.md','Makefile','blocker_ledger.csv','status_dashboard.csv','status_dashboard.md',
 'docs/implementation_dag.md','protocol_contracts/scientific_design_contract.md','protocol_contracts/statistical_validation_contract.md',
 'protocol_contracts/data_fidelity_contract.md','protocol_contracts/computational_assurance_contract.md',
 'schemas/config.schema.json','schemas/raw_archive_manifest.schema.json','schemas/run_manifest.schema.json','schemas/status_dashboard.schema.json',
 'schemas/clean_outputs/tickers_universe.schema.json','schemas/clean_outputs/sep_prices.schema.json','schemas/clean_outputs/actions.schema.json','schemas/clean_outputs/terminal_events.schema.json','schemas/clean_outputs/eligible_snapshots.schema.json',
 'fixtures/golden_v1/README.md','fixtures/golden_v1/inputs/tickers_fixture.csv','fixtures/golden_v1/expected/selected_names.csv',
 'tests/scaffold/test_required_scaffold.py','tests/gates/test_blocking_gates.py'
]
missing=[p for p in required if not Path(p).exists()]
if missing: raise SystemExit('Missing required scaffold files: '+', '.join(missing))
print('PASS scaffold files present')
