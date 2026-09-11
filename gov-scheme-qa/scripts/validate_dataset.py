"""
Stage 5 Dataset Validation Script.
Validates:
1. train.jsonl, validation.jsonl, test.jsonl exist and are valid JSONL
2. All scheme IDs match canonical schemes or null
3. All intents match canonical domain intents
4. No corrupted labels or missing fields
5. Zero leakage / zero duplicate queries across splits
"""

import sys
import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DATASET_DIR = os.path.join(BASE_DIR, "dataset")

VALID_INTENTS = {
    "OVERVIEW", "BENEFITS", "ELIGIBILITY", "CHECK_ELIGIBILITY",
    "DOCUMENTS", "PROCEDURE", "EXCLUSIONS", "AUTHORITY",
    "FAQ", "LIST_SCHEMES", "OUT_OF_SCOPE"
}

def validate_dataset():
    print("=== VALIDATING STAGE 5 QUERY DATASET ===")
    errors = []

    # Load canonical schemes
    schemes_file = os.path.join(BASE_DIR, "data", "schemes", "all_schemes.json")
    with open(schemes_file) as f:
        schemes = json.load(f)
    valid_scheme_ids = {s["scheme_id"] for s in schemes}

    splits = ["train.jsonl", "validation.jsonl", "test.jsonl"]
    split_queries = {}

    for s_name in splits:
        path = os.path.join(DATASET_DIR, s_name)
        if not os.path.exists(path):
            errors.append(f"Missing required split file: {s_name}")
            continue

        queries_in_split = set()
        line_count = 0

        with open(path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                line_count += 1
                try:
                    obj = json.loads(line)
                except Exception as e:
                    errors.append(f"{s_name}:{line_no} Invalid JSON syntax: {e}")
                    continue

                q = obj.get("query", "").strip().lower()
                intent = obj.get("intent")
                sid = obj.get("scheme_id")

                if not q:
                    errors.append(f"{s_name}:{line_no} Empty query string")

                if intent not in VALID_INTENTS:
                    errors.append(f"{s_name}:{line_no} Invalid intent '{intent}'")

                if sid is not None and sid not in valid_scheme_ids:
                    errors.append(f"{s_name}:{line_no} Invalid scheme_id '{sid}'")

                if q in queries_in_split:
                    errors.append(f"{s_name}:{line_no} Internal duplicate query: '{q}'")
                queries_in_split.add(q)

        split_queries[s_name] = queries_in_split
        print(f"  [OK] Validated {s_name}: {line_count} valid samples.")

    # Check for train / val / test leakage
    if "train.jsonl" in split_queries and "test.jsonl" in split_queries:
        train_test_leakage = split_queries["train.jsonl"].intersection(split_queries["test.jsonl"])
        if train_test_leakage:
            errors.append(f"Train/Test leakage detected! {len(train_test_leakage)} identical queries found in both train and test.")
        else:
            print("  [OK] Zero train/test leakage confirmed (0 duplicate queries).")

    if "train.jsonl" in split_queries and "validation.jsonl" in split_queries:
        train_val_leakage = split_queries["train.jsonl"].intersection(split_queries["validation.jsonl"])
        if train_val_leakage:
            errors.append(f"Train/Val leakage detected! {len(train_val_leakage)} identical queries found in both train and val.")
        else:
            print("  [OK] Zero train/val leakage confirmed (0 duplicate queries).")

    if "validation.jsonl" in split_queries and "test.jsonl" in split_queries:
        val_test_leakage = split_queries["validation.jsonl"].intersection(split_queries["test.jsonl"])
        if val_test_leakage:
            errors.append(f"Val/Test leakage detected! {len(val_test_leakage)} identical queries found in both val and test.")
        else:
            print("  [OK] Zero val/test leakage confirmed (0 duplicate queries).")

    if errors:
        print("\n=== STAGE 5 DATASET VALIDATION FAILED ===")
        for e in errors[:15]:
            print(f" - {e}")
        if len(errors) > 15:
            print(f" ... and {len(errors) - 15} more errors.")
        sys.exit(1)
    else:
        print("\n=== STAGE 5 DATASET VALIDATION PASSED ===")
        print("All dataset splits meet integrity, validity, and non-leakage criteria.")
        sys.exit(0)

if __name__ == "__main__":
    validate_dataset()
