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
