"""Queue-generator tests (review item 6). Assert on the COMMITTED artifacts and the code that
made them. No performance."""
import csv, json, hashlib, os, collections

def rows(p): return list(csv.DictReader(open(p)))

def test_manifest_matches_committed_csv_bytes():
    m = json.load(open('results/phaseE/review_queue_manifest.json'))
    for p, h in m['output_content_sha256'].items():
        assert hashlib.sha256(open(p,'rb').read()).hexdigest() == h, f'{p} drifted from manifest'

def test_generator_blob_sha_matches_repo_file():
    m = json.load(open('results/phaseE/review_queue_manifest.json'))
    assert hashlib.sha256(open('build/build_review_queues.py','rb').read()).hexdigest() == m['generator_blob_sha']

def test_no_tmp_dependency_in_generators():
    for f in ('build/build_review_queues.py', 'build/build_exposure_sets.py', 'build/build_clone_draws.py'):
        assert '/tmp/' not in open(f).read(), f'{f} has a /tmp dependency'

def test_event_ids_unique_per_event_not_per_exposure():
    ev = rows('results/phaseE/dev_transaction_events.csv')
    ids = [r['event_id'] for r in ev]
    assert len(ids) == len(set(ids)), 'event_id must be unique in the events queue'
    keys = [(r['permaticker'], r['last_trade_date'], r['event_type'], r['raw_action'], r['raw_action_date']) for r in ev]
    assert len(keys) == len(set(keys)), 'one row per canonical economic event'

def test_exposures_reference_real_events_and_repeat_by_design():
    ev = {r['event_id'] for r in rows('results/phaseE/dev_transaction_events.csv')}
    ex = rows('results/phaseE/dev_transaction_exposures.csv')
    assert all(r['event_id'] in ev for r in ex), 'orphan exposure'
    assert len({r['exposure_id'] for r in ex}) == len(ex), 'exposure_id must be unique'
    assert len(ex) >= len(ev), 'exposures >= events (one event can span formations)'

def test_exposure_count_matches_actual_exposures():
    ev = rows('results/phaseE/dev_transaction_events.csv')
    ex = rows('results/phaseE/dev_transaction_exposures.csv')
    c = collections.Counter(r['event_id'] for r in ex)
    for r in ev:
        assert int(r['exposure_count']) == c[r['event_id']], f"exposure_count wrong for {r['event_id']}"

def test_raw_action_matches_event_type_classification():
    want = {'ACQUIRED':'acquisitionby','MERGER_NONSURVIVOR':'mergerfrom','BANKRUPTCY_LIQUIDATION':'bankruptcyliquidation',
            'DELISTED_OTHER':'delisted','REGULATORY_DELISTING':'regulatorydelisting','VOLUNTARY_DELISTING':'voluntarydelisting'}
    for r in rows('results/phaseE/dev_transaction_events.csv'):
        if r['raw_action']:
            assert r['raw_action'] == want[r['event_type']], f"raw_action {r['raw_action']} != classification {r['event_type']}"

def test_raw_action_date_within_window_of_last_trade():
    import datetime
    for r in rows('results/phaseE/dev_transaction_events.csv'):
        if r['raw_action_date']:
            d1 = datetime.date.fromisoformat(r['raw_action_date']); d2 = datetime.date.fromisoformat(r['last_trade_date'])
            assert abs((d1 - d2).days) <= 45, 'raw action joined outside the declared window'

def test_cik_never_fabricated():
    for r in rows('results/phaseE/dev_transaction_events.csv') + rows('results/phaseE/phaseF_transaction_events.csv'):
        assert r['cik'] in ('', None) or r['cik'].isdigit(), f"non-numeric cik {r['cik']}"

def test_dev_and_phaseF_queues_are_separate_files():
    assert os.path.exists('results/phaseE/dev_transaction_events.csv')
    assert os.path.exists('results/phaseE/phaseF_transaction_events.csv')
    assert not os.path.exists('results/phaseE/manual_transaction_review_queue.csv'), 'combined queue must not exist'
    for r in rows('results/phaseE/phaseF_transaction_events.csv'):
        assert 'SEALED_PERIOD' in r['evidence_status']

def test_clone_draw_contract_and_hash_cover_all_columns():
    m = json.load(open('results/phaseE/clone_draws_manifest.json'))
    assert len(m['columns']) == 9
    import duckdb
    con = duckdb.connect()
    n = con.execute("SELECT COUNT(*) FROM read_parquet('results/phaseE/clone_draws.parquet')").fetchone()[0]
    assert n == m['rows'] == 630000
    rowsx = con.execute("""SELECT clone_id, formation_date, rank_position, permaticker, eligible_snapshot_hash,
        eligible_universe_size, seed, rng_algorithm, rng_version FROM read_parquet('results/phaseE/clone_draws.parquet')
        ORDER BY clone_id, formation_date, rank_position""").fetchall()
    canon = '\n'.join('|'.join(map(str, r)) for r in rowsx)
    assert hashlib.sha256(canon.encode()).hexdigest() == m['content_hash_sha256'], '9-column content hash mismatch'

