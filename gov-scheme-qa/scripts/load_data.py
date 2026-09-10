"""
Ingests canonical JSON data into SQLite database and builds FTS5 BM25 search indices.
"""

import os
import json
import sqlite3
from store.database import DB_PATH, init_db, get_connection

DATA_DIR = "/home/sivaguru/Documents/slm/gov-scheme-qa/data"

def load_data():
    print("Initializing database tables...")
    init_db(DB_PATH)
    conn = get_connection(DB_PATH)
    cur = conn.cursor()

    # 1. Load Schemes
    with open(f"{DATA_DIR}/schemes/all_schemes.json") as f:
        schemes = json.load(f)

    for s in schemes:
        cur.execute("""
        INSERT INTO schemes (
            scheme_id, official_name, abbreviation, aliases, category, subcategory,
            entity_type, scheme_type, objective, description, ministry, department,
            implementing_agency, geographic_scope, status, effective_from, effective_until,
            version, source_pages, source_sections
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            s["scheme_id"],
            s["official_name"],
            s.get("abbreviation"),
            json.dumps(s.get("aliases", [])),
            s["category"],
            s.get("subcategory"),
            s.get("entity_type", "SCHEME"),
            s.get("scheme_type", "CENTRAL_SECTOR"),
            s.get("objective"),
            s["description"],
            s["ministry"],
            s.get("department"),
            s.get("implementing_agency"),
            s.get("geographic_scope", "NATIONAL"),
            s.get("status", "ACTIVE"),
            s.get("effective_from"),
            s.get("effective_until"),
            s.get("version", "current"),
            json.dumps(s.get("source_pages", [])),
            json.dumps(s.get("source_sections", []))
        ))

        # Index overview into FTS5
        content = f"{s['official_name']} {s.get('abbreviation','')} {s.get('category','')} {s.get('description','')} {s.get('objective','')}"
        cur.execute("""
        INSERT INTO fts_schemes_content (scheme_id, scheme_name, abbreviation, section, content, source_pages)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            s["scheme_id"],
            s["official_name"],
            s.get("abbreviation", ""),
            "OVERVIEW",
            content,
            json.dumps(s.get("source_pages", []))
        ))

    print(f"Loaded {len(schemes)} schemes.")

    # 2. Load Benefits
    with open(f"{DATA_DIR}/benefits/all_benefits.json") as f:
        benefits = json.load(f)

    for b in benefits:
        cur.execute("""
        INSERT INTO benefits (
            benefit_id, scheme_id, benefit_type, description, beneficiary_count, coverage, quantified_value, method, source_pages
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            b["benefit_id"],
            b["scheme_id"],
            b.get("benefit_type", "GENERAL"),
            b["description"],
            b.get("beneficiary_count"),
            b.get("coverage"),
            b.get("quantified_value"),
            b.get("method"),
            json.dumps(b.get("source_pages", []))
        ))

        cur.execute("""
        INSERT INTO fts_schemes_content (scheme_id, scheme_name, abbreviation, section, content, source_pages)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            b["scheme_id"],
            "",
            "",
            "BENEFITS",
            f"{b.get('benefit_type','')} {b['description']} {b.get('quantified_value','')}",
            json.dumps(b.get("source_pages", []))
        ))
    print(f"Loaded {len(benefits)} benefits.")

    # 3. Load Rules
    with open(f"{DATA_DIR}/rules/all_rules.json") as f:
        rules = json.load(f)

    for r in rules:
        cur.execute("""
        INSERT INTO rules (
            rule_id, scheme_id, rule_type, description, operator, conditions, source_pages
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            r["rule_id"],
            r["scheme_id"],
            r.get("rule_type", "QUALIFICATION"),
            r["description"],
            r.get("operator", "AND"),
            json.dumps(r.get("conditions", [])),
            json.dumps(r.get("source_pages", []))
        ))

        cond_text = " ".join([c.get("description", "") for c in r.get("conditions", [])])
        cur.execute("""
        INSERT INTO fts_schemes_content (scheme_id, scheme_name, abbreviation, section, content, source_pages)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            r["scheme_id"],
            "",
            "",
            "ELIGIBILITY",
            f"{r['description']} {cond_text}",
            json.dumps(r.get("source_pages", []))
        ))
    print(f"Loaded {len(rules)} rules.")

    # 4. Load Exclusions
    with open(f"{DATA_DIR}/exclusions/all_exclusions.json") as f:
        exclusions = json.load(f)

    for e in exclusions:
        cur.execute("""
        INSERT INTO exclusions (
            exclusion_id, scheme_id, category, description, rule_condition, source_pages
        ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            e["exclusion_id"],
            e["scheme_id"],
            e["category"],
            e["description"],
            e.get("rule_condition"),
            json.dumps(e.get("source_pages", []))
        ))

        cur.execute("""
        INSERT INTO fts_schemes_content (scheme_id, scheme_name, abbreviation, section, content, source_pages)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            e["scheme_id"],
            "",
            "",
            "EXCLUSIONS",
            f"{e['category']} {e['description']}",
            json.dumps(e.get("source_pages", []))
        ))
    print(f"Loaded {len(exclusions)} exclusions.")

    # 5. Load Documents
    with open(f"{DATA_DIR}/documents/all_documents.json") as f:
        docs = json.load(f)

    for d in docs:
        cur.execute("""
        INSERT INTO documents (
            document_id, scheme_id, mandatory, optional, source_pages
        ) VALUES (?, ?, ?, ?, ?)
        """, (
            d["document_id"],
            d["scheme_id"],
            json.dumps(d.get("mandatory", [])),
            json.dumps(d.get("optional", [])),
            json.dumps(d.get("source_pages", []))
        ))

        doc_names = " ".join([m["name"] for m in d.get("mandatory", [])] + [o["name"] for o in d.get("optional", [])])
        cur.execute("""
        INSERT INTO fts_schemes_content (scheme_id, scheme_name, abbreviation, section, content, source_pages)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            d["scheme_id"],
            "",
            "",
            "DOCUMENTS",
            f"Documents required: {doc_names}",
            json.dumps(d.get("source_pages", []))
        ))
    print(f"Loaded {len(docs)} document sets.")

    # 6. Load Procedures
    with open(f"{DATA_DIR}/procedures/all_procedures.json") as f:
        procs = json.load(f)

    for p in procs:
        cur.execute("""
        INSERT INTO procedures (
            procedure_id, scheme_id, mode, online_steps, offline_steps, processing_time, fees, source_pages
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["procedure_id"],
            p["scheme_id"],
            p["mode"],
            json.dumps(p.get("online_steps", [])),
            json.dumps(p.get("offline_steps", [])),
            p.get("processing_time"),
            p.get("fees"),
            json.dumps(p.get("source_pages", []))
        ))

        proc_text = " ".join(p.get("online_steps", []) + p.get("offline_steps", []))
        cur.execute("""
        INSERT INTO fts_schemes_content (scheme_id, scheme_name, abbreviation, section, content, source_pages)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            p["scheme_id"],
            "",
            "",
            "PROCEDURE",
            f"How to apply process: {proc_text}",
            json.dumps(p.get("source_pages", []))
        ))
    print(f"Loaded {len(procs)} procedures.")

    # 7. Load FAQs
    with open(f"{DATA_DIR}/faqs/all_faqs.json") as f:
        faqs = json.load(f)

    for q in faqs:
        cur.execute("""
        INSERT INTO faqs (
            faq_id, scheme_id, question, answer, source_pages
        ) VALUES (?, ?, ?, ?, ?)
        """, (
            q["faq_id"],
            q["scheme_id"],
            q["question"],
            q["answer"],
            json.dumps(q.get("source_pages", []))
        ))

        cur.execute("""
        INSERT INTO fts_schemes_content (scheme_id, scheme_name, abbreviation, section, content, source_pages)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            q["scheme_id"],
            "",
            "",
            "FAQ",
            f"{q['question']} {q['answer']}",
            json.dumps(q.get("source_pages", []))
        ))
    print(f"Loaded {len(faqs)} FAQs.")

    # 8. Load Authorities
    with open(f"{DATA_DIR}/authorities/all_authorities.json") as f:
        auths = json.load(f)

    for a in auths:
        cur.execute("""
        INSERT INTO authorities (
            authority_id, scheme_id, ministry, department, implementing_agency, portal_url, helpline, grievance_redressal, source_pages
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            a["authority_id"],
            a["scheme_id"],
            a["ministry"],
            a.get("department"),
            a.get("implementing_agency"),
            a.get("portal_url"),
            a.get("helpline"),
            a.get("grievance_redressal"),
            json.dumps(a.get("source_pages", []))
        ))
    print(f"Loaded {len(auths)} authorities.")

    # 9. Load Relationships
    with open(f"{DATA_DIR}/relationships/all_relationships.json") as f:
        rels = json.load(f)

    for r in rels:
        cur.execute("""
        INSERT INTO relationships (
            relationship_id, source_scheme_id, target_scheme_id, relationship_type, description, shared_fields
        ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            r["relationship_id"],
            r["source_scheme_id"],
            r["target_scheme_id"],
            r["relationship_type"],
            r["description"],
            json.dumps(r.get("shared_fields", []))
        ))
    print(f"Loaded {len(rels)} relationships.")

    conn.commit()
    conn.close()
    print("Database initialization and FTS5 indexing complete!")

if __name__ == "__main__":
    load_data()
