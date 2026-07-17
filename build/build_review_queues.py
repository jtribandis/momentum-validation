#!/usr/bin/env python3
"""build_review_queues.py — enriched, SEPARATED transaction review queues (v3.2.4, review item 4).
Two queues, never combined:
  dev_clone_transaction_review_queue.csv      — ACTUAL 2016-2023 development-clone exposures
  phaseF_possible_transaction_review_queue.csv — Phase F (2006-2015) POSSIBLE eligible-universe
                                                 exposures. Evidence-prep only; period sealed.
CIK is NOT a Sharadar TICKERS field; it is parsed from the secfilings URL where present and left
NULL otherwise (never fabricated). No performance computed."""
import csv, json, re, sys, hashlib, datetime
from pathlib import Path
import duckdb

VINTAGE = 'SHARADAR_20260620'
PRIORITY = {'BANKRUPTCY_LIQUIDATION': 'P1_ZERO_RECOVERY_CLAIM', 'ACQUIRED': 'P2_CONSIDERATION_UNKNOWN',
            'MERGER_NONSURVIVOR': 'P2_CONSIDERATION_UNKNOWN', 'REGULATORY_DELISTING': 'P3_DELISTING_TERMS',
            'VOLUNTARY_DELISTING': 'P3_DELISTING_TERMS', 'DELISTED_OTHER': 'P3_DELISTING_TERMS',
            'NO_ACTION_EVIDENCE': 'P4_NO_VENDOR_EVIDENCE'}
BRANCH = {'ACQUIRED': 'cash_acquisition|stock_acquisition|mixed_acquisition (UNDETERMINED)',
          'MERGER_NONSURVIVOR': 'stock_acquisition|mixed_acquisition (UNDETERMINED)',
          'BANKRUPTCY_LIQUIDATION': 'verified_bankruptcy_zero_recovery (UNVERIFIED)',
          'REGULATORY_DELISTING': 'unverified_ma', 'VOLUNTARY_DELISTING': 'unverified_ma',
          'DELISTED_OTHER': 'unverified_ma', 'NO_ACTION_EVIDENCE': 'unverified_ma'}
FIELDS = ['event_id','evaluation_window','formation_date','deploy_date','scheduled_exit_date','permaticker',
          'historical_ticker','company_name','cik','raw_action','raw_action_date','raw_value','raw_contraticker',
          'raw_contraname','last_trade_date','event_type','clone_lot_hits','affected_clone_count','first_clone_id',
          'source_row_ids','policy_target_branch','evidence_required','manual_review_priority','evidence_status',
          'data_vintage_id','content_hash']
EVIDENCE = ('SEC 8-K Item 2.01 (completion) or Item 1.03 (bankruptcy); definitive merger agreement / proxy '
            '(consideration + exchange ratio); exchange delisting notice; issuer IR announcement')

