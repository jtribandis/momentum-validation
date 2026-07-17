#!/usr/bin/env python3
"""build_review_queues.py — event-level transaction review queues (review items 1, 3).
Reads results/phaseE/terminal_exposure_sets.json (versioned, hashed; no scratch-file dependency).

Event-level keys (review item 3): a canonical economic event is keyed by
(permaticker, last_trade_date, event_type, raw_action, raw_action_date). Raw ACTIONS rows are
joined by ACTUAL event date + action classification - never r0=rr[0].
  event_id    = EV-<sha16 of the canonical event key>      -> reviewed ONCE per event
  exposure_id = <event_id>|<formation_date>|<evaluation_window>

Emits FOUR artifacts:
  dev_transaction_events.csv     unique development events (manual evidence unit)
  dev_transaction_exposures.csv  formation-permaticker exposure pairs (accounting unit)
  phaseF_transaction_events.csv / phaseF_transaction_exposures.csv (sealed period, evidence-prep)
plus a queue manifest. CIK is NOT a Sharadar field; parsed from secfilings URL where present,
left NULL otherwise, NEVER fabricated. No performance computed.
"""
import csv, json, re, sys, hashlib, datetime, subprocess, platform
from pathlib import Path
import duckdb

VINTAGE = 'SHARADAR_20260620'
TERMINAL_ACTIONS = ('acquisitionby','mergerfrom','bankruptcyliquidation','delisted',
                    'regulatorydelisting','voluntarydelisting')
PRIORITY = {'BANKRUPTCY_LIQUIDATION': 'P1_ZERO_RECOVERY_CLAIM', 'ACQUIRED': 'P2_CONSIDERATION_UNKNOWN',
            'MERGER_NONSURVIVOR': 'P2_CONSIDERATION_UNKNOWN', 'REGULATORY_DELISTING': 'P3_DELISTING_TERMS',
            'VOLUNTARY_DELISTING': 'P3_DELISTING_TERMS', 'DELISTED_OTHER': 'P3_DELISTING_TERMS',
            'NO_ACTION_EVIDENCE': 'P4_NO_VENDOR_EVIDENCE'}
BRANCH = {'ACQUIRED': 'cash_acquisition|stock_acquisition|mixed_acquisition (UNDETERMINED)',
          'MERGER_NONSURVIVOR': 'stock_acquisition|mixed_acquisition (UNDETERMINED)',
          'BANKRUPTCY_LIQUIDATION': 'verified_bankruptcy_zero_recovery (UNVERIFIED)',
          'REGULATORY_DELISTING': 'unverified_ma', 'VOLUNTARY_DELISTING': 'unverified_ma',
          'DELISTED_OTHER': 'unverified_ma', 'NO_ACTION_EVIDENCE': 'unverified_ma'}
EVIDENCE = ('SEC 8-K Item 2.01 (completion) or Item 1.03 (bankruptcy); definitive merger agreement/proxy '
            '(consideration + exchange ratio); exchange delisting notice; issuer IR announcement')
EVENT_FIELDS = ['event_id','evaluation_window','permaticker','historical_ticker','company_name','cik',
                'raw_action','raw_action_date','raw_value','raw_contraticker','raw_contraname',
                'last_trade_date','event_type','raw_action_match_mode','same_date_conflicting_rows',
                'conflicting_row_count','conflicting_rows_preserved','terminal_event_selection_rule','events_in_interval',
                'source_row_ids','policy_target_branch','evidence_required',
                'manual_review_priority','evidence_status','data_vintage_id','exposure_count',
                'total_clone_lot_hits','content_hash']
EXP_FIELDS = ['exposure_id','event_id','evaluation_window','formation_date','deploy_date',
              'scheduled_exit_date','permaticker','last_trade_date','event_type','clone_lot_hits',
              'affected_clone_count','first_clone_id','data_vintage_id','content_hash']

def event_id(p, ltd, et, ra, rad):
    return 'EV-' + hashlib.sha256(f'{p}|{ltd}|{et}|{ra}|{rad}'.encode()).hexdigest()[:16]

def chash(rec, skip='content_hash'):
    return hashlib.sha256(json.dumps({k: ('' if v is None else str(v)) for k, v in rec.items() if k != skip},
                                     sort_keys=True).encode()).hexdigest()[:16]

