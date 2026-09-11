"""
Stage 2 Database Verification Script.
Checks tables, schema integrity, foreign key constraints, and record counts.
"""

import sys
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "store", "schemes.db")

def verify_database():
    print("=== VERIFYING STAGE 2 SQLITE KNOWLEDGE STORE ===")
    if not os.path.exists(DB_PATH):
        print(f"FAIL: Database file not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Tables check
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cur.fetchall()]
    print(f"  [OK] Found tables: {len(tables)} tables present.")

    # PRAGMA integrity_check
    cur.execute("PRAGMA integrity_check;")
    integrity = cur.fetchall()
    if integrity != [('ok',)]:
        print(f"  [FAIL] PRAGMA integrity_check failed: {integrity}")
        sys.exit(1)
    print("  [OK] PRAGMA integrity_check = ok")

    # PRAGMA foreign_key_check
    cur.execute("PRAGMA foreign_key_check;")
    fk_violations = cur.fetchall()
    if fk_violations:
        print(f"  [FAIL] PRAGMA foreign_key_check violations: {fk_violations}")
        sys.exit(1)
    print("  [OK] PRAGMA foreign_key_check = 0 violations")

    # Expected record counts based on Stage 0/1 data
    cur.execute("SELECT COUNT(*) FROM schemes;")
    scheme_count = cur.fetchone()[0]
    if scheme_count != 29:
        print(f"  [FAIL] Expected 29 schemes, found {scheme_count}")
        sys.exit(1)
    print(f"  [OK] Confirmed {scheme_count} schemes loaded.")

    conn.close()
    print("\n=== STAGE 2 VERIFICATION PASSED ===")

if __name__ == "__main__":
    verify_database()
