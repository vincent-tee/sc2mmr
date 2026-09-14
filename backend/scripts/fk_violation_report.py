"""
READ-ONLY diagnostic: categorize PRAGMA foreign_key_check violations.

Opens the DB in read-only mode (file:...?mode=ro) and NEVER writes.
This is a one-off report tool for the "375 FK violations" investigation —
do not extend it into a repair script.
"""
import sqlite3
import sys
from collections import Counter, defaultdict

DB_PATH = "data/sc2mmr.db"


def connect_ro():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def main():
    conn = connect_ro()
    cur = conn.cursor()

    cur.execute("PRAGMA foreign_key_check;")
    violations = cur.fetchall()
    print(f"Total violations: {len(violations)}\n")

    by_pair = Counter()
    rows_by_pair = defaultdict(list)
    for v in violations:
        by_pair[(v["table"], v["parent"])] += 1
        rows_by_pair[(v["table"], v["parent"])].append((v["rowid"], v["fkid"]))

    print("=== Category counts (table -> parent_table) ===")
    for pair, count in sorted(by_pair.items(), key=lambda x: -x[1]):
        print(f"{count:6d}  {pair[0]:30s} -> {pair[1]}")
    print()

    print("=== FK definitions for involved tables ===")
    tables_involved = set(t for t, p in by_pair.keys())
    for t in tables_involved:
        cur.execute(f"PRAGMA foreign_key_list({t});")
        for fk in cur.fetchall():
            print(f"{t}: fkid={fk['id']} -> {fk['table']}.{fk['to']} (from {t}.{fk['from']}, on_delete={fk['on_delete']})")
    print()

    print("=== Examples per category ===")
    for pair, count in sorted(by_pair.items(), key=lambda x: -x[1]):
        table, parent = pair
        print(f"\n--- {table} -> {parent} (n={count}) ---")
        cur.execute(f"PRAGMA foreign_key_list({table});")
        fk_defs = {fk['id']: fk for fk in cur.fetchall()}
        sample_rowids = rows_by_pair[pair][:5]
        cur.execute(f"PRAGMA table_info({table});")
        cols = [c['name'] for c in cur.fetchall()]
        for rowid, fkid in sample_rowids:
            fk = fk_defs.get(fkid)
            from_col = fk['from'] if fk else '?'
            to_col = fk['to'] if fk else '?'
            try:
                cur.execute(f"SELECT rowid, * FROM {table} WHERE rowid = ?", (rowid,))
                row = cur.fetchone()
                row_dict = dict(row) if row else None
            except Exception as e:
                row_dict = f"ERROR: {e}"
            missing_val = row_dict.get(from_col) if isinstance(row_dict, dict) else None
            print(f"  rowid={rowid} fk_col={from_col} -> {parent}.{to_col} missing_value={missing_val}")
            print(f"    row={row_dict}")
            # check if the missing parent id exists at all anywhere (e.g. was it ever valid)
            if missing_val is not None:
                try:
                    cur.execute(f"SELECT COUNT(*) as c FROM {parent} WHERE {to_col} = ?", (missing_val,))
                    exists = cur.fetchone()['c']
                    print(f"    parent {parent}.{to_col}={missing_val} currently exists: {exists > 0}")
                except Exception as e:
                    print(f"    (could not check parent existence: {e})")

    conn.close()


if __name__ == "__main__":
    main()
