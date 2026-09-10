import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

DB_PATH = "/home/sivaguru/Documents/slm/gov-scheme-qa/store/schemes.db"

def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(db_path: str = DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = get_connection(db_path)
    cur = conn.cursor()

    # 1. Schemes table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS schemes (
        scheme_id TEXT PRIMARY KEY,
        official_name TEXT NOT NULL,
        abbreviation TEXT,
        aliases TEXT, -- JSON array of strings
        category TEXT NOT NULL,
        subcategory TEXT,
        entity_type TEXT DEFAULT 'SCHEME',
        scheme_type TEXT DEFAULT 'CENTRAL_SECTOR',
        objective TEXT,
        description TEXT NOT NULL,
        ministry TEXT NOT NULL,
        department TEXT,
        implementing_agency TEXT,
        geographic_scope TEXT DEFAULT 'NATIONAL',
        status TEXT DEFAULT 'ACTIVE',
        effective_from TEXT,
        effective_until TEXT,
        version TEXT DEFAULT 'current',
        source_pages TEXT, -- JSON array of ints
        source_sections TEXT -- JSON array of strings
    );
    """)

    # 2. Benefits table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS benefits (
        benefit_id TEXT PRIMARY KEY,
        scheme_id TEXT NOT NULL,
        benefit_type TEXT NOT NULL,
        description TEXT NOT NULL,
        beneficiary_count TEXT,
        coverage TEXT,
        quantified_value TEXT,
        method TEXT,
        source_pages TEXT,
        FOREIGN KEY (scheme_id) REFERENCES schemes(scheme_id) ON DELETE CASCADE
    );
    """)

    # 3. Rules table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS rules (
        rule_id TEXT PRIMARY KEY,
        scheme_id TEXT NOT NULL,
        rule_type TEXT DEFAULT 'QUALIFICATION',
        description TEXT NOT NULL,
        operator TEXT DEFAULT 'AND',
        conditions TEXT NOT NULL, -- JSON array of condition objects
        source_pages TEXT,
        FOREIGN KEY (scheme_id) REFERENCES schemes(scheme_id) ON DELETE CASCADE
    );
    """)

    # 4. Exclusions table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exclusions (
        exclusion_id TEXT PRIMARY KEY,
        scheme_id TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        rule_condition TEXT,
        source_pages TEXT,
        FOREIGN KEY (scheme_id) REFERENCES schemes(scheme_id) ON DELETE CASCADE
    );
    """)

    # 5. Documents table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        document_id TEXT PRIMARY KEY,
        scheme_id TEXT NOT NULL,
        mandatory TEXT NOT NULL, -- JSON array of items
        optional TEXT,          -- JSON array of items
        source_pages TEXT,
        FOREIGN KEY (scheme_id) REFERENCES schemes(scheme_id) ON DELETE CASCADE
    );
    """)

    # 6. Procedures table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS procedures (
        procedure_id TEXT PRIMARY KEY,
        scheme_id TEXT NOT NULL,
        mode TEXT NOT NULL,
        online_steps TEXT,  -- JSON array
        offline_steps TEXT, -- JSON array
        processing_time TEXT,
        fees TEXT,
        source_pages TEXT,
        FOREIGN KEY (scheme_id) REFERENCES schemes(scheme_id) ON DELETE CASCADE
    );
    """)

    # 7. FAQs table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS faqs (
        faq_id TEXT PRIMARY KEY,
        scheme_id TEXT NOT NULL,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        source_pages TEXT,
        FOREIGN KEY (scheme_id) REFERENCES schemes(scheme_id) ON DELETE CASCADE
    );
    """)

    # 8. Authorities table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS authorities (
        authority_id TEXT PRIMARY KEY,
        scheme_id TEXT NOT NULL,
        ministry TEXT NOT NULL,
        department TEXT,
        implementing_agency TEXT,
        portal_url TEXT,
        helpline TEXT,
        grievance_redressal TEXT,
        source_pages TEXT,
        FOREIGN KEY (scheme_id) REFERENCES schemes(scheme_id) ON DELETE CASCADE
    );
    """)

    # 9. Relationships table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS relationships (
        relationship_id TEXT PRIMARY KEY,
        source_scheme_id TEXT NOT NULL,
        target_scheme_id TEXT NOT NULL,
        relationship_type TEXT NOT NULL,
        description TEXT NOT NULL,
        shared_fields TEXT,
        FOREIGN KEY (source_scheme_id) REFERENCES schemes(scheme_id) ON DELETE CASCADE
    );
    """)

    # 10. FTS5 Virtual Table for BM25 Search
    cur.execute("DROP TABLE IF EXISTS fts_schemes_content;")
    cur.execute("""
    CREATE VIRTUAL TABLE fts_schemes_content USING fts5(
        scheme_id UNINDEXED,
        scheme_name,
        abbreviation,
        section,
        content,
        source_pages UNINDEXED,
        tokenize = 'porter unicode61'
    );
    """)

    conn.commit()
    conn.close()

class SchemeRepository:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def get_scheme_by_id(self, scheme_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM schemes WHERE scheme_id = ?", (scheme_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            d = dict(row)
            d["aliases"] = json.loads(d["aliases"]) if d.get("aliases") else []
            d["source_pages"] = json.loads(d["source_pages"]) if d.get("source_pages") else []
            d["source_sections"] = json.loads(d["source_sections"]) if d.get("source_sections") else []
            return d
        return None

    def get_all_schemes(self) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM schemes ORDER BY official_name")
        rows = cur.fetchall()
        conn.close()
        results = []
        for r in rows:
            d = dict(r)
            d["aliases"] = json.loads(d["aliases"]) if d.get("aliases") else []
            d["source_pages"] = json.loads(d["source_pages"]) if d.get("source_pages") else []
            results.append(d)
        return results

    def get_benefits_for_scheme(self, scheme_id: str) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM benefits WHERE scheme_id = ?", (scheme_id,))
        rows = cur.fetchall()
        conn.close()
        res = []
        for r in rows:
            d = dict(r)
            d["source_pages"] = json.loads(d["source_pages"]) if d.get("source_pages") else []
            res.append(d)
        return res

    def get_rules_for_scheme(self, scheme_id: str) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM rules WHERE scheme_id = ?", (scheme_id,))
        rows = cur.fetchall()
        conn.close()
        res = []
        for r in rows:
            d = dict(r)
            d["conditions"] = json.loads(d["conditions"]) if d.get("conditions") else []
            d["source_pages"] = json.loads(d["source_pages"]) if d.get("source_pages") else []
            res.append(d)
        return res

    def get_exclusions_for_scheme(self, scheme_id: str) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM exclusions WHERE scheme_id = ?", (scheme_id,))
        rows = cur.fetchall()
        conn.close()
        res = []
        for r in rows:
            d = dict(r)
            d["source_pages"] = json.loads(d["source_pages"]) if d.get("source_pages") else []
            res.append(d)
        return res

    def get_documents_for_scheme(self, scheme_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM documents WHERE scheme_id = ?", (scheme_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            d = dict(row)
            d["mandatory"] = json.loads(d["mandatory"]) if d.get("mandatory") else []
            d["optional"] = json.loads(d["optional"]) if d.get("optional") else []
            d["source_pages"] = json.loads(d["source_pages"]) if d.get("source_pages") else []
            return d
        return None

    def get_procedure_for_scheme(self, scheme_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM procedures WHERE scheme_id = ?", (scheme_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            d = dict(row)
            d["online_steps"] = json.loads(d["online_steps"]) if d.get("online_steps") else []
            d["offline_steps"] = json.loads(d["offline_steps"]) if d.get("offline_steps") else []
            d["source_pages"] = json.loads(d["source_pages"]) if d.get("source_pages") else []
            return d
        return None

    def get_faqs_for_scheme(self, scheme_id: str) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM faqs WHERE scheme_id = ?", (scheme_id,))
        rows = cur.fetchall()
        conn.close()
        res = []
        for r in rows:
            d = dict(r)
            d["source_pages"] = json.loads(d["source_pages"]) if d.get("source_pages") else []
            res.append(d)
        return res

    def get_authority_for_scheme(self, scheme_id: str) -> Optional[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM authorities WHERE scheme_id = ?", (scheme_id,))
        row = cur.fetchone()
        conn.close()
        if row:
            d = dict(row)
            d["source_pages"] = json.loads(d["source_pages"]) if d.get("source_pages") else []
            return d
        return None

    def search_bm25(self, query: str, scheme_id: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Perform BM25 full-text search against the indexed FTS5 table.
        Safe query sanitizer removes punctuation that breaks FTS5 query syntax.
        """
        clean_tokens = [w for w in "".join([c if c.isalnum() else " " for c in query]).split() if len(w) > 2]
        if not clean_tokens:
            return []

        fts_query = " OR ".join(clean_tokens)

        conn = get_connection(self.db_path)
        cur = conn.cursor()

        if scheme_id:
            sql = """
            SELECT scheme_id, scheme_name, abbreviation, section, content, source_pages, bm25(fts_schemes_content) as score
            FROM fts_schemes_content
            WHERE fts_schemes_content MATCH ? AND scheme_id = ?
            ORDER BY score
            LIMIT ?
            """
            cur.execute(sql, (fts_query, scheme_id, limit))
        else:
            sql = """
            SELECT scheme_id, scheme_name, abbreviation, section, content, source_pages, bm25(fts_schemes_content) as score
            FROM fts_schemes_content
            WHERE fts_schemes_content MATCH ?
            ORDER BY score
            LIMIT ?
            """
            cur.execute(sql, (fts_query, limit))

        rows = cur.fetchall()
        conn.close()

        results = []
        for r in rows:
            d = dict(r)
            d["source_pages"] = json.loads(d["source_pages"]) if d.get("source_pages") else []
            results.append(d)
        return results