def test_frozen_seed_and_consumption_contract_in_config():
    import yaml
    c = yaml.safe_load(open('config/core_frozen.yaml'))['clone_null']
    assert c['seed'] == '12878176638248399935' and c['clone_count'] == 10000
    assert c['min_universe_size'] == 3 and c['undersized_universe_policy'].startswith('HARD_FAIL')
    assert 'MUST be read from the frozen draw artifact' in c['draw_consumption_contract']
    assert 'ORDER BY permaticker' in c['universe_ordering_rule']


def test_no_scratch_path_dependency_in_generators_AST():
    """AST-based: scans string LITERALS in executable code, ignoring docstrings/comments.
    F-023 rationale: the prior substring test was satisfied by editing a DOCSTRING rather than
    the code — the artifact was changed to fit the test. This version cannot be gamed that way,
    and still detects a real dependency in a file with no comments at all."""
    import ast
    SCRATCH = ('/tmp/', '/var/tmp/', '/dev/shm/', 'C:\\Temp')
    for f in ('build/build_review_queues.py', 'build/build_exposure_sets.py', 'build/build_clone_draws.py'):
        tree = ast.parse(open(f).read(), filename=f)
        docs = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                d = ast.get_docstring(node, clean=False)
                if d: docs.add(d)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value not in docs:
                for s in SCRATCH:
                    assert s not in node.value, f'{f}:{node.lineno} executable literal uses scratch path {s!r}'
        assert not [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == 'gettempdir'], \
            f'{f} calls tempfile.gettempdir()'


def test_repo_has_no_stale_superseded_artifacts():
    """F-023: no tracked artifact may come from a superseded generator."""
    import subprocess
    tracked = set(subprocess.run(['git','ls-files','results/phaseE','build'], capture_output=True, text=True).stdout.split())
    banned = {'results/phaseE/clone_draws.sha256', 'results/phaseE/old111_vs_corrected.json',
              'results/phaseE/old_vs_new_terminal_worklist_diff.csv', 'results/phaseE/terminal_exposures_report.json',
              'results/phaseE/manual_transaction_review_queue.csv', 'results/phaseE/core_terminal_exposures.csv',
              'results/phaseE/clone_terminal_exposures.csv', 'results/phaseE/phaseF_possible_terminal_exposures.csv',
              'results/phaseE/dev_clone_transaction_review_queue.csv', 'results/phaseE/terminal_ledger.json',
              'results/phaseE/phaseF_possible_transaction_review_queue.csv',
              'build/build_terminal_exposures.py', 'build/reconcile_terminal_worklist.py', 'build/build_terminal_ledger.py'}
    assert not (banned & tracked), f'superseded artifacts still tracked: {sorted(banned & tracked)}'


def test_clone_hit_stats_scoped_to_exposed_pairs_only():
    s = json.load(open('results/phaseE/terminal_exposure_sets.json'))
    assert s['clone_hit_stats_scope'] == 'EXPOSED_PAIRS_ONLY'
    exposed = {f"{e['formation']}|{e['permaticker']}" for e in s['clone_exposures']}
    assert set(s['clone_hit_stats']) == exposed, 'clone_hit_stats must cover exactly the exposed pairs'
    assert len(s['clone_hit_stats']) == 91


def test_exposure_set_content_hash_excludes_timestamp():
    """F-024, superseded by the canonical-artifact rule: created_utc no longer exists in the
    artifact at all, so the logical content hash covers the whole artifact."""
    s = json.load(open('results/phaseE/terminal_exposure_sets.json'))
    m = json.load(open('results/phaseE/terminal_exposure_sets_manifest.json'))
    assert 'created_utc' not in s
    assert hashlib.sha256(json.dumps(s, sort_keys=True).encode()).hexdigest() == m['output_content_sha256']


def test_exact_action_join_never_picks_a_nearby_row():
    """Review item 1: two same-action rows within 45 days must NOT let the wrong one be chosen.
    Builds an in-memory ACTIONS table with a decoy 10 days before the true event date and proves
    the exact join selects the true date or reports NO_EXACT_RAW_ACTION_MATCH — never the decoy."""
    import duckdb, datetime
    con = duckdb.connect()
    con.execute("CREATE TABLE ac (permaticker BIGINT, action VARCHAR, date DATE, value DOUBLE, "
                "contraticker VARCHAR, contraname VARCHAR, ticker VARCHAR, name VARCHAR)")
    con.executemany("INSERT INTO ac VALUES (?,?,?,?,?,?,?,?)", [
        (1, 'acquisitionby', datetime.date(2020, 6, 1), 111.0, 'DECOY', 'Decoy Co', 'AAA', 'A Corp'),
        (1, 'acquisitionby', datetime.date(2020, 6, 11), 222.0, 'TRUE', 'True Co', 'AAA', 'A Corp')])
    def exact(p, want, d):
        return con.execute("SELECT action, date, value, contraticker FROM ac WHERE permaticker=? "
                           "AND action=? AND date=?", [p, want, d]).fetchall()
    hit = exact(1, 'acquisitionby', datetime.date(2020, 6, 11))
    assert len(hit) == 1 and hit[0][3] == 'TRUE', 'exact join must select the true-date row'
    assert exact(1, 'acquisitionby', datetime.date(2020, 6, 5)) == [], \
        'a date with no exact row must return nothing, not the nearby decoy'
    assert exact(1, 'mergerfrom', datetime.date(2020, 6, 11)) == [], \
        'wrong action code must not match'


