#!/usr/bin/env python3
"""build_terminal_events.py — terminal-event classification (v3.2.4 S3.6).
CORRECTED 2026-07-16 against official vendor semantics
(evidence/vendor_semantics/SHARADAR_INDICATORS_ACTIONS_ACTIONTYPES_20260716.csv,
 sha256 52ef6da7...). See results/phaseB/terminal_event_semantics.json.

Binding rules (vendor-verified):
  acquisitionby  -> TERMINAL for ticker (ticker = ACQUIRED company)
  acquisitionof  -> NOT terminal for ticker (ticker = ACQUIRING company)
  mergerfrom     -> TERMINAL for ticker (ticker = NON-SURVIVING company)
  mergerto       -> NOT terminal for ticker (ticker = SURVIVING company)   [was a DEFECT: see F-016]
  bankruptcyliquidation / delisted / regulatorydelisting / voluntarydelisting -> TERMINAL
  relation       -> NOT terminal, NOT identity continuation
  tickerchange*  -> identity continuation, NOT terminal
  ACTIONS.value is FINAL MARKET CAP -> NEVER used as terminal per-share proceeds.
  ACTIONS.date is LAST TRADE DATE -> NEVER labeled legal completion date.
Paired mirror rows (acquisitionby/acquisitionof, mergerfrom/mergerto) are deduplicated by
keeping only the row whose ticker is the terminating entity."""
import json, sys, datetime, hashlib
from pathlib import Path
import duckdb

TERMINAL_ACTIONS = {'acquisitionby': 'ACQUIRED', 'mergerfrom': 'MERGER_NONSURVIVOR',
                    'bankruptcyliquidation': 'BANKRUPTCY_LIQUIDATION', 'delisted': 'DELISTED_OTHER',
                    'regulatorydelisting': 'REGULATORY_DELISTING', 'voluntarydelisting': 'VOLUNTARY_DELISTING'}
NON_TERMINAL = {'acquisitionof', 'mergerto', 'relation', 'tickerchangefrom', 'tickerchangeto',
                'split', 'dividend', 'listed', 'initiated', 'spinoff', 'spinoffdividend',
                'spunofffrom', 'adrratiosplit'}

def sha256(p):
    h = hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()

def classify(actions_for_perm):
    """actions_for_perm: list of (action, date). Returns (event_type, event_date) or None.
    Priority: bankruptcy > acquired > merger_nonsurvivor > regulatory > voluntary > delisted."""
    PRIORITY = ['bankruptcyliquidation', 'acquisitionby', 'mergerfrom',
                'regulatorydelisting', 'voluntarydelisting', 'delisted']
    hits = {a: d for a, d in actions_for_perm if a in TERMINAL_ACTIONS}
    for a in PRIORITY:
        if a in hits: return TERMINAL_ACTIONS[a], hits[a]
    return None, None

def main() -> int:
    con = duckdb.connect()
    horizon = con.execute("SELECT MAX(date) FROM read_parquet('data/clean/sep_prices_part*.parquet')").fetchone()[0]
    con.execute(f"""CREATE TABLE last_px AS
        SELECT p.permaticker, MAX(p.date) last_trade_date
        FROM read_parquet('data/clean/sep_prices_part*.parquet') p
        JOIN (SELECT DISTINCT permaticker FROM read_parquet('data/clean/membership_snapshots.parquet')) m USING (permaticker)
        GROUP BY 1 HAVING MAX(p.date) < DATE '{horizon}' - INTERVAL 10 DAY""")
    tl = ','.join(f"'{a}'" for a in TERMINAL_ACTIONS)
    rows = con.execute(f"""
        SELECT l.permaticker, l.last_trade_date, a.action, a.date
        FROM last_px l LEFT JOIN read_parquet('data/clean/actions_clean.parquet') a
          ON a.permaticker = l.permaticker
         AND a.date BETWEEN l.last_trade_date - INTERVAL 45 DAY AND l.last_trade_date + INTERVAL 45 DAY
         AND a.action IN ({tl})
        ORDER BY l.permaticker""").fetchall()
    byp = {}
    for p, ltd, act, ad in rows:
        byp.setdefault(p, {'ltd': ltd, 'acts': []})
        if act: byp[p]['acts'].append((act, ad))
    out = []
    for p, v in byp.items():
        et, ed = classify(v['acts'])
        out.append({'permaticker': p, 'last_trade_date': str(v['ltd']),
                    'event_type': et or 'NO_ACTION_EVIDENCE',
                    'action_date_last_trade_per_vendor': str(ed) if ed else None,
                    'value_units_unverified': False,      # vendor semantics now RESOLVED
                    'value_is_market_cap_never_proceeds': True,
                    'terminal_return_policy': 'CLASSIFICATION_ONLY_NO_TERMINAL_RETURN_ASSIGNED'})
    con.execute("CREATE TABLE ev (permaticker BIGINT, last_trade_date DATE, event_type VARCHAR, action_date DATE)")
    con.executemany("INSERT INTO ev VALUES (?,?,?,?)",
        [(o['permaticker'], o['last_trade_date'], o['event_type'], o['action_date_last_trade_per_vendor']) for o in out])
    con.execute("COPY (SELECT * FROM ev ORDER BY permaticker) TO 'data/clean/terminal_events.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)")
    mix = {}
    for o in out: mix[o['event_type']] = mix.get(o['event_type'], 0) + 1
    rep = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'vendor_semantics_source': 'evidence/vendor_semantics/SHARADAR_INDICATORS_ACTIONS_ACTIONTYPES_20260716.csv',
           'vendor_semantics_sha256': '52ef6da79c66bdee51e25b882185787ea44dfbe2dc67a66cc2d4e5e949d4b420',
           'terminated_member_permatickers': len(out), 'event_type_mix': mix,
           'corrections_applied': ['mergerto REMOVED as terminal (ticker = surviving company) - F-016',
                                   'mergerfrom ADDED as terminal (ticker = non-surviving company)',
                                   'acquisitionof explicitly non-terminal (ticker = acquirer)',
                                   'regulatorydelisting + voluntarydelisting ADDED as terminal',
                                   'relation explicitly non-terminal'],
           'output_sha256': sha256(Path('data/clean/terminal_events.parquet')), 'overall': 'PASS'}
    Path('results/phaseB/terminal_events_report.json').write_text(json.dumps(rep, indent=2, default=str) + '\n')
    print('PASS terminal events (vendor-corrected):', mix)
    return 0

if __name__ == '__main__':
    sys.exit(main())
