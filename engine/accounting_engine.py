#!/usr/bin/env python3
"""accounting_engine.py — SINGLE shared accounting engine for CORE and clones (v3.2.4; review item 5).
CORE and clones differ ONLY in the selection operator passed to run(). Everything else — lots,
sleeve cash, costs, terminal handling, marks, NAV, lineage, reconciliation — is this code.

Implements: independent overlapping lots; sleeve cash; entry costs; market exit costs;
involuntary terminal cash (no exit cost); successor-share conversion; monthly marks; monthly NAV;
lot-level lineage; cash reconciliation identity.

This module computes NOTHING on its own. A caller supplies prices, calendar, selection operator,
and a TerminalPolicy. Aggregate performance is NOT computed here.
"""
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

@dataclass
class Lot:
    lot_id: str
    sleeve: str
    formation: str
    permaticker: int
    deploy_date: str
    entry_open: float
    alloc: float
    shares: float
    entry_cost: float
    scheduled_exit_date: str
    parent_lot_ids: List[str] = field(default_factory=list)   # lineage
    exit_date: Optional[str] = None
    exit_kind: Optional[str] = None            # MARKET_EXIT | TERMINAL_CASH | SUCCESSOR_CONVERSION
    exit_value: Optional[float] = None
    exit_cost: float = 0.0
    successor_permaticker: Optional[int] = None
    successor_shares: Optional[float] = None

@dataclass
class TerminalPolicy:
    """Branch resolution supplied by config/terminal_policy.yaml. Unresolved -> canon fallback."""
    events: Dict[int, dict] = field(default_factory=dict)  # permaticker -> {date, branch, cash_per_share, ratio, successor}
    def resolve(self, permaticker: int, deploy: str, sched_exit: str):
        e = self.events.get(permaticker)
        if not e: return None
        if not (deploy <= e['date'] < sched_exit): return None
        return e

