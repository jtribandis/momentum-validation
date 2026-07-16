"""G9 property-based tests (Hypothesis) on the reference engine's compute().
Random price fixtures on the golden calendar; invariants that must hold for ALL inputs."""
import sys, math
sys.path.insert(0, 'engine')
from momentum_engine_py import compute
from hypothesis import given, settings, strategies as st

ME = ['2019-08-30','2019-09-30','2019-10-31','2019-11-29','2019-12-31','2020-01-31','2020-02-28',
      '2020-03-31','2020-04-30','2020-05-29','2020-06-30','2020-07-31','2020-08-31','2020-09-30',
      '2020-10-30','2020-11-30','2020-12-31','2021-01-29','2021-02-26','2021-03-31','2021-04-30']
OD = ['2020-04-01','2020-07-01','2020-10-01','2021-01-01','2021-04-01']
PREV = {OD[0]: 7, OD[1]: 10, OD[2]: 13, OD[3]: 16, OD[4]: 19}
CFG = {'cost_bps_per_side': '10'}

prices = st.lists(st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
                  min_size=21, max_size=21)

def mk(pxs):
    px = {900000+i+1: dict(zip(ME, v)) for i, v in enumerate(pxs)}
    op = {p: {d: px[p][ME[PREV[d]]] for d in OD} for p in px}
    return px, op

def parse(out):
    d = {}
    for sec, a, b, f, v in out: d[(sec, a, b, f)] = v
    return d

@settings(max_examples=60, deadline=None)
@given(st.lists(prices, min_size=4, max_size=8))
def test_invariants(pxs):
    px, op = mk(pxs)
    out = compute(px, op, {}, CFG)
    d = parse(out)
    # P1: each selection has exactly 3, ordered by signal desc then permaticker asc
    for fdate in ('2020-03-31','2020-06-30','2020-09-30'):
        sel = [int(x) for x in d[('selection', fdate, '', 'top3_permatickers_in_rank_order')].split(',')]
        assert len(sel) == 3 and len(set(sel)) == 3
        sigs = {p: float(d[('signal', fdate, str(p), 'signal_6dp')]) for p in px}
        for i in range(2):
            assert (sigs[sel[i]] > sigs[sel[i+1]]) or (sigs[sel[i]] == sigs[sel[i+1]] and sel[i] < sel[i+1])
        unpicked_max = max((s for p, s in sigs.items() if p not in sel), default=-9e9)
        assert sigs[sel[2]] >= unpicked_max
    # P2/P3: shares identity and cost round-trip on every lot row present
    c = 0.001
    for (sec, fid, p, f), v in list(d.items()):
        if sec == 'lot' and f == 'shares_6dp':
            shares = float(v)
            alloc = 50000.0 if fid in ('F1','F2') else None
            if alloc:
                entry_open = op[int(p)][OD[0] if fid=='F1' else OD[1]]
                assert math.isclose(shares * entry_open * (1+c), alloc, abs_tol=1e-3)  # shares emitted at 6dp: max abs err ~5e-7*open*(1+c)
    # P4: NAV at 2020-03-31 is exactly the undeployed 300k
    assert d[('nav','2020-03-31','','total_nav_2dp')] == '300000.00'
    # P5: permutation invariance — reversed dict insertion order gives identical output
    px2 = dict(reversed(list(px.items()))); op2 = dict(reversed(list(op.items())))
    assert compute(px2, op2, {}, CFG) == out

@settings(max_examples=30, deadline=None)
@given(st.lists(prices, min_size=4, max_size=6), st.floats(min_value=1.0, max_value=500.0))
def test_terminal_invariants(pxs, cash):
    px, op = mk(pxs)
    victim = sorted(px)[0]
    term = {victim: ('2020-11-16', cash)}
    out = compute(px, op, term, CFG)
    d = parse(out)
    # P6: if victim is in F2 or F3 selection, its lot exit is terminal cash = shares*cash
    for fid, dep in (('F2','2020-06-30'), ('F3','2020-09-30')):
        sel = [int(x) for x in d[('selection', dep, '', 'top3_permatickers_in_rank_order')].split(',')]
        if victim in sel:
            sh = float(d[('lot', fid, str(victim), 'shares_6dp')])
            tc = float(d[('lot', fid, str(victim), 'terminal_cash_2dp')])
            assert math.isclose(tc, sh * cash, rel_tol=1e-6, abs_tol=0.011)