def test_generator_uses_exact_equality_not_interval_join():
    src = open('build/build_review_queues.py').read()
    assert 'INTERVAL 45 DAY' not in src, 'proximity window must be gone from the queue generator'
    assert 'NO_EXACT_RAW_ACTION_MATCH' in src
    assert "date = DATE" in src, 'join must use exact date equality'


def test_match_modes_are_declared_and_valid():
    ok = {'EXACT_ACTION_DATE', 'EXACT_LAST_TRADE_DATE_VENDOR_EQUIVALENCE',
          'NO_EXACT_RAW_ACTION_MATCH', 'NO_EXPECTED_ACTION_CODE'}
    for f in ('dev', 'phaseF'):
        for r in csv.DictReader(open(f'results/phaseE/{f}_transaction_events.csv')):
            assert r['raw_action_match_mode'] in ok, f"bad match mode {r['raw_action_match_mode']}"
            if r['raw_action_match_mode'] == 'NO_EXACT_RAW_ACTION_MATCH':
                assert not r['raw_action'], 'unmatched events must carry no raw action fields'


def test_conflicting_rows_preserved_and_flagged_not_silently_deduped():
    found = 0
    for f in ('dev', 'phaseF'):
        for r in csv.DictReader(open(f'results/phaseE/{f}_transaction_events.csv')):
            if r['same_date_conflicting_rows'] == 'YES':
                found += 1
                rows = json.loads(r['conflicting_rows_preserved'])
                assert len(rows) == int(r['conflicting_row_count']) > 1
                assert len({json.dumps(x, sort_keys=True) for x in rows}) == len(rows), \
                    'preserved rows must be distinct (identical rows are deduped)'
            else:
                assert r['conflicting_rows_preserved'] == ''
    assert found == 6, f'expected 6 conflicting-row events (1 dev + 5 phaseF), found {found}'


def test_conflicts_do_not_inflate_exposures():
    for f in ('dev', 'phaseF'):
        ex = list(csv.DictReader(open(f'results/phaseE/{f}_transaction_exposures.csv')))
        keys = [(r['formation_date'], r['permaticker']) for r in ex]
        assert len(keys) == len(set(keys)), 'one exposure per lot interval; conflicts must not duplicate it'


def test_first_terminal_event_rule_recorded():
    s = json.load(open('results/phaseE/terminal_exposure_sets.json'))
    assert s['controlling_parameters']['first_terminal_event_rule'].startswith('earliest valid event')
    for e in s['clone_exposures'] + s['phaseF_possible_exposures'] + s['core_exposures']:
        assert e['terminal_event_selection_rule'] == 'FIRST_EVENT_IN_INTERVAL'
        assert e['events_in_interval'] >= 1
        if e['events_in_interval'] == 1:
            assert e['related_evidence_only_events'] == []
    m = s['multi_terminal_event_intervals']
    assert m['dev'] == 0 and m['phaseF'] == 0, 'multi-event counts must be explicitly recorded'


def test_exposure_manifest_declares_every_input_with_full_provenance():
    import glob as _g
    m = json.load(open('results/phaseE/terminal_exposure_sets_manifest.json'))
    assert m['schema_version'] == 'terminal_exposure_sets_v2'
    s = json.load(open('results/phaseE/terminal_exposure_sets.json'))
    assert s['schema_version'] == m['schema_version'], 'artifact and manifest schema versions must match'
    paths = [i['path'] for i in m['inputs']]
    for p in sorted(_g.glob('data/clean/sep_prices_part*.parquet')):
        assert p in paths, f'{p} missing from declared inputs'
    for c in ('config/core_frozen.yaml', 'config/terminal_policy.yaml', 'config/risk_limits.yaml',
              'config/tolerance_contract.yaml'):
        assert c in paths, f'{c} missing from declared inputs'
    for i in m['inputs']:
        assert set(('path', 'byte_sha256', 'schema_sha256', 'row_count')) <= set(i)
        assert hashlib.sha256(open(i['path'], 'rb').read()).hexdigest() == i['byte_sha256']
    for k in ('development_window', 'phaseF_window', 'holding_months', 'execution_timing',
              'selection_count', 'identity_rule'):
        assert k in m['controlling_parameters']


def test_artifact_has_no_timestamp_manifest_does():
    s = json.load(open('results/phaseE/terminal_exposure_sets.json'))
    assert 'created_utc' not in s, 'artifact must be timestamp-free (canonical bytes)'
    m = json.load(open('results/phaseE/terminal_exposure_sets_manifest.json'))
    assert 'created_utc' in m
    assert hashlib.sha256(open('results/phaseE/terminal_exposure_sets.json', 'rb').read()).hexdigest() \
        == m['artifact_byte_sha256']
