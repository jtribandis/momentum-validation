.PHONY: scaffold-check status blocker-check gate-test test phaseA phaseB phaseC phaseD phaseE phaseF phaseG phaseH phaseI phaseJ phaseK phaseL package-results verify-sources clean

scaffold-check:
	python tools/scaffold_check.py
	pytest -q tests/scaffold

status:
	python tools/update_status_dashboard.py

blocker-check:
	python tools/check_blockers.py

gate-test:
	pytest -q tests/gates

# By default, test means scaffold + blocking gates. It is expected to fail until blockers are resolved.
test: scaffold-check gate-test

phaseA:
	python tools/validate_json.py schemas/config.schema.json schemas/raw_archive_manifest.schema.json schemas/run_manifest.schema.json
	python tools/create_protocol_release.py
	python tools/validate_config.py
	python tools/validate_ledgers.py
	python tools/holdout_guard.py --self-test

phaseB: phaseA
	python build/verify_reduced_upload.py  # venue-split: reducer ran on operator machine (see findings F-008/F-009)
	python build/verify_vendor_semantics.py
	python build/build_security_master.py
	python build/build_price_panel.py
	python build/build_actions.py
	python build/build_terminal_events.py
	python build/build_sf1_asreported.py
	python qa/phaseB_no_aggregate_output.py

phaseC: phaseB
	python build/build_sp500_membership.py
	python build/build_eligible_snapshots.py
	python qa/audit_membership.py

phaseD: phaseC
	python build/build_compact_bundle.py
	python tools/hash_artifacts.py
	python qa/deterministic_reducer_check.py

phaseE: phaseD
	pytest -q tests/gates/test_golden_fixture_gate.py
	python tools/deterministic_rerun.py

phaseF: phaseE
	python tools/holdout_guard.py --period 2006-2015
	python analysis/core_backtest.py
	python analysis/null_clone.py
	python analysis/primary_gate.py
	python analysis/tail_audit.py

phaseG: phaseF
	python analysis/download_factors.py
	python analysis/attribution_ff5_mom.py

phaseH:
	python tools/check_module_inventory.py --module M3

phaseI:
	python tools/check_module_inventory.py --module M4

phaseJ: phaseG
	python tools/holdout_guard.py --period 1998-2005
	python analysis/core_backtest.py --period 1998-2005 --label selected_stress

phaseK: phaseJ
	python tools/holdout_guard.py --period 2024-2026
	python analysis/core_backtest.py --period 2024-2026 --label forward_holdout

phaseL: phaseK
	python analysis/lno_diagnostic.py

verify-sources:
	python tools/verify_source_ledger.py

package-results: status verify-sources
	@echo "Package manifests, results, logs, source verification ledger, status dashboard, and allowed claim language."

clean:
	rm -rf .pytest_cache tests/__pycache__ */__pycache__ */*/__pycache__