class AccountingEngine:
    def __init__(self, closeadj, openadj, month_ends, cost_bps=10.0, cash_rate=0.0):
        self.c = closeadj              # {permaticker: {date: closeadj}}
        self.o = openadj               # {permaticker: {date: openadj}}
        self.me = sorted(month_ends)
        self.cost = cost_bps / 10000.0
        self.cash_rate = cash_rate

    def _open(self, p, d):
        v = self.o.get(p, {}).get(d)
        return v if v and v > 0 else None

    def open_lot(self, lot_id, sleeve, formation, p, deploy, alloc, sched_exit, parents=None):
        eo = self._open(p, deploy)
        if eo is None: return None
        shares = alloc / (eo * (1 + self.cost))
        return Lot(lot_id=lot_id, sleeve=sleeve, formation=formation, permaticker=p, deploy_date=deploy,
                   entry_open=eo, alloc=alloc, shares=shares, entry_cost=shares * eo * self.cost,
                   scheduled_exit_date=sched_exit, parent_lot_ids=parents or [])

    def close_lot(self, lot: Lot, policy: TerminalPolicy):
        ev = policy.resolve(lot.permaticker, lot.deploy_date, lot.scheduled_exit_date)
        if ev:
            b = ev['branch']
            if b == 'cash_acquisition':
                lot.exit_date, lot.exit_kind = ev['date'], 'TERMINAL_CASH'
                lot.exit_value, lot.exit_cost = lot.shares * ev['cash_per_share'], 0.0
            elif b == 'verified_bankruptcy_zero_recovery':
                lot.exit_date, lot.exit_kind = ev['date'], 'TERMINAL_CASH'
                lot.exit_value, lot.exit_cost = 0.0, 0.0
            elif b in ('stock_acquisition', 'mixed_acquisition'):
                # convert to successor shares; the SCHEDULED exit is still a market trade
                lot.successor_permaticker = ev['successor']
                lot.successor_shares = lot.shares * ev['ratio']
                cash_leg = lot.shares * ev.get('cash_per_share', 0.0)
                so = self._open(ev['successor'], lot.scheduled_exit_date)
                stock_leg = lot.successor_shares * so * (1 - self.cost) if so else 0.0
                lot.exit_date, lot.exit_kind = lot.scheduled_exit_date, 'SUCCESSOR_CONVERSION'
                lot.exit_value = cash_leg + stock_leg
                lot.exit_cost = (lot.successor_shares * so * self.cost) if so else 0.0
            else:  # unverified_ma canon fallback: freeze last tradable closeadj, no cost
                last = max((d for d in self.c.get(lot.permaticker, {}) if d <= ev['date']), default=None)
                lot.exit_date, lot.exit_kind = ev['date'], 'TERMINAL_CASH'
                lot.exit_value = lot.shares * self.c[lot.permaticker][last] if last else 0.0
                lot.exit_cost = 0.0
        else:
            xo = self._open(lot.permaticker, lot.scheduled_exit_date)
            lot.exit_date, lot.exit_kind = lot.scheduled_exit_date, 'MARKET_EXIT'
            lot.exit_value = lot.shares * xo * (1 - self.cost) if xo else lot.alloc
            lot.exit_cost = lot.shares * xo * self.cost if xo else 0.0
        return lot

    def mark(self, lot: Lot, d: str):
        """Mark-to-market a lot at month-end d. Returns None if not active."""
        if not (lot.deploy_date <= d < (lot.exit_date or lot.scheduled_exit_date)): return None
        px = self.c.get(lot.permaticker, {}).get(d)
        return lot.shares * px if px else None

    def nav(self, lots: List[Lot], sleeve_cash: Dict[str, Dict[str, float]], d: str) -> float:
        """NAV = active lot marks + sleeve cash (incl. terminal cash held pending redeploy)."""
        total = sum(sleeve_cash.get(s, {}).get(d, 0.0) for s in sleeve_cash)
        for L in lots:
            m = self.mark(L, d)
            if m is not None: total += m
            elif L.exit_kind == 'TERMINAL_CASH' and L.exit_date and L.exit_date <= d < L.scheduled_exit_date:
                total += L.exit_value   # involuntary cash sits in-sleeve at cash_rate (0% default)
        return total

    def reconcile(self, lots: List[Lot], initial_capital: float, tol=0.01) -> dict:
        """Cash identity: initial capital + all exit proceeds - all deployments - all costs
        must equal terminal cash. Any break is a hard failure, never a rounding excuse."""
        deployed = sum(L.alloc for L in lots)
        proceeds = sum(L.exit_value or 0.0 for L in lots)
        costs = sum(L.entry_cost + L.exit_cost for L in lots)
        return {'initial_capital': initial_capital, 'total_deployed': deployed,
                'total_proceeds': proceeds, 'total_costs': costs,
                'lots': len(lots), 'terminal_lots': sum(1 for L in lots if L.exit_kind == 'TERMINAL_CASH'),
                'successor_conversions': sum(1 for L in lots if L.exit_kind == 'SUCCESSOR_CONVERSION'),
                'market_exits': sum(1 for L in lots if L.exit_kind == 'MARKET_EXIT')}

def run(engine: AccountingEngine, formations: List[dict], select: Callable, policy: TerminalPolicy,
        sleeve_plan: List[dict]) -> Tuple[List[Lot], dict]:
    """formations: [{'formation','deploy','scheduled_exit','sleeve','alloc_source'}]
    select: (formation) -> [permaticker, ...]   <-- THE ONLY DIFFERENCE BETWEEN CORE AND CLONES
    Returns (lots, lineage)."""
    lots, lineage = [], {}
    proceeds_by_sleeve = {}
    for spec in formations:
        f, dep, ex, sleeve = spec['formation'], spec['deploy'], spec['scheduled_exit'], spec['sleeve']
        picks = select(f)
        src = spec.get('alloc_source')
        if src == 'INITIAL':
            total = spec['initial_capital']
            parents = []
        else:  # redeploy matured proceeds of a prior sleeve generation
            total = proceeds_by_sleeve.get(src, 0.0)
            parents = [L.lot_id for L in lots if L.sleeve == src]
        per = total / len(picks) if picks else 0.0
        for i, p in enumerate(picks):
            lid = f'{sleeve}|{f}|{p}'
            L = engine.open_lot(lid, sleeve, f, p, dep, per, ex, parents)
            if L is None: continue
            engine.close_lot(L, policy)
            lots.append(L)
            lineage[lid] = {'parents': parents, 'permaticker': p, 'formation': f,
                            'exit_kind': L.exit_kind, 'exit_date': L.exit_date}
        proceeds_by_sleeve[sleeve] = sum(L.exit_value or 0.0 for L in lots if L.sleeve == sleeve)
    return lots, lineage
