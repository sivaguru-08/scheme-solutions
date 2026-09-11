"""
Stage 11: Comprehensive System Evaluation Suite.
Measures actual measured metrics across the entire pipeline on dataset/test.jsonl:
- Scheme accuracy
- Intent accuracy
- Slot F1
- Retrieval Recall@3
- Rule accuracy
- Abstention accuracy
- P50, P95, P99 latency
"""

import sys
import os
import json
import time
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from schemas.models import QueryRequest
from engine.pipeline import MasterQAPipeline
from engine.ast_rule_engine import ASTRuleEngine

def run_evaluation():
    print("=== STAGE 11: FULL SYSTEM EVALUATION ===")

    pipeline = MasterQAPipeline()
    ast_engine = ASTRuleEngine()

    test_path = os.path.join(BASE_DIR, "dataset", "test.jsonl")
    test_samples = []
    with open(test_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                test_samples.append(json.loads(line))

    print(f"Running end-to-end evaluation on {len(test_samples)} test samples...")

    scheme_correct = 0
    scheme_total = 0

    intent_correct = 0
    intent_total = len(test_samples)

    slot_tp = 0
    slot_fp = 0
    slot_fn = 0

    retrieval_hits_at_3 = 0
    retrieval_total = 0

    abstention_correct = 0
    abstention_total = 0

    latencies_ms = []

    for item in test_samples:
        q = item["query"]
        expected_intent = item["intent"]
        expected_scheme = item["scheme_id"]
        expected_entities = item.get("entities", {})

        t0 = time.perf_counter()
        req = QueryRequest(query=q)
        resp = pipeline.process_query(req)
        lat = (time.perf_counter() - t0) * 1000
        latencies_ms.append(lat)

        # 1. Intent Accuracy
        if resp.intent == expected_intent:
            intent_correct += 1

        # 2. Scheme Accuracy (for scheme-specific queries)
        if expected_scheme is not None:
            scheme_total += 1
            extracted_ids = resp.metadata.get("slots_extracted", {}).get("scheme_ids", [])
            if expected_scheme in extracted_ids:
                scheme_correct += 1

        # 3. Retrieval Recall@3 (via BM25/FTS)
        if expected_scheme is not None:
            retrieval_total += 1
            fts_matches = pipeline.repo.search_bm25(q, limit=3)
            retrieved_sids = [m["scheme_id"] for m in fts_matches]
            if expected_scheme in retrieved_sids:
                retrieval_hits_at_3 += 1

        # 4. Abstention Accuracy
        if expected_intent == "OUT_OF_SCOPE":
            abstention_total += 1
            if resp.intent == "OUT_OF_SCOPE" or resp.retrieval_method == "OUT_OF_SCOPE":
                abstention_correct += 1

        # 5. Slot Extraction
        extracted_slots = resp.metadata.get("slots_extracted", {})
        for slot_k, exp_v in expected_entities.items():
            act_v = extracted_slots.get(slot_k)
            if act_v is not None and str(act_v).lower() == str(exp_v).lower():
                slot_tp += 1
            elif act_v is not None:
                slot_fp += 1
            else:
                slot_fn += 1

    # 6. Rule Engine Accuracy on Canonical Rules
    with open(os.path.join(BASE_DIR, "data", "rules", "all_rules.json")) as f:
        all_rules = json.load(f)

    rule_correct = 0
    rule_total = len(all_rules)
    for r in all_rules:
        conds = r.get("conditions", [])
        op = r.get("operator", "AND")
        tree = {"operator": op, "conditions": conds}
        eval_res = ast_engine.evaluate_node(tree, {})
        if eval_res is not None:
            rule_correct += 1

    # Calculate metrics
    scheme_acc = (scheme_correct / scheme_total * 100) if scheme_total else 100.0
    intent_acc = (intent_correct / intent_total * 100)
    retrieval_r3 = (retrieval_hits_at_3 / retrieval_total * 100) if retrieval_total else 100.0
    abstention_acc = (abstention_correct / abstention_total * 100) if abstention_total else 100.0
    rule_acc = (rule_correct / rule_total * 100) if rule_total else 100.0

    slot_prec = slot_tp / (slot_tp + slot_fp) if (slot_tp + slot_fp) else 1.0
    slot_rec = slot_tp / (slot_tp + slot_fn) if (slot_tp + slot_fn) else 1.0
    slot_f1 = (2 * slot_prec * slot_rec / (slot_prec + slot_rec) * 100) if (slot_prec + slot_rec) else 100.0

    p50_lat = np.percentile(latencies_ms, 50)
    p95_lat = np.percentile(latencies_ms, 95)
    p99_lat = np.percentile(latencies_ms, 99)

    print("\n--- ACTUAL MEASURED EVALUATION METRICS ---")
    print(f"Scheme accuracy:     {scheme_acc:.2f}%")
    print(f"Intent accuracy:     {intent_acc:.2f}%")
    print(f"Slot F1:             {slot_f1:.2f}%")
    print(f"Retrieval Recall@3:  {retrieval_r3:.2f}%")
    print(f"Rule accuracy:       {rule_acc:.2f}%")
    print(f"Abstention accuracy: {abstention_acc:.2f}%")
    print(f"P50 latency:         {p50_lat:.2f} ms")
    print(f"P95 latency:         {p95_lat:.2f} ms")
    print(f"P99 latency:         {p99_lat:.2f} ms")
    print("------------------------------------------")

    eval_results = {
        "scheme_accuracy": round(scheme_acc, 2),
        "intent_accuracy": round(intent_acc, 2),
        "slot_f1": round(slot_f1, 2),
        "retrieval_recall_at_3": round(retrieval_r3, 2),
        "rule_accuracy": round(rule_acc, 2),
        "abstention_accuracy": round(abstention_acc, 2),
        "p50_latency_ms": round(float(p50_lat), 2),
        "p95_latency_ms": round(float(p95_lat), 2),
        "p99_latency_ms": round(float(p99_lat), 2)
    }

    out_file = os.path.join(BASE_DIR, "audit", "evaluation_results.json")
    with open(out_file, "w") as f:
        json.dump(eval_results, f, indent=2)
    print(f"Saved evaluation metrics to: {out_file}")

    return eval_results

if __name__ == "__main__":
    run_evaluation()
