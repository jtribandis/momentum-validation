"""Vendor-semantics regression tests for terminal classification (v3.2.4).
Every mapping below is asserted directly against the archived vendor text
(evidence/vendor_semantics/..., sha256 52ef6da7...)."""
import sys, json, hashlib, datetime
sys.path.insert(0, 'build')
from build_terminal_events import classify, TERMINAL_ACTIONS, NON_TERMINAL

D = datetime.date(2020, 6, 1)

def test_vendor_file_integrity():
    h = hashlib.sha256(open('evidence/vendor_semantics/SHARADAR_INDICATORS_ACTIONS_ACTIONTYPES_20260716.csv','rb').read()).hexdigest()
    assert h == '52ef6da79c66bdee51e25b882185787ea44dfbe2dc67a66cc2d4e5e949d4b420'

def test_acquisitionby_is_terminal():
    # vendor: "The ticker field represents the ticker of the acquired company"
    assert classify([('acquisitionby', D)]) == ('ACQUIRED', D)

def test_acquisitionof_is_NOT_terminal():
    # vendor: "The ticker field represents the ticker of the acquiring company"
    assert classify([('acquisitionof', D)]) == (None, None)
    assert 'acquisitionof' in NON_TERMINAL

def test_REGRESSION_mergerto_was_wrong_now_nonterminal():
    """DEFECT F-016: the pre-2026-07-16 engine mapped mergerto -> terminal 'MERGER'.
    Vendor: mergerto.ticker = SURVIVING company -> the lot does NOT terminate.
    This test fails against the old code and passes against the corrected code."""
    assert classify([('mergerto', D)]) == (None, None), 'mergerto must NOT be terminal (ticker = survivor)'
    assert 'mergerto' in NON_TERMINAL
    assert 'mergerto' not in TERMINAL_ACTIONS

def test_REGRESSION_mergerfrom_now_terminal():
    # vendor: mergerfrom.ticker = NON-SURVIVING company -> terminal
    assert classify([('mergerfrom', D)]) == ('MERGER_NONSURVIVOR', D)

def test_relation_not_terminal_not_identity():
    assert classify([('relation', D)]) == (None, None)
    assert 'relation' in NON_TERMINAL

def test_ticker_changes_are_identity_continuation_not_terminal():
    assert classify([('tickerchangefrom', D)]) == (None, None)
    assert classify([('tickerchangeto', D)]) == (None, None)

def test_all_delisting_flavors_terminal():
    for a, exp in (('delisted','DELISTED_OTHER'), ('regulatorydelisting','REGULATORY_DELISTING'),
                   ('voluntarydelisting','VOLUNTARY_DELISTING'), ('bankruptcyliquidation','BANKRUPTCY_LIQUIDATION')):
        assert classify([(a, D)]) == (exp, D)

def test_split_and_dividend_never_terminal():
    assert classify([('split', D)]) == (None, None)
    assert classify([('dividend', D)]) == (None, None)

def test_mirror_row_dedup_keeps_terminating_entity():
    # a paired merger emits mergerfrom (non-survivor) + mergerto (survivor); only one terminates
    assert classify([('mergerto', D), ('mergerfrom', D)]) == ('MERGER_NONSURVIVOR', D)
    assert classify([('acquisitionof', D), ('acquisitionby', D)]) == ('ACQUIRED', D)

def test_bankruptcy_priority_over_delisting():
    assert classify([('delisted', D), ('bankruptcyliquidation', D)]) == ('BANKRUPTCY_LIQUIDATION', D)

def test_value_never_used_as_proceeds():
    sem = json.load(open('results/phaseB/terminal_event_semantics.json'))
    assert 'never per-share proceeds' in sem['BINDING_PROHIBITION']
    for a in ('acquisitionby','mergerfrom','bankruptcyliquidation'):
        assert 'market cap' in sem['binding_semantics_VERIFIED_AGAINST_VENDOR_TEXT'][a]['value']
