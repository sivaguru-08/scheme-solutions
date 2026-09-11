"""
Stage 7 Test Suite: Retrieval Performance & Metrics.
Verifies:
1. SQLite FTS5 BM25 search functionality
2. Benchmarked Recall@3 >= 89%
3. Average latency < 5ms
"""

import sys
import os
import json
import time
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from store.database import SchemeRepository

@pytest.fixture
def repo():
    return SchemeRepository()

def test_bm25_retrieval_accuracy(repo):
    # Test specific high-value queries
    r1 = repo.search_bm25("ration card portability across fair price shops")
    assert len(r1) > 0
    assert r1[0]["scheme_id"] == "SCH_ONORC"

    r2 = repo.search_bm25("solar rooftop muft bijli 300 units")
    assert len(r2) > 0
    assert r2[0]["scheme_id"] == "SCH_PMSURYA"

    r3 = repo.search_bm25("unorganised worker monthly pension 3000 rupees")
    assert len(r3) > 0
    assert r3[0]["scheme_id"] == "SCH_PMSYM"

def test_benchmark_metrics_file_exists():
    path = os.path.join(BASE_DIR, "audit", "retrieval_benchmark.json")
    assert os.path.exists(path), f"Benchmark file {path} missing"
    with open(path) as f:
        data = json.load(f)

    assert "sqlite_fts5_bm25" in data
    assert "hybrid_rrf" in data
    assert data["hybrid_rrf"]["Recall@3"] >= 0.90
    assert data["sqlite_fts5_bm25"]["latency_ms"] < 5.0

def test_retrieval_latency_benchmark(repo):
    t0 = time.perf_counter()
    queries = ["pension", "ration card", "solar rooftop", "street vendor", "kisan"]
    for q in queries:
        _ = repo.search_bm25(q, limit=3)
    avg_latency = (time.perf_counter() - t0) * 1000 / len(queries)
    assert avg_latency < 5.0, f"Average retrieval latency too high: {avg_latency:.2f}ms"
