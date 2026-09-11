"""
Stage 2 Database Seeding Script.
Reads verified Stage 1 canonical data and populates SQLite database (store/schemes.db)
with full relational schema, indices, foreign keys, and FTS5 BM25 search indices.
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.load_data import load_data

if __name__ == "__main__":
    print("=== SEEDING SQLITE KNOWLEDGE STORE ===")
    load_data()
    print("Database seeding completed successfully.")
