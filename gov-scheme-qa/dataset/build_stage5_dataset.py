"""
Stage 5: Query-Understanding Dataset Generator.
Builds grounded query datasets with splits:
- dataset/train.jsonl
- dataset/validation.jsonl
- dataset/test.jsonl
Ensures zero duplicate queries across splits (no leakage).
"""

import sys
import os
import json
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DATASET_DIR = os.path.join(BASE_DIR, "dataset")
os.makedirs(DATASET_DIR, exist_ok=True)

# Load canonical schemes
with open(os.path.join(BASE_DIR, "data", "schemes", "all_schemes.json")) as f:
    schemes = json.load(f)

scheme_dict = {s["scheme_id"]: s for s in schemes}

INTENTS = [
    "OVERVIEW", "BENEFITS", "ELIGIBILITY", "CHECK_ELIGIBILITY",
    "DOCUMENTS", "PROCEDURE", "EXCLUSIONS", "AUTHORITY",
    "FAQ", "LIST_SCHEMES", "OUT_OF_SCOPE"
]

TEMPLATES = {
    "OVERVIEW": [
        "What is {name}?",
        "Explain {abbreviation}",
        "Tell me about {name}",
        "What is the objective of {abbreviation}?",
        "Overview of {name}",
        "Can you provide details on {abbreviation}?",
        "Summary of {name}"
    ],
    "BENEFITS": [
        "What are the benefits of {name}?",
        "How much money do I get under {abbreviation}?",
        "What financial assistance does {name} offer?",
        "Tell me the benefits provided by {abbreviation}",
        "What is the coverage under {name}?",
        "What do beneficiaries receive under {abbreviation}?",
        "What are the financial payouts in {name}?"
    ],
    "ELIGIBILITY": [
        "What is the eligibility criteria for {name}?",
        "Who is eligible for {abbreviation}?",
        "What are the age limits for {name}?",
        "Who can join {abbreviation}?",
        "What are the qualification rules for {name}?",
        "What income limits apply to {abbreviation}?"
    ],
    "CHECK_ELIGIBILITY": [
        "I am {age} years old earning {income} per month. Am I eligible for {name}?",
        "Can a {occupation} aged {age} apply for {abbreviation}?",
        "Do I qualify for {name} if my age is {age} and monthly income is {income}?",
        "Am I eligible for {abbreviation} as a {occupation}?",
        "Check my eligibility for {name} with age {age}."
    ],
    "DOCUMENTS": [
        "What documents are required for {name}?",
        "What papers do I need to apply for {abbreviation}?",
        "Required documents checklist for {name}",
        "Do I need an Aadhaar card for {abbreviation}?",
        "Which KYC proofs are mandatory for {name}?"
    ],
    "PROCEDURE": [
        "How to apply for {name}?",
        "What is the application process for {abbreviation}?",
        "Step by step registration procedure for {name}",
        "Can I register online for {abbreviation}?",
        "Where do I submit the application form for {name}?"
    ],
    "EXCLUSIONS": [
        "Who is excluded from {name}?",
        "Who cannot apply for {abbreviation}?",
        "What are the disqualifications for {name}?",
        "Are income tax payers excluded from {abbreviation}?",
        "Who is ineligible for {name}?"
    ],
    "AUTHORITY": [
        "Which ministry administers {name}?",
        "Who is the implementing agency for {abbreviation}?",
        "Helpline number for {name}",
        "Toll-free customer care number for {abbreviation}",
        "Official website portal for {name}?"
    ],
    "FAQ": [
        "Frequently asked questions about {name}",
        "Can my family claim benefits in another state under {abbreviation}?",
        "Is eKYC mandatory for {name}?",
        "Common questions and answers on {abbreviation}"
    ]
}

OCCUPATIONS = ["farmer", "street vendor", "carpenter", "tailor", "weaver", "construction worker", "unorganised worker", "artisan", "small retailer"]
OUT_OF_SCOPE_QUERIES = [
    "What is the capital of France?",
    "Write a poem about the sea",
    "Who won the 2024 cricket world cup?",
    "How do I bake a chocolate cake?",
    "What is quantum computing?",
    "Solve quadratic equation x^2 - 4 = 0",
    "What is the population of Tokyo?",
    "Book a hotel room in Goa",
    "Translate this sentence to Spanish",
    "What is the weather in Delhi right now?"
]

LIST_SCHEMES_QUERIES = [
    "List all government schemes",
    "What welfare schemes are available?",
    "Show me the catalog of central schemes",
    "List social security schemes",
    "Display all government programmes",
    "Give me a list of all 29 schemes",
    "What schemes can I apply for in India?"
]

def build_dataset():
    all_examples = []
    seen_queries = set()

    def add_example(q, intent, sid=None, entities=None):
        clean_q = " ".join(q.strip().split())
        q_lower = clean_q.lower()
        if q_lower in seen_queries:
            return
        seen_queries.add(q_lower)
        all_examples.append({
            "query": clean_q,
            "intent": intent,
            "scheme_id": sid,
            "entities": entities or {}
        })

    # 1. Scheme-specific intents
    for sid, s in scheme_dict.items():
        name = s["official_name"]
        abbr = s.get("abbreviation") or name

        for intent, tmpls in TEMPLATES.items():
            for tmpl in tmpls:
                age = random.randint(18, 55)
                income = random.choice([8000, 10000, 12000, 14000, 16000, 20000])
                occ = random.choice(OCCUPATIONS)

                query = tmpl.format(
                    name=name,
                    abbreviation=abbr,
                    age=age,
                    income=income,
                    occupation=occ
                )

                entities = {}
                if intent == "CHECK_ELIGIBILITY":
                    if "{age}" in tmpl:
                        entities["age"] = age
                    if "{income}" in tmpl:
                        entities["income"] = income
                    if "{occupation}" in tmpl:
                        entities["occupation"] = occ

                add_example(query, intent, sid, entities)

    # 2. List Schemes
    for q in LIST_SCHEMES_QUERIES:
        add_example(q, "LIST_SCHEMES", None)
        add_example(f"Please {q.lower()}", "LIST_SCHEMES", None)

    # 3. Out of scope
    for q in OUT_OF_SCOPE_QUERIES:
        add_example(q, "OUT_OF_SCOPE", None)
        add_example(f"Tell me {q.lower()}", "OUT_OF_SCOPE", None)

    random.seed(42)
    random.shuffle(all_examples)

    total = len(all_examples)
    train_end = int(total * 0.70)
    val_end = int(total * 0.85)

    train_split = all_examples[:train_end]
    val_split = all_examples[train_end:val_end]
    test_split = all_examples[val_end:]

    print(f"Generated {total} unique grounded query examples.")
    print(f"Train split: {len(train_split)} | Validation split: {len(val_split)} | Test split: {len(test_split)}")

    # Write JSONL splits
    for name, split in [("train.jsonl", train_split), ("validation.jsonl", val_split), ("test.jsonl", test_split)]:
        path = os.path.join(DATASET_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            for item in split:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"Saved {path} ({len(split)} lines)")

if __name__ == "__main__":
    build_dataset()
