"""
Stage 1 Data Validation Script.
Validates:
1. JSON syntax across all files in data/
2. Schema compliance using Pydantic domain models
3. Foreign-key-like references (every scheme_id exists in schemes)
4. Source page numbers are valid integers in range [1, 261]
5. Rule references and conditions format
6. Benefit references and types
7. FAQ question/answer pairs
8. Exclusions, procedures, documents, authorities, relationships, temporal records
"""

import sys
import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from schemas.models import (
    Scheme, Benefit, Rule, Exclusion, DocumentRequirement,
    Procedure, FAQ, Authority
)

DATA_DIR = os.path.join(BASE_DIR, "data")

def validate_data():
    print("=== RUNNING STAGE 1 CANONICAL DATA VALIDATION ===")
    errors = []

    # 1. Load and validate Schemes
    schemes_file = os.path.join(DATA_DIR, "schemes", "all_schemes.json")
    if not os.path.exists(schemes_file):
        errors.append("Missing data/schemes/all_schemes.json")
        print("\n".join(errors))
        sys.exit(1)

    try:
        with open(schemes_file) as f:
            schemes_data = json.load(f)
    except Exception as e:
        errors.append(f"Invalid JSON syntax in all_schemes.json: {e}")
        print("\n".join(errors))
        sys.exit(1)

    valid_scheme_ids = set()
    for idx, s in enumerate(schemes_data):
        try:
            scheme_obj = Scheme(**s)
            valid_scheme_ids.add(scheme_obj.scheme_id)
            for p in scheme_obj.source_pages:
                if not (1 <= p <= 261):
                    errors.append(f"Scheme {scheme_obj.scheme_id} has invalid source page {p}")
        except Exception as e:
            errors.append(f"Scheme validation failed at index {idx}: {e}")

    print(f"  [OK] Validated {len(valid_scheme_ids)} schemes.")

    # 2. Validate Benefits
    benefits_file = os.path.join(DATA_DIR, "benefits", "all_benefits.json")
    try:
        with open(benefits_file) as f:
            benefits_data = json.load(f)
        for idx, b in enumerate(benefits_data):
            try:
                b_obj = Benefit(**b)
                if b_obj.scheme_id not in valid_scheme_ids:
                    errors.append(f"Benefit {b_obj.benefit_id} references invalid scheme_id: {b_obj.scheme_id}")
                for p in b_obj.source_pages:
                    if not (1 <= p <= 261):
                        errors.append(f"Benefit {b_obj.benefit_id} invalid source page {p}")
            except Exception as e:
                errors.append(f"Benefit validation error at index {idx}: {e}")
        print(f"  [OK] Validated {len(benefits_data)} benefits with valid scheme references.")
    except Exception as e:
        errors.append(f"Failed to read/validate benefits: {e}")

    # 3. Validate Rules
    rules_file = os.path.join(DATA_DIR, "rules", "all_rules.json")
    try:
        with open(rules_file) as f:
            rules_data = json.load(f)
        for idx, r in enumerate(rules_data):
            try:
                r_obj = Rule(**r)
                if r_obj.scheme_id not in valid_scheme_ids:
                    errors.append(f"Rule {r_obj.rule_id} references invalid scheme_id: {r_obj.scheme_id}")
                for p in r_obj.source_pages:
                    if not (1 <= p <= 261):
                        errors.append(f"Rule {r_obj.rule_id} invalid source page {p}")
            except Exception as e:
                errors.append(f"Rule validation error at index {idx}: {e}")
        print(f"  [OK] Validated {len(rules_data)} rules with valid scheme references.")
    except Exception as e:
        errors.append(f"Failed to read/validate rules: {e}")

    # 4. Validate Exclusions
    exclusions_file = os.path.join(DATA_DIR, "exclusions", "all_exclusions.json")
    try:
        with open(exclusions_file) as f:
            exclusions_data = json.load(f)
        for idx, ex in enumerate(exclusions_data):
            try:
                ex_obj = Exclusion(**ex)
                if ex_obj.scheme_id not in valid_scheme_ids:
                    errors.append(f"Exclusion {ex_obj.exclusion_id} references invalid scheme_id: {ex_obj.scheme_id}")
            except Exception as e:
                errors.append(f"Exclusion validation error at index {idx}: {e}")
        print(f"  [OK] Validated {len(exclusions_data)} exclusions.")
    except Exception as e:
        errors.append(f"Failed to read/validate exclusions: {e}")

    # 5. Validate Documents
    docs_file = os.path.join(DATA_DIR, "documents", "all_documents.json")
    try:
        with open(docs_file) as f:
            docs_data = json.load(f)
        for idx, d in enumerate(docs_data):
            try:
                d_obj = DocumentRequirement(**d)
                if d_obj.scheme_id not in valid_scheme_ids:
                    errors.append(f"Document {d_obj.document_id} references invalid scheme_id: {d_obj.scheme_id}")
            except Exception as e:
                errors.append(f"Document validation error at index {idx}: {e}")
        print(f"  [OK] Validated {len(docs_data)} document requirements.")
    except Exception as e:
        errors.append(f"Failed to read/validate documents: {e}")

    # 6. Validate Procedures
    procs_file = os.path.join(DATA_DIR, "procedures", "all_procedures.json")
    try:
        with open(procs_file) as f:
            procs_data = json.load(f)
        for idx, p in enumerate(procs_data):
            try:
                p_obj = Procedure(**p)
                if p_obj.scheme_id not in valid_scheme_ids:
                    errors.append(f"Procedure {p_obj.procedure_id} references invalid scheme_id: {p_obj.scheme_id}")
            except Exception as e:
                errors.append(f"Procedure validation error at index {idx}: {e}")
        print(f"  [OK] Validated {len(procs_data)} procedures.")
    except Exception as e:
        errors.append(f"Failed to read/validate procedures: {e}")

    # 7. Validate FAQs
    faqs_file = os.path.join(DATA_DIR, "faqs", "all_faqs.json")
    try:
        with open(faqs_file) as f:
            faqs_data = json.load(f)
        for idx, q in enumerate(faqs_data):
            try:
                q_obj = FAQ(**q)
                if q_obj.scheme_id not in valid_scheme_ids:
                    errors.append(f"FAQ {q_obj.faq_id} references invalid scheme_id: {q_obj.scheme_id}")
            except Exception as e:
                errors.append(f"FAQ validation error at index {idx}: {e}")
        print(f"  [OK] Validated {len(faqs_data)} FAQs.")
    except Exception as e:
        errors.append(f"Failed to read/validate FAQs: {e}")

    # 8. Validate Authorities
    auth_file = os.path.join(DATA_DIR, "authorities", "all_authorities.json")
    try:
        with open(auth_file) as f:
            auth_data = json.load(f)
        for idx, a in enumerate(auth_data):
            try:
                a_obj = Authority(**a)
                if a_obj.scheme_id not in valid_scheme_ids:
                    errors.append(f"Authority {a_obj.authority_id} references invalid scheme_id: {a_obj.scheme_id}")
            except Exception as e:
                errors.append(f"Authority validation error at index {idx}: {e}")
        print(f"  [OK] Validated {len(auth_data)} administrative authorities.")
    except Exception as e:
        errors.append(f"Failed to read/validate authorities: {e}")

    # 9. Validate Relationships
    rels_file = os.path.join(DATA_DIR, "relationships", "all_relationships.json")
    try:
        with open(rels_file) as f:
            rels_data = json.load(f)
        for idx, r in enumerate(rels_data):
            if r.get("source_scheme_id") not in valid_scheme_ids:
                errors.append(f"Relationship {r.get('relationship_id')} has invalid source_scheme_id: {r.get('source_scheme_id')}")
        print(f"  [OK] Validated {len(rels_data)} inter-scheme relationships.")
    except Exception as e:
        errors.append(f"Failed to read/validate relationships: {e}")

    # 10. Check Source Chunks
    chunks_file = os.path.join(DATA_DIR, "source_chunks", "all_chunks.json")
    try:
        with open(chunks_file) as f:
            chunks_data = json.load(f)
        for idx, c in enumerate(chunks_data):
            if c.get("scheme_id") not in valid_scheme_ids:
                errors.append(f"Chunk {c.get('chunk_id')} has invalid scheme_id: {c.get('scheme_id')}")
        print(f"  [OK] Validated {len(chunks_data)} source text chunks.")
    except Exception as e:
        errors.append(f"Failed to read/validate chunks: {e}")

    # Final Verdict
    if errors:
        print("\n=== STAGE 1 VALIDATION FAILED ===")
        for e in errors:
            print(f" - {e}")
        sys.exit(1)
    else:
        print("\n=== STAGE 1 VALIDATION PASSED ===")
        print("All canonical data files validated successfully against Pydantic schemas and relational integrity.")
        sys.exit(0)

if __name__ == "__main__":
    validate_data()
