import os
import sys
import json
import sqlite3
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from store.database import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def update_scheme_overview(scheme_data: Dict[str, Any]) -> bool:
    """Validate and upsert scheme overview."""
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO schemes (
                scheme_id, official_name, abbreviation, aliases, category,
                subcategory, entity_type, scheme_type, objective, description,
                ministry, department, implementing_agency, geographic_scope,
                status, effective_from, effective_until, version, source_pages, source_sections
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scheme_id) DO UPDATE SET
                official_name=excluded.official_name,
                abbreviation=excluded.abbreviation,
                aliases=excluded.aliases,
                category=excluded.category,
                subcategory=excluded.subcategory,
                entity_type=excluded.entity_type,
                scheme_type=excluded.scheme_type,
                objective=excluded.objective,
                description=excluded.description,
                ministry=excluded.ministry,
                department=excluded.department,
                implementing_agency=excluded.implementing_agency,
                geographic_scope=excluded.geographic_scope,
                status=excluded.status,
                effective_from=excluded.effective_from,
                effective_until=excluded.effective_until,
                version=excluded.version,
                source_pages=excluded.source_pages,
                source_sections=excluded.source_sections
        """, (
            scheme_data["scheme_id"],
            scheme_data["official_name"],
            scheme_data.get("abbreviation"),
            json.dumps(scheme_data.get("aliases", [])),
            scheme_data.get("category", "General"),
            scheme_data.get("subcategory"),
            scheme_data.get("entity_type", "SCHEME"),
            scheme_data.get("scheme_type", "CENTRAL_SECTOR"),
            scheme_data.get("objective", ""),
            scheme_data["description"],
            scheme_data.get("ministry", ""),
            scheme_data.get("department"),
            scheme_data.get("implementing_agency"),
            scheme_data.get("geographic_scope", "NATIONAL"),
            scheme_data.get("status", "ACTIVE"),
            scheme_data.get("effective_from"),
            scheme_data.get("effective_until"),
            scheme_data.get("version", "current"),
            json.dumps(scheme_data.get("source_pages", [])),
            json.dumps(scheme_data.get("source_sections", []))
        ))
        conn.commit()
        return True
    finally:
        conn.close()

def upsert_benefit(benefit_data: Dict[str, Any]) -> bool:
    """Validate and upsert a benefit item."""
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO benefits (
                benefit_id, scheme_id, benefit_type, description,
                beneficiary_count, coverage, quantified_value, method, source_pages
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(benefit_id) DO UPDATE SET
                scheme_id=excluded.scheme_id,
                benefit_type=excluded.benefit_type,
                description=excluded.description,
                beneficiary_count=excluded.beneficiary_count,
                coverage=excluded.coverage,
                quantified_value=excluded.quantified_value,
                method=excluded.method,
                source_pages=excluded.source_pages
        """, (
            benefit_data["benefit_id"],
            benefit_data["scheme_id"],
            benefit_data["benefit_type"],
            benefit_data["description"],
            benefit_data.get("beneficiary_count"),
            benefit_data.get("coverage"),
            benefit_data.get("quantified_value"),
            benefit_data.get("method"),
            json.dumps(benefit_data.get("source_pages", []))
        ))
        conn.commit()
        return True
    finally:
        conn.close()

def upsert_rule(rule_data: Dict[str, Any]) -> bool:
    """Validate and upsert an eligibility/exclusion rule."""
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO rules (
                rule_id, scheme_id, rule_type, description,
                operator, conditions, source_pages
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(rule_id) DO UPDATE SET
                scheme_id=excluded.scheme_id,
                rule_type=excluded.rule_type,
                description=excluded.description,
                operator=excluded.operator,
                conditions=excluded.conditions,
                source_pages=excluded.source_pages
        """, (
            rule_data["rule_id"],
            rule_data["scheme_id"],
            rule_data.get("rule_type", "QUALIFICATION"),
            rule_data["description"],
            rule_data.get("operator", "AND"),
            json.dumps(rule_data.get("conditions", [])),
            json.dumps(rule_data.get("source_pages", []))
        ))
        conn.commit()
        return True
    finally:
        conn.close()

def upsert_document_set(doc_data: Dict[str, Any]) -> bool:
    """Validate and upsert a document requirement set."""
    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO documents (
                document_id, scheme_id, mandatory,
                optional, source_pages
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(document_id) DO UPDATE SET
                scheme_id=excluded.scheme_id,
                mandatory=excluded.mandatory,
                optional=excluded.optional,
                source_pages=excluded.source_pages
        """, (
            doc_data["document_id"],
            doc_data["scheme_id"],
            json.dumps(doc_data.get("mandatory", [])),
            json.dumps(doc_data.get("optional", [])),
            json.dumps(doc_data.get("source_pages", []))
        ))
        conn.commit()
        return True
    finally:
        conn.close()

def rebuild_fts5_index():
    """Sync FTS5 index with schemes table."""
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM fts_schemes_content WHERE section = 'OVERVIEW';")
        cur = conn.cursor()
        cur.execute("SELECT scheme_id, official_name, abbreviation, category, description, objective, source_pages FROM schemes;")
        schemes = cur.fetchall()
        for s in schemes:
            scheme_id, official_name, abbreviation, category, description, objective, source_pages = s
            content = f"{official_name} {abbreviation or ''} {category or ''} {description or ''} {objective or ''}"
            conn.execute("""
                INSERT INTO fts_schemes_content (scheme_id, scheme_name, abbreviation, section, content, source_pages)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (scheme_id, official_name, abbreviation or "", "OVERVIEW", content, source_pages or "[]"))
        conn.commit()
        return True
    finally:
        conn.close()

if __name__ == "__main__":
    print("Rebuilding FTS5 search index...")
    rebuild_fts5_index()
    print("FTS5 index successfully rebuilt and synchronized.")