def main() -> int:
    con = duckdb.connect(); con.execute('SET threads TO 1')
    sets = json.load(open('results/phaseE/terminal_exposure_sets.json'))
    con.execute("CREATE VIEW ac AS SELECT * FROM read_parquet('data/clean/actions_clean.parquet')")
    con.execute("CREATE VIEW tkr AS SELECT * FROM read_parquet('data/compact_upload/tickers_universe.parquet')")

    # Vendor semantics (evidence/vendor_semantics/, sha256 52ef6da7) state that for every
    # terminal action code, ACTIONS.date IS the last trade date. That is the ONLY reason an
    # exact-last_trade_date fallback is permitted when action_date is absent.
    ACTION_DATE_IS_LAST_TRADE = {'acquisitionby', 'mergerfrom', 'bankruptcyliquidation',
                                 'delisted', 'regulatorydelisting', 'voluntarydelisting'}
    EXPECTED = {'ACQUIRED': 'acquisitionby', 'MERGER_NONSURVIVOR': 'mergerfrom',
                'BANKRUPTCY_LIQUIDATION': 'bankruptcyliquidation', 'DELISTED_OTHER': 'delisted',
                'REGULATORY_DELISTING': 'regulatorydelisting', 'VOLUNTARY_DELISTING': 'voluntarydelisting'}

    def raw_rows(p, ltd, et, action_date):
        """EXACT join: (permaticker, exact date, exact expected action code). No proximity search.
        Returns (rows, match_mode, conflict_flag). Never auto-picks a nearby row (review item 1)."""
        want = EXPECTED.get(et)
        if not want:
            return [], 'NO_EXPECTED_ACTION_CODE', False
        def q(d):
            return con.execute(f'''SELECT action, date, value, contraticker, contraname, ticker, "name"
                FROM ac WHERE permaticker={p} AND action = \'{want}\' AND date = DATE \'{d}\'
                ORDER BY action, date, value, contraticker, contraname, ticker, "name"''').fetchall()
        rows, mode = ([], None)
        if action_date:
            rows = q(action_date)
            mode = 'EXACT_ACTION_DATE' if rows else None
        if not rows and want in ACTION_DATE_IS_LAST_TRADE:
            rows = q(ltd)
            mode = 'EXACT_LAST_TRADE_DATE_VENDOR_EQUIVALENCE' if rows else None
        if not rows:
            return [], 'NO_EXACT_RAW_ACTION_MATCH', False
        # Deduplicate ONLY rows identical across EVERY raw field.
        uniq = sorted(set(rows))
        # Same-date rows differing in any field are CONFLICTS: preserve and flag, never choose.
        conflict = len(uniq) > 1
        return uniq, mode, conflict

    def cik_of(p):
        r = con.execute(f"SELECT ANY_VALUE(secfilings) FROM tkr WHERE permaticker={p}").fetchone()
        if not r or not r[0]: return None
        m = re.search(r'CIK=?(\d{4,10})', str(r[0]), re.I)
        return m.group(1).lstrip('0') if m else None

    def build(exposures, window_tag, is_clone):
        events, exps = {}, []
        for e in exposures:
            p, ltd, et = e['permaticker'], e['last_trade_date'], e['event_type']
            rr, match_mode, conflict = raw_rows(p, ltd, et, e.get('action_date'))
            # ONE event per canonical economic event. Conflicting same-date rows are preserved
            # in-row as evidence and flagged; they must NEVER mint extra exposures for one lot.
            for r in [rr[0] if rr else (None, None, None, None, None, None, None)]:
                ra, rad = r[0], (str(r[1]) if r[1] else None)
                eid = event_id(p, ltd, et, ra, rad)
                st = sets['clone_hit_stats'].get(f"{e['formation']}|{p}", {}) if is_clone else {}
                if eid not in events:
                    events[eid] = {'event_id': eid, 'evaluation_window': window_tag, 'permaticker': p,
                        'historical_ticker': r[5], 'company_name': r[6], 'cik': cik_of(p),
                        'raw_action': ra, 'raw_action_date': rad, 'raw_value': r[2],
                        'raw_contraticker': r[3], 'raw_contraname': r[4], 'last_trade_date': ltd,
                        'event_type': et,
                        'terminal_event_selection_rule': e.get('terminal_event_selection_rule'),
                        'events_in_interval': e.get('events_in_interval'),
                        'source_row_ids': f'ACTIONS:permaticker={p},date={rad},action={ra}',
                        'raw_action_match_mode': match_mode,
                        'same_date_conflicting_rows': 'YES' if conflict else 'NO',
                        'conflicting_row_count': len(rr) if conflict else 0,
                        'conflicting_rows_preserved': (json.dumps([{'action': x[0], 'date': str(x[1]),
                            'value': x[2], 'contraticker': x[3], 'contraname': x[4], 'ticker': x[5],
                            'name': x[6]} for x in rr], sort_keys=True) if conflict else ''),
                        'policy_target_branch': BRANCH.get(et, 'unverified_ma'),
                        'evidence_required': EVIDENCE, 'manual_review_priority': PRIORITY.get(et, 'P4_NO_VENDOR_EVIDENCE'),
                        'evidence_status': ('PENDING_TRANSACTION_EVIDENCE' if is_clone else
                                            'PENDING_TRANSACTION_EVIDENCE_SEALED_PERIOD_NO_SELECTION_KNOWN'),
                        'data_vintage_id': VINTAGE, 'exposure_count': 0, 'total_clone_lot_hits': 0}
                events[eid]['exposure_count'] += 1
                events[eid]['total_clone_lot_hits'] += st.get('clone_lot_hits', 0)
                rec = {'exposure_id': f"{eid}|{e['formation']}|{window_tag}", 'event_id': eid,
                       'evaluation_window': window_tag, 'formation_date': e['formation'],
                       'deploy_date': e['deploy_date'], 'scheduled_exit_date': e['scheduled_exit_date'],
                       'permaticker': p, 'last_trade_date': ltd, 'event_type': et,
                       'clone_lot_hits': st.get('clone_lot_hits', 0),
                       'affected_clone_count': st.get('affected_clone_count', 0),
                       'first_clone_id': st.get('first_clone_id'), 'data_vintage_id': VINTAGE}
                rec['content_hash'] = chash(rec); exps.append(rec)
        for v in events.values(): v['content_hash'] = chash(v)
        return sorted(events.values(), key=lambda r: (r['last_trade_date'], r['permaticker'])), \
               sorted(exps, key=lambda r: (r['formation_date'], r['permaticker']))

    dev_e, dev_x = build(sets['clone_exposures'], 'DEV_2016_2023_ACTUAL_CLONE_EXPOSURE', True)
    pf_e, pf_x = build(sets['phaseF_possible_exposures'], 'PHASEF_2006_2015_POSSIBLE_ELIGIBLE_UNIVERSE_ONLY', False)

    def dump(path, rows, fields):
        with open(path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
            for r in rows: w.writerow({k: r.get(k) for k in fields})
        return hashlib.sha256(open(path, 'rb').read()).hexdigest()
    outs = {
      'results/phaseE/dev_transaction_events.csv': dump('results/phaseE/dev_transaction_events.csv', dev_e, EVENT_FIELDS),
      'results/phaseE/dev_transaction_exposures.csv': dump('results/phaseE/dev_transaction_exposures.csv', dev_x, EXP_FIELDS),
      'results/phaseE/phaseF_transaction_events.csv': dump('results/phaseE/phaseF_transaction_events.csv', pf_e, EVENT_FIELDS),
      'results/phaseE/phaseF_transaction_exposures.csv': dump('results/phaseE/phaseF_transaction_exposures.csv', pf_x, EXP_FIELDS)}
    ins = ['results/phaseE/terminal_exposure_sets.json', 'data/clean/actions_clean.parquet',
           'data/compact_upload/tickers_universe.parquet']
    Path('results/phaseE/review_queue_manifest.json').write_text(json.dumps({
        'generator_file': 'build/build_review_queues.py',
        'generator_blob_sha': hashlib.sha256(open('build/build_review_queues.py','rb').read()).hexdigest(),
        'git_commit': subprocess.run(['git','rev-parse','HEAD'], capture_output=True, text=True).stdout.strip(),
        'exact_command': 'python build/build_review_queues.py',
        'environment_digest': f'{platform.python_version()}|duckdb {duckdb.__version__}|{platform.system()}',
        'input_paths': ins,
        'input_sha256': {p: hashlib.sha256(open(p,'rb').read()).hexdigest() for p in ins if Path(p).exists()},
        'output_paths': list(outs), 'output_row_counts': {'dev_events': len(dev_e), 'dev_exposures': len(dev_x),
            'phaseF_events': len(pf_e), 'phaseF_exposures': len(pf_x)},
        'output_content_sha256': outs,
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}, indent=2) + '\n')
    print(f'PASS queues: dev events={len(dev_e)} exposures={len(dev_x)} | phaseF events={len(pf_e)} exposures={len(pf_x)}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
