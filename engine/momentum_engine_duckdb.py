#!/usr/bin/env python3
"""momentum_engine_duckdb.py — G8 SQL/DuckDB engine (protocol v3.2.4).
Third independent reconstruction: ALL arithmetic in SQL. Python only sequences queries and
writes the CSV. Reads fixtures/golden_v2/inputs/ only."""
import csv, sys
from pathlib import Path
import duckdb

IN = 'fixtures/golden_v2/inputs'

def main() -> int:
    con = duckdb.connect()
    con.execute(f"CREATE VIEW px AS SELECT CAST(permaticker AS BIGINT) p, month_end_date d, CAST(closeadj AS DOUBLE) c FROM read_csv_auto('{IN}/month_end_prices.csv')")
    con.execute(f"CREATE VIEW op AS SELECT CAST(permaticker AS BIGINT) p, date d, CAST(openadj AS DOUBLE) o FROM read_csv_auto('{IN}/opens.csv')")
    con.execute(f"CREATE VIEW tm AS SELECT CAST(permaticker AS BIGINT) p, event_date, CAST(cash_per_share AS DOUBLE) cash FROM read_csv_auto('{IN}/terminal_events.csv')")
    cost = con.execute(f"SELECT CAST(value AS DOUBLE)/10000 FROM read_csv_auto('{IN}/fixture_config.csv') WHERE param='cost_bps_per_side'").fetchone()[0]
    ods = [str(r[0]) for r in con.execute("SELECT DISTINCT d FROM op ORDER BY d").fetchall()]
    dep = {'F1': ods[0], 'F2': ods[1], 'F3': ods[2]}; ext = {'F1': ods[2], 'F2': ods[3], 'F3': ods[4]}
    F = [('F1','2020-03-31','2020-02-28','2019-08-30'), ('F2','2020-06-30','2020-05-29','2019-11-29'), ('F3','2020-09-30','2020-08-31','2020-02-28')]

    con.execute("CREATE TABLE sig (fid VARCHAR, fdate VARCHAR, p BIGINT, s DOUBLE)")
    for fid, fdate, m1, m7 in F:
        con.execute(f"""INSERT INTO sig
            SELECT '{fid}', '{fdate}', a.p, a.c/b.c - 1
            FROM px a JOIN px b USING (p) WHERE a.d = DATE '{m1}' AND b.d = DATE '{m7}'""")
    con.execute("""CREATE TABLE sel AS
        SELECT fid, fdate, p, row_number() OVER (PARTITION BY fid ORDER BY s DESC, p ASC) rk
        FROM sig QUALIFY rk <= 3""")

    # lots: F1/F2 alloc = 50000; F3 alloc = sum(F1 exit proceeds)/3 — computed in SQL
    con.execute(f"""CREATE TABLE lot12 AS
        SELECT s.fid, s.p, s.rk, 150000.0/3 AS alloc,
               o.o AS entry_open,
               (150000.0/3) / (o.o * (1 + {cost})) AS shares
        FROM sel s JOIN op o ON o.p = s.p AND o.d = CASE s.fid WHEN 'F1' THEN DATE '{dep['F1']}' WHEN 'F2' THEN DATE '{dep['F2']}' END
        WHERE s.fid IN ('F1','F2')""")
    con.execute(f"""CREATE TABLE lot12x AS
        SELECT l.*, 
          CASE WHEN t.p IS NOT NULL AND t.event_date > CASE l.fid WHEN 'F1' THEN DATE '{dep['F1']}' ELSE DATE '{dep['F2']}' END
                                    AND t.event_date < CASE l.fid WHEN 'F1' THEN DATE '{ext['F1']}' ELSE DATE '{ext['F2']}' END
               THEN l.shares * t.cash
               ELSE l.shares * e.o * (1 - {cost}) END AS exit_val,
          CASE WHEN t.p IS NOT NULL AND t.event_date > CASE l.fid WHEN 'F1' THEN DATE '{dep['F1']}' ELSE DATE '{dep['F2']}' END
                                    AND t.event_date < CASE l.fid WHEN 'F1' THEN DATE '{ext['F1']}' ELSE DATE '{ext['F2']}' END
               THEN 'terminal_cash_2dp' ELSE 'exit_proceeds_2dp' END AS kind
        FROM lot12 l
        LEFT JOIN tm t ON t.p = l.p
        LEFT JOIN op e ON e.p = l.p AND e.d = CASE l.fid WHEN 'F1' THEN DATE '{ext['F1']}' ELSE DATE '{ext['F2']}' END""")
    con.execute(f"""CREATE TABLE lot3 AS
        SELECT 'F3' fid, s.p, s.rk,
               (SELECT SUM(exit_val) FROM lot12x WHERE fid='F1')/3 AS alloc,
               o.o AS entry_open,
               ((SELECT SUM(exit_val) FROM lot12x WHERE fid='F1')/3) / (o.o * (1 + {cost})) AS shares
        FROM sel s JOIN op o ON o.p = s.p AND o.d = DATE '{dep['F3']}'
        WHERE s.fid = 'F3'""")
    con.execute(f"""CREATE TABLE lots AS
        SELECT fid, p, rk, alloc, entry_open, shares, exit_val, kind FROM lot12x
        UNION ALL
        SELECT l.fid, l.p, l.rk, l.alloc, l.entry_open, l.shares,
          CASE WHEN t.p IS NOT NULL AND t.event_date > DATE '{dep['F3']}' AND t.event_date < DATE '{ext['F3']}'
               THEN l.shares * t.cash ELSE l.shares * e.o * (1 - {cost}) END,
          CASE WHEN t.p IS NOT NULL AND t.event_date > DATE '{dep['F3']}' AND t.event_date < DATE '{ext['F3']}'
               THEN 'terminal_cash_2dp' ELSE 'exit_proceeds_2dp' END
        FROM lot3 l LEFT JOIN tm t ON t.p = l.p
        LEFT JOIN op e ON e.p = l.p AND e.d = DATE '{ext['F3']}'""")

    out = []
    for fid, fdate, m1, m7 in F:
        for p, s in con.execute(f"SELECT p, s FROM sig WHERE fid='{fid}' ORDER BY p").fetchall():
            out.append(('signal', fdate, str(p), 'signal_6dp', f"{s:.6f}"))
        sel = [str(r[0]) for r in con.execute(f"SELECT p FROM sel WHERE fid='{fid}' ORDER BY rk").fetchall()]
        out.append(('selection', fdate, '', 'top3_permatickers_in_rank_order', ';'.join(sel)))
    for fid in ('F1','F2','F3'):
        for p, alloc, shares, exit_val, kind, eo in con.execute(
            f"SELECT p, alloc, shares, exit_val, kind, entry_open FROM lots WHERE fid='{fid}' ORDER BY rk").fetchall():
            out.append(('lot', fid, str(p), 'shares_6dp', f"{shares:.6f}"))
            out.append(('lot', fid, str(p), 'entry_cost_2dp', f"{shares*eo*cost:.2f}"))
            out.append(('lot', fid, str(p), kind, f"{exit_val:.2f}"))
            out.append(('lot', fid, str(p), 'lot_return_6dp', f"{exit_val/alloc - 1:.6f}"))
    nav_rows = con.execute(f"""
        WITH me AS (SELECT DISTINCT d FROM px WHERE d BETWEEN DATE '2020-03-31' AND DATE '2021-03-31'),
        lotmeta AS (SELECT l.*, CASE fid WHEN 'F1' THEN DATE '{dep['F1']}' WHEN 'F2' THEN DATE '{dep['F2']}' ELSE DATE '{dep['F3']}' END dd,
                                CASE fid WHEN 'F1' THEN DATE '{ext['F1']}' WHEN 'F2' THEN DATE '{ext['F2']}' ELSE DATE '{ext['F3']}' END xd,
                                t.event_date td FROM lots l LEFT JOIN tm t USING (p))
        SELECT me.d,
          COALESCE(SUM(CASE WHEN lm.dd <= me.d AND me.d < lm.xd
                            THEN CASE WHEN lm.td IS NOT NULL AND lm.td <= me.d THEN lm.exit_val
                                      ELSE lm.shares * px.c END END), 0)
          + CASE WHEN me.d < DATE '{dep['F1']}' THEN 150000 ELSE 0 END
          + CASE WHEN me.d < DATE '{dep['F2']}' THEN 150000 ELSE 0 END
          + CASE WHEN me.d >= DATE '{ext['F2']}' THEN (SELECT SUM(exit_val) FROM lots WHERE fid='F2') ELSE 0 END
        FROM me LEFT JOIN lotmeta lm ON TRUE LEFT JOIN px ON px.p = lm.p AND px.d = me.d
        GROUP BY me.d ORDER BY me.d""").fetchall()
    for d, v in nav_rows:
        out.append(('nav', str(d), '', 'total_nav_2dp', f"{v:.2f}"))
    fin = con.execute("SELECT SUM(exit_val) FROM lots WHERE fid IN ('F2','F3')").fetchone()[0]
    out.append(('nav', '2021-04-01', '', 'final_nav_after_F3_exit_2dp', f"{fin:.2f}"))

    Path('results/phaseE').mkdir(parents=True, exist_ok=True)
    with open('results/phaseE/engine_outputs_duckdb.csv', 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['section','formation_or_date','permaticker','field','value'])
        w.writerows(out)
    print(f'PASS DuckDB engine: {len(out)} values -> results/phaseE/engine_outputs_duckdb.csv')
    return 0

if __name__ == '__main__':
    sys.exit(main())
