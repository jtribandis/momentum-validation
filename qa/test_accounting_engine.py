"""Common accounting engine tests (review item 5). Golden_v2 reproduction + mechanics traces
+ deterministic reconciliation. NO aggregate performance. golden_v3 branch tests are BLOCKED
pending Jason's hand-derived expected_outputs_SIGNED.csv (see test_golden_v3_blocked)."""
import csv, sys, math, os
sys.path.insert(0, 'engine')
from accounting_engine import AccountingEngine, TerminalPolicy, Lot, run

IN = 'fixtures/golden_v2/inputs/'

def load_v2():
    c, o = {}, {}
    for r in csv.DictReader(open(IN + 'month_end_prices.csv')):
        c.setdefault(int(r['permaticker']), {})[r['month_end_date']] = float(r['closeadj'])
    for r in csv.DictReader(open(IN + 'opens.csv')):
        o.setdefault(int(r['permaticker']), {})[r['date']] = float(r['openadj'])
    me = sorted({d for p in c for d in c[p]})
    return c, o, me

def golden():
    return {(r['section'], r['formation_or_date'], r['permaticker'], r['field']): r['value_JASON_FILLS'].strip()
            for r in csv.DictReader(open('fixtures/golden_v2/expected_outputs_SIGNED.csv'))}

def v2_engine():
    c, o, me = load_v2()
    return AccountingEngine(c, o, me, cost_bps=10.0)

def test_engine_reproduces_golden_v2_lots():
    """The SHARED engine must reproduce Jason's hand-derived lot values (F1 sleeve A)."""
    eng = v2_engine(); g = golden()
    pol = TerminalPolicy(events={900005: {'date': '2020-11-16', 'branch': 'cash_acquisition', 'cash_per_share': 90.0}})
    sel = [int(x) for x in g[('selection', '2020-03-31', '', 'top3_permatickers_in_rank_order')].replace(';', ',').split(',')]
    for p in sel:
        L = eng.open_lot(f'A|F1|{p}', 'A', 'F1', p, '2020-04-01', 150000.0/3, '2020-10-01')
        eng.close_lot(L, pol)
        assert abs(L.shares - float(g[('lot','F1',str(p),'shares_6dp')])) < 5e-7, f'shares mismatch {p}'
        assert abs(L.entry_cost - float(g[('lot','F1',str(p),'entry_cost_2dp')])) < 0.011, f'entry cost mismatch {p}'
        assert abs(L.exit_value - float(g[('lot','F1',str(p),'exit_proceeds_2dp')])) < 0.011, f'exit mismatch {p}'

def test_engine_reproduces_golden_v2_terminal_lot():
    """GE (900005) cash acquisition: terminal cash, NO exit cost — vs Jason's hand-derived value."""
    eng = v2_engine(); g = golden()
    pol = TerminalPolicy(events={900005: {'date': '2020-11-16', 'branch': 'cash_acquisition', 'cash_per_share': 90.0}})
    key = ('lot', 'F2', '900005', 'terminal_cash_2dp')
    if key not in g: return   # only if GE was selected at F2 in Jason's derivation
    L = eng.open_lot('B|F2|900005', 'B', 'F2', 900005, '2020-07-01', 150000.0/3, '2021-01-01')
    eng.close_lot(L, pol)
    assert L.exit_kind == 'TERMINAL_CASH' and L.exit_cost == 0.0
    assert abs(L.exit_value - float(g[key])) < 0.011

def test_core_and_clone_differ_only_by_selection_operator():
    """Same engine, same policy, same calendar: swapping ONLY the selection operator changes
    picks and nothing structural."""
    eng = v2_engine()
    pol = TerminalPolicy()
    forms = [{'formation': 'F1', 'deploy': '2020-04-01', 'scheduled_exit': '2020-10-01',
              'sleeve': 'A', 'alloc_source': 'INITIAL', 'initial_capital': 150000.0}]
    core_lots, _ = run(eng, forms, lambda f: [900001, 900002, 900003], pol, [])
    clone_lots, _ = run(eng, forms, lambda f: [900006, 900007, 900008], pol, [])
    assert [L.permaticker for L in core_lots] != [L.permaticker for L in clone_lots]
    assert {L.sleeve for L in core_lots} == {L.sleeve for L in clone_lots}
    assert all(abs(L.alloc - 50000.0) < 1e-9 for L in core_lots + clone_lots)
    for L in core_lots + clone_lots:
        assert abs(L.shares * L.entry_open * 1.001 - L.alloc) < 1e-6   # cost identity holds for both

