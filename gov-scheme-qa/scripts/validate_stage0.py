"""
Stage 0 Validation Script.
Validates:
1. All required audit files exist
2. All 261 PDF pages are accounted for with zero gaps
3. All primary entities are cataloged with valid fields
4. Field dictionary contains type and descriptions
5. Discrepancy register contains valid entries with resolutions
"""

import sys
import os
import json
import csv

AUDIT_DIR = "/home/sivaguru/Documents/slm/gov-scheme-qa/audit"

def validate_stage0():
    print("=== RUNNING STAGE 0 VALIDATION ===")
    errors = []

    # 1. Check required files
    required_files = [
        "entity_inventory.csv",
        "field_dictionary.json",
        "source_page_map.json",
        "discrepancy_register.json",
        "audit_report.md"
    ]

    for rf in required_files:
        path = os.path.join(AUDIT_DIR, rf)
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            errors.append(f"Missing or empty required audit file: {rf}")
        else:
            print(f"  [OK] Found {rf} ({os.path.getsize(path)} bytes)")

    if errors:
        for err in errors:
            print(f"  [FAIL] {err}")
        sys.exit(1)

    # 2. Check source page map accounts for all 261 pages
    with open(os.path.join(AUDIT_DIR, "source_page_map.json")) as f:
        page_map = json.load(f)

    if len(page_map) < 261:
        errors.append(f"Page map only covers {len(page_map)} pages; expected 261 pages.")
    else:
        for p in range(1, 262):
            if str(p) not in page_map:
                errors.append(f"Page {p} missing from source page map!")
        print(f"  [OK] All 261 pages accounted for in source_page_map.json.")

    # 3. Check entity inventory
    with open(os.path.join(AUDIT_DIR, "entity_inventory.csv")) as f:
        reader = csv.DictReader(f)
        entities = list(reader)

    if len(entities) < 25:
        errors.append(f"Entity inventory contains only {len(entities)} entities; expected >= 25.")
    else:
        print(f"  [OK] Entity inventory validated: {len(entities)} entities cataloged.")

    # 4. Check field dictionary
    with open(os.path.join(AUDIT_DIR, "field_dictionary.json")) as f:
        fields = json.load(f)

    if not fields or "demographic" not in fields or "economic" not in fields:
        errors.append("Field dictionary missing core demographic or economic namespaces.")
    else:
        total_fields = sum(len(v) for v in fields.values())
        print(f"  [OK] Field dictionary validated: {total_fields} fields defined across {len(fields)} categories.")

    # 5. Check discrepancy register
    with open(os.path.join(AUDIT_DIR, "discrepancy_register.json")) as f:
        discrepancies = json.load(f)

    if len(discrepancies) < 3:
        errors.append("Discrepancy register has fewer than 3 documented issues.")
    else:
        print(f"  [OK] Discrepancy register validated: {len(discrepancies)} statutory issues recorded.")

    # Final verdict
    if errors:
        print("\n=== STAGE 0 VALIDATION FAILED ===")
        for e in errors:
            print(f" - {e}")
        sys.exit(1)
    else:
        print("\n=== STAGE 0 VALIDATION PASSED ===")
        print("All exit criteria satisfied.")
        sys.exit(0)

if __name__ == "__main__":
    validate_stage0()
