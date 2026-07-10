from pathlib import Path


def test_required_scaffold_files_exist():
    required = [
        'operator_runbook.md','Makefile','blocker_ledger.csv','status_dashboard.md','docs/implementation_dag.md',
        'protocol_contracts/scientific_design_contract.md','protocol_contracts/statistical_validation_contract.md',
        'protocol_contracts/data_fidelity_contract.md','protocol_contracts/computational_assurance_contract.md',
        'schemas/config.schema.json','schemas/raw_archive_manifest.schema.json','schemas/run_manifest.schema.json',
        'fixtures/golden_v1/README.md','evidence/source_verification/source_claim_map.csv'
    ]
    missing=[p for p in required if not Path(p).exists()]
    assert not missing, 'Missing scaffold files: '+', '.join(missing)


def test_makefile_contains_explicit_dag_targets():
    makefile=Path('Makefile').read_text()
    for target in ['phaseA:', 'phaseB: phaseA', 'phaseC: phaseB', 'phaseD: phaseC', 'phaseE: phaseD', 'phaseF: phaseE', 'phaseG: phaseF', 'phaseK: phaseJ', 'phaseL: phaseK']:
        assert target in makefile