def main() -> int:
    con = duckdb.connect(); con.execute("SET threads TO 1")
    sets = json.load(open('/tmp/_sets.json'))
    lw = sets['lw']; hits = sets['hits']
    core_pairs = {(f, p) for f, p in sets['core_pairs']}
    clone_pairs = {(f, p) for f, p in sets['clone_pairs']}
    con.execute("CREATE VIEW te AS SELECT * FROM read_parquet('data/clean/terminal_events.parquet')")
    con.execute("CREATE VIEW el AS SELECT * FROM read_parquet('data/clean/eligible_snapshots.parquet')")
    con.execute("CREATE VIEW ac AS SELECT * FROM read_parquet('data/clean/actions_clean.parquet')")
    con.execute("CREATE VIEW px AS SELECT permaticker p, date d, openadj o FROM read_parquet('data/clean/sep_prices_part*.parquet')")
    meta = {r[0]: r[1:] for r in con.execute("""
        SELECT permaticker, MAX(ticker), MAX("name"), MAX(secfilings)
        FROM read_parquet('data/compact_upload/tickers_universe.parquet')
        WHERE "table"='SEP' GROUP BY 1""").fetchall()}
    term = {r[0]: (str(r[1]), r[2]) for r in con.execute("SELECT permaticker, last_trade_date, event_type FROM te").fetchall()}
    raw = {}
    for p, d, a, v, ct, cn in con.execute("""SELECT permaticker, date, action, value, contraticker, contraname FROM ac
        WHERE action IN ('acquisitionby','mergerfrom','bankruptcyliquidation','delisted','regulatorydelisting','voluntarydelisting')""").fetchall():
        raw.setdefault(p, []).append((str(d), a, v, ct, cn))
    def cik_of(p):
        s = meta.get(p, (None, None, None))[2]
        m = re.search(r'CIK=(\d+)|cik[=/](\d+)', s or '', re.I)
        return (m.group(1) or m.group(2)) if m else None

    def row(f, p, window):
        tk, nm, _ = meta.get(p, (None, None, None))
        rr = raw.get(p, [])
        r0 = rr[0] if rr else (None, None, None, None, None)
        dep, ex = lw[f]
        h = hits.get(f'{f}|{p}', [0, None, 0])
        d = {'evaluation_window': window, 'formation_date': f, 'deploy_date': dep, 'scheduled_exit_date': ex,
             'permaticker': p, 'historical_ticker': tk, 'company_name': nm, 'cik': cik_of(p),
             'raw_action': r0[1], 'raw_action_date': r0[0], 'raw_value': r0[2], 'raw_contraticker': r0[3],
             'raw_contraname': r0[4], 'last_trade_date': term[p][0], 'event_type': term[p][1],
             'clone_lot_hits': h[0], 'affected_clone_count': h[2], 'first_clone_id': h[1],
             'source_row_ids': ';'.join(f'ACTIONS:{p}|{x[0]}|{x[1]}' for x in rr) or None,
             'policy_target_branch': BRANCH.get(term[p][1], 'unverified_ma'), 'evidence_required': EVIDENCE,
             'manual_review_priority': PRIORITY.get(term[p][1], 'P4_NO_VENDOR_EVIDENCE'),
             'evidence_status': 'PENDING_TRANSACTION_EVIDENCE', 'data_vintage_id': VINTAGE}
        d['event_id'] = 'EV-' + hashlib.sha256(f"{p}|{term[p][0]}|{f}|{window}".encode()).hexdigest()[:12]
        d['content_hash'] = hashlib.sha256(json.dumps({k: str(d.get(k)) for k in FIELDS if k != 'content_hash'}, sort_keys=True).encode()).hexdigest()
        return d

    dev = [row(f, p, 'DEV_2016_2023_ACTUAL_CLONE_EXPOSURE') for f, p in sorted(clone_pairs | core_pairs)]
    # Phase F possible (evidence-prep only)
    trading = [str(r[0]) for r in con.execute("SELECT DISTINCT d FROM px ORDER BY d").fetchall()]
    me = [str(r[0]) for r in con.execute("SELECT month_end FROM read_parquet('data/clean/month_end_calendar.parquet') ORDER BY month").fetchall()]
    def foa(d):
        for t in trading:
            if t > d: return t
    def me6(d):
        for i, m in enumerate(me):
            if m == d: return me[i+6] if i+6 < len(me) else None
    ff = [str(r[0]) for r in con.execute("SELECT DISTINCT formation FROM el WHERE formation BETWEEN DATE '2006-01-01' AND DATE '2015-12-31' ORDER BY 1").fetchall()]
    pf = []
    for f in ff:
        x6 = me6(f)
        if not x6: continue
        dep, ex = foa(f), foa(x6)
        lw[f] = [dep, ex]
        for (p,) in con.execute(f"SELECT permaticker FROM el WHERE formation = DATE '{f}' ORDER BY permaticker").fetchall():
            if p in term and dep <= term[p][0] < ex:
                r = row(f, p, 'PHASEF_2006_2015_POSSIBLE_ELIGIBLE_UNIVERSE_EXPOSURE')
                r['clone_lot_hits'] = None; r['affected_clone_count'] = None; r['first_clone_id'] = None
                pf.append(r)
    def dump(path, rows):
        with open(path,'w',newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader()
            for r in rows: w.writerow({k: r.get(k) for k in FIELDS})
    dump('results/phaseE/dev_clone_transaction_review_queue.csv', dev)
    dump('results/phaseE/phaseF_possible_transaction_review_queue.csv', pf)
    for old in ('results/phaseE/manual_transaction_review_queue.csv',):
        Path(old).unlink(missing_ok=True)
    def bycls(rows):
        o = {}
        for r in rows: o[r['event_type']] = o.get(r['event_type'], 0) + 1
        return o
    rep = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'dev_clone_queue': {'rows_formation_permaticker_pairs': len(dev),
                               'unique_events': len({(r['permaticker'], r['last_trade_date']) for r in dev}),
                               'by_event_type': bycls(dev), 'by_priority': {p: sum(1 for r in dev if r['manual_review_priority']==p) for p in {r['manual_review_priority'] for r in dev}},
                               'core_exposures_included': len(core_pairs)},
           'phaseF_possible_queue': {'rows_formation_permaticker_pairs': len(pf),
                                     'unique_events': len({(r['permaticker'], r['last_trade_date']) for r in pf}),
                                     'by_event_type': bycls(pf),
                                     'access_class': 'CORPORATE_ACTION_EVIDENCE_PREPARATION_ONLY; period NOT spent'},
           'cik_availability': {'source': 'parsed from TICKERS.secfilings URL; cik is NOT a Sharadar field',
                                'dev_populated': sum(1 for r in dev if r['cik']), 'dev_null': sum(1 for r in dev if not r['cik']),
                                'phaseF_populated': sum(1 for r in pf if r['cik']), 'phaseF_null': sum(1 for r in pf if not r['cik'])},
           'combined_count_prohibited': 'Development-clone ACTUAL exposures and Phase F POSSIBLE exposures are never summed.',
           'NO_PERFORMANCE_COMPUTED': True}
    Path('results/phaseE/review_queues_report.json').write_text(json.dumps(rep, indent=2, default=str) + '\n')
    print(json.dumps(rep, indent=2, default=str)[:1200])
    return 0

if __name__ == '__main__':
    sys.exit(main())
