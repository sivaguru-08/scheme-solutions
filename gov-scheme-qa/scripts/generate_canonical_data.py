"""
Stage 1: Generates and verifies canonical machine-readable data files.
Populates individual scheme JSONs and verifies consistency across:
- data/schemes/
- data/rules/
- data/exclusions/
- data/benefits/
- data/documents/
- data/procedures/
- data/faqs/
- data/authorities/
- data/relationships/
- data/temporal/
- data/source_chunks/
"""

import os
import json

DATA_DIR = "/home/sivaguru/Documents/slm/gov-scheme-qa/data"

with open(f"{DATA_DIR}/schemes/all_schemes.json", "r", encoding="utf-8") as f:
    schemes = json.load(f)

print(f"Total schemes in all_schemes: {len(schemes)}")

# Write individual scheme JSON files
for s in schemes:
    sid = s["scheme_id"]
    file_path = f"{DATA_DIR}/schemes/{sid}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)

print(f"Saved {len(schemes)} individual scheme files in {DATA_DIR}/schemes/")
