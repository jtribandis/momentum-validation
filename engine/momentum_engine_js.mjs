#!/usr/bin/env node
// momentum_engine_js.mjs — G8 JavaScript engine (protocol v3.2.4).
// Independent reconstruction: reads fixtures/golden_v2/inputs/ only, writes engine_outputs_js.csv.
import { readFileSync, writeFileSync, mkdirSync } from 'fs';

function csv(path) {
  const [h, ...rows] = readFileSync(path, 'utf8').trim().split(/\r?\n/).map(l => l.split(','));
  return rows.map(r => Object.fromEntries(h.map((k, i) => [k, r[i]])));
}
const IN = 'fixtures/golden_v2/inputs/';
const px = {}, op = {};
for (const r of csv(IN + 'month_end_prices.csv')) {
  (px[r.permaticker] ??= {})[r.month_end_date] = parseFloat(r.closeadj);
}
for (const r of csv(IN + 'opens.csv')) {
  (op[r.permaticker] ??= {})[r.date] = parseFloat(r.openadj);
}
const term = {};
for (const r of csv(IN + 'terminal_events.csv')) term[r.permaticker] = [r.event_date, parseFloat(r.cash_per_share)];
const cfg = Object.fromEntries(csv(IN + 'fixture_config.csv').map(r => [r.param, r.value]));
const COST = parseFloat(cfg.cost_bps_per_side) / 10000;

const perms = Object.keys(px).sort();
const openDates = [...new Set(Object.values(op).flatMap(o => Object.keys(o)))].sort();
const dep = { F1: openDates[0], F2: openDates[1], F3: openDates[2] };
const ext = { F1: openDates[2], F2: openDates[3], F3: openDates[4] };
const F = [['F1','2020-03-31','2020-02-28','2019-08-30'], ['F2','2020-06-30','2020-05-29','2019-11-29'], ['F3','2020-09-30','2020-08-31','2020-02-28']];

const out = [], top3 = {};
for (const [fid, fdate, m1, m7] of F) {
  const sig = {};
  for (const p of perms) if (px[p][m1] !== undefined && px[p][m7] !== undefined) sig[p] = px[p][m1] / px[p][m7] - 1;
  const ranked = Object.keys(sig).sort((a, b) => (sig[b] - sig[a]) || (parseInt(a) - parseInt(b)));
  top3[fid] = ranked.slice(0, 3);
  for (const p of perms) out.push(['signal', fdate, p, 'signal_6dp', sig[p].toFixed(6)]);
  out.push(['selection', fdate, '', 'top3_permatickers_in_rank_order', top3[fid].join(';')]);
}
const lots = {};
let f1Proceeds = 0;
for (const fid of ['F1', 'F2', 'F3']) {
  const alloc = fid === 'F3' ? f1Proceeds / 3 : 150000 / 3;
  for (const p of top3[fid]) {
    const o = op[p][dep[fid]];
    const shares = alloc / (o * (1 + COST));
    const entryCost = shares * o * COST;
    let exitVal, kind;
    if (term[p] && term[p][0] > dep[fid] && term[p][0] < ext[fid]) { exitVal = shares * term[p][1]; kind = 'terminal_cash_2dp'; }
    else { exitVal = shares * op[p][ext[fid]] * (1 - COST); kind = 'exit_proceeds_2dp'; }
    lots[fid + '|' + p] = { shares, entryCost, exitVal, kind, dep: dep[fid], ext: ext[fid], perm: p, fid };
    if (fid === 'F1') f1Proceeds += exitVal;
  }
}
for (const fid of ['F1', 'F2', 'F3']) for (const p of top3[fid]) {
  const L = lots[fid + '|' + p];
  const alloc = fid === 'F3' ? f1Proceeds / 3 : 150000 / 3;
  out.push(['lot', fid, p, 'shares_6dp', L.shares.toFixed(6)]);
  out.push(['lot', fid, p, 'entry_cost_2dp', L.entryCost.toFixed(2)]);
  out.push(['lot', fid, p, L.kind, L.exitVal.toFixed(2)]);
  out.push(['lot', fid, p, 'lot_return_6dp', (L.exitVal / alloc - 1).toFixed(6)]);
}
const meDates = [...new Set(Object.values(px).flatMap(o => Object.keys(o)))].sort()
  .filter(d => d >= '2020-03-31' && d <= '2021-03-31');
for (const d of meDates) {
  let nav = 0;
  if (d < dep.F1) nav += 150000;
  if (d < dep.F2) nav += 150000;
  for (const L of Object.values(lots)) {
    if (!(L.dep <= d && d < L.ext)) continue;
    nav += (term[L.perm] && term[L.perm][0] <= d) ? L.exitVal : L.shares * px[L.perm][d];
  }
  if (ext.F2 <= d) for (const L of Object.values(lots)) if (L.fid === 'F2') nav += L.exitVal;
  out.push(['nav', d, '', 'total_nav_2dp', nav.toFixed(2)]);
}
let fin = 0;
for (const L of Object.values(lots)) if (L.fid === 'F2' || L.fid === 'F3') fin += L.exitVal;
out.push(['nav', '2021-04-01', '', 'final_nav_after_F3_exit_2dp', fin.toFixed(2)]);

mkdirSync('results/phaseE', { recursive: true });
writeFileSync('results/phaseE/engine_outputs_js.csv',
  'section,formation_or_date,permaticker,field,value\n' + out.map(r => r.join(',')).join('\n') + '\n');
console.log(`PASS JS engine: ${out.length} values -> results/phaseE/engine_outputs_js.csv`);
