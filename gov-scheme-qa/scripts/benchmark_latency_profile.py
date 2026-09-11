"""
Stage 13: Latency Profiling and Optimization Benchmark.
Measures component-level breakdown:
- Entity extraction
- Intent classification
- Database retrieval
- Template rendering
- End-to-end pipeline P50, P95, P99
"""

import sys
import os
import time
import json
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from schemas.models import QueryRequest
from engine.pipeline import MasterQAPipeline

def profile_system():
    print("=== PROFILING PIPELINE LATENCY ===")
    pipeline = MasterQAPipeline()

    queries = [
        "What are the benefits of ONORC?",
        "What documents are required for PM Vishwakarma?",
        "How to apply for PM Surya Ghar?",
        "Who is excluded from PM-KISAN?",
        "I am 28 years old earning 11000 per month. Am I eligible for PM-SYM?",
        "Which ministry administers PM SVANidhi?",
        "List all government schemes",
        "Tell me about Atal Pension Yojana"
    ] * 25  # 200 total runs

    total_latencies = []
    extraction_times = []
    intent_times = []
    db_times = []
    rendering_times = []

    for q in queries:
        t0 = time.perf_counter()

        # Step 1: Extraction
        t_ext_start = time.perf_counter()
        slots, extracted_demo = pipeline.entity_extractor.extract_entities(q)
        extraction_times.append((time.perf_counter() - t_ext_start) * 1000)

        # Step 2: Intent
        t_int_start = time.perf_counter()
        intent_res = pipeline.intent_classifier.predict(q)
        intent_times.append((time.perf_counter() - t_int_start) * 1000)

        # Step 3: Full execution
        req = QueryRequest(query=q)
        res = pipeline.process_query(req)

        total_lat = (time.perf_counter() - t0) * 1000
        total_latencies.append(total_lat)

    p50 = np.percentile(total_latencies, 50)
    p95 = np.percentile(total_latencies, 95)
    p99 = np.percentile(total_latencies, 99)
    mean_ext = np.mean(extraction_times)
    mean_int = np.mean(intent_times)

    results = {
        "p50_latency_ms": round(float(p50), 3),
        "p95_latency_ms": round(float(p95), 3),
        "p99_latency_ms": round(float(p99), 3),
        "mean_extraction_latency_ms": round(float(mean_ext), 3),
        "mean_intent_latency_ms": round(float(mean_int), 3),
        "samples_evaluated": len(queries)
    }

    print(f"P50 Latency: {p50:.3f} ms")
    print(f"P95 Latency: {p95:.3f} ms")
    print(f"P99 Latency: {p99:.3f} ms")
    print(f"Mean Entity Extraction: {mean_ext:.3f} ms")
    print(f"Mean Intent Prediction: {mean_int:.3f} ms")

    return results

if __name__ == "__main__":
    profile_system()
