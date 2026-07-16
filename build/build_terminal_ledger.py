#!/usr/bin/env python3
"""build_terminal_ledger.py — event-level terminal ledger (B0-05 closure vehicle, v3.2.4 S3.6).
Emits ONE ROW PER TERMINAL EVENT touching any CORE- or clone-eligible name, with the policy
branch each event resolves to under config/terminal_policy.yaml and the evidence still missing.
This replaces any global assumption about ACTIONS.value semantics: no event is valued until its
branch has both vendor-semantic and transaction evidence. Until then every event resolves to
unverified_ma (canon fallback), which is what makes runs PROVISIONAL."""
import json, sys, datetime, hashlib
from pathlib import Path
import duckdb, yaml

def main() -> int:
    pol = yaml.safe_load(open('config/terminal_policy.yaml'))
    con = duckdb.connect()
    con.execute("CREATE VIEW ac AS SELECT * FROM read_parquet('data/clean/actions_clean.parquet')")
    con.execute("CREATE VIEW te AS SELECT * FROM read_parquet('data/clean/terminal_events.parquet')")
    con.execute("CREATE VIEW el AS SELECT DISTINCT permaticker, formation FROM read_parquet('data/clean/eligible_snapshots.parquet')")
    # every terminal event on a name that was EVER eligible (CORE or clone could hold it)
    rows = con.execute("""
        SELECT t.permaticker, t.last_trade_date, t.event_type,
               (SELECT COUNT(*) FROM el WHERE el.permaticker = t.permaticker) AS eligible_appearances,
               (SELECT MIN(formation) FROM el WHERE el.permaticker = t.permaticker) AS first_elig,
               (SELECT MAX(formation) FROM el WHERE el.permaticker = t.permaticker) AS last_elig
        FROM te t WHERE EXISTS (SELECT 1 FROM el WHERE el.permaticker = t.permaticker)
        ORDER BY t.last_trade_date""").fetchall()
    BRANCH = {'ACQUIRED': 'cash_acquisition_OR_stock_acquisition_UNDETERMINED',
              'MERGER': 'stock_acquisition_OR_mixed_UNDETERMINED',
              'BANKRUPTCY_LIQUIDATION': 'verified_bankruptcy_zero_recovery_UNVERIFIED',
              'DELISTED_OTHER': 'unverified_ma', 'TICKER_CHANGE': 'identity_continuation',
              'NO_ACTION_EVIDENCE': 'unverified_ma'}
    ledger = []
    for p, ltd, et, n_el, f0, f1 in rows:
        target = BRANCH.get(et, 'unverified_ma')
        resolved = 'identity_continuation' if target == 'identity_continuation' else 'unverified_ma'
        ledger.append({'permaticker': p, 'last_trade_date': str(ltd), 'vendor_event_type': et,
            'eligible_appearances': n_el, 'first_eligible_formation': str(f0), 'last_eligible_formation': str(f1),
            'target_policy_branch': target, 'RESOLVED_BRANCH_TODAY': resolved,
            'evidence_missing': [] if resolved == 'identity_continuation' else
                ['vendor ACTIONS.value semantics (B0-05)', 'SEC 8-K / merger agreement transaction terms'],
            'in_2016_2023_window': str(f1) >= '2016-01-01' and str(f0) <= '2023-12-31'})
    dev_window = [e for e in ledger if e['in_2016_2023_window']]
    rep = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'terminal_policy_version': pol['terminal_policy_version'],
           'policy_effective': pol['effective_before_rerun'],
           'total_events_on_eligible_names': len(ledger),
           'events_touching_2016_2023_window': len(dev_window),
           'resolved_branch_counts': {b: sum(1 for e in ledger if e['RESOLVED_BRANCH_TODAY'] == b)
                                      for b in {e['RESOLVED_BRANCH_TODAY'] for e in ledger}},
           'target_branch_counts': {b: sum(1 for e in ledger if e['target_policy_branch'] == b)
                                    for b in {e['target_policy_branch'] for e in ledger}},
           'b005_status': 'OPEN — no event may leave unverified_ma until BOTH vendor-semantic and transaction evidence are filed per event (or per class with documented class-level evidence).',
           'ledger': ledger}
    Path('results/phaseE').mkdir(parents=True, exist_ok=True)
    Path('results/phaseE/terminal_ledger.json').write_text(json.dumps(rep, indent=2, default=str) + '\n')
    print(f"PASS terminal ledger: {len(ledger)} events on eligible names, {len(dev_window)} touch 2016-2023")
    print(' resolved today:', rep['resolved_branch_counts'])
    print(' targets pending evidence:', rep['target_branch_counts'])
    return 0

if __name__ == '__main__':
    sys.exit(main())