def test_terminal_cash_pays_no_exit_cost_but_market_exit_does():
    eng = v2_engine()
    cash = TerminalPolicy(events={900001: {'date': '2020-08-14', 'branch': 'cash_acquisition', 'cash_per_share': 100.0}})
    L1 = eng.open_lot('x', 'A', 'F1', 900001, '2020-04-01', 50000.0, '2020-10-01'); eng.close_lot(L1, cash)
    L2 = eng.open_lot('y', 'A', 'F1', 900001, '2020-04-01', 50000.0, '2020-10-01'); eng.close_lot(L2, TerminalPolicy())
    assert L1.exit_cost == 0.0 and L1.exit_kind == 'TERMINAL_CASH'
    assert L2.exit_cost > 0.0 and L2.exit_kind == 'MARKET_EXIT'

def test_verified_bankruptcy_is_total_loss():
    eng = v2_engine()
    pol = TerminalPolicy(events={900001: {'date': '2020-08-14', 'branch': 'verified_bankruptcy_zero_recovery'}})
    L = eng.open_lot('z', 'A', 'F1', 900001, '2020-04-01', 50000.0, '2020-10-01'); eng.close_lot(L, pol)
    assert L.exit_value == 0.0 and L.exit_cost == 0.0
    assert abs((L.exit_value / L.alloc - 1) - (-1.0)) < 1e-12

def test_successor_conversion_holds_to_scheduled_exit():
    eng = v2_engine()
    pol = TerminalPolicy(events={900001: {'date': '2020-08-14', 'branch': 'stock_acquisition',
                                          'ratio': 0.5, 'successor': 900002}})
    L = eng.open_lot('s', 'A', 'F1', 900001, '2020-04-01', 50000.0, '2020-10-01'); eng.close_lot(L, pol)
    assert L.exit_kind == 'SUCCESSOR_CONVERSION'
    assert abs(L.successor_shares - L.shares * 0.5) < 1e-9
    assert L.exit_date == '2020-10-01' and L.exit_cost > 0.0   # scheduled exit IS a market trade

def test_overlapping_lots_are_independent():
    eng = v2_engine()
    pol = TerminalPolicy()
    a = eng.open_lot('a', 'A', 'F1', 900001, '2020-04-01', 50000.0, '2020-10-01'); eng.close_lot(a, pol)
    b = eng.open_lot('b', 'B', 'F2', 900001, '2020-07-01', 50000.0, '2021-01-01'); eng.close_lot(b, pol)
    assert a.exit_date != b.exit_date and a.shares != b.shares   # same name, independent lots

def test_lineage_records_redeploy_parents():
    eng = v2_engine(); pol = TerminalPolicy()
    forms = [{'formation':'F1','deploy':'2020-04-01','scheduled_exit':'2020-10-01','sleeve':'A','alloc_source':'INITIAL','initial_capital':150000.0},
             {'formation':'F3','deploy':'2020-10-01','scheduled_exit':'2021-04-01','sleeve':'A2','alloc_source':'A'}]
    lots, lineage = run(eng, forms, lambda f: [900001,900002,900003], pol, [])
    a2 = [l for l in lots if l.sleeve == 'A2']
    assert a2 and all(len(l.parent_lot_ids) == 3 for l in a2)   # F3 chains from F1 proceeds
    assert abs(sum(l.alloc for l in a2) - sum(l.exit_value for l in lots if l.sleeve == 'A')) < 1e-6

def test_reconciliation_identity():
    eng = v2_engine(); pol = TerminalPolicy()
    forms = [{'formation':'F1','deploy':'2020-04-01','scheduled_exit':'2020-10-01','sleeve':'A','alloc_source':'INITIAL','initial_capital':150000.0}]
    lots, _ = run(eng, forms, lambda f: [900001,900002,900003], pol, [])
    rec = eng.reconcile(lots, 150000.0)
    assert abs(rec['total_deployed'] - 150000.0) < 1e-6
    assert rec['market_exits'] == 3 and rec['terminal_lots'] == 0

def test_golden_v3_blocked_pending_jason_hand_derivation():
    """G6 discipline: the engine's terminal branches CANNOT be certified until Jason hand-derives
    fixtures/golden_v3_terminal/expected_outputs_SIGNED.csv. This test documents the block."""
    assert not os.path.exists('fixtures/golden_v3_terminal/expected_outputs_SIGNED.csv'), \
        'golden_v3 SIGNED now exists -> replace this test with real branch assertions'
