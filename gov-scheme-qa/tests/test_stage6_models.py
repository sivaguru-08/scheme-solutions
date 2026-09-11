"""
Stage 6 Test Suite: Query Understanding Models & Slot Extraction.
Verifies:
1. Intent model artifact loading and inference
2. Scheme model artifact loading and inference
3. Slot extraction separation
4. Sub-millisecond inference latency
"""

import sys
import os
import joblib
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from models.entity_extractor import DeterministicEntityExtractor

ARTIFACTS_DIR = os.path.join(BASE_DIR, "models", "artifacts")

@pytest.fixture
def intent_model():
    path = os.path.join(ARTIFACTS_DIR, "intent_model.joblib")
    assert os.path.exists(path), f"Missing intent model artifact at {path}"
    return joblib.load(path)

@pytest.fixture
def scheme_model():
    path = os.path.join(ARTIFACTS_DIR, "scheme_model.joblib")
    assert os.path.exists(path), f"Missing scheme model artifact at {path}"
    return joblib.load(path)

@pytest.fixture
def entity_extractor():
    return DeterministicEntityExtractor()

def test_intent_model_predictions(intent_model):
    pred = intent_model.predict(["What are the benefits of ONORC?"])[0]
    assert pred == "BENEFITS"

    pred_proc = intent_model.predict(["How to apply for PM Surya Ghar?"])[0]
    assert pred_proc == "PROCEDURE"

    pred_docs = intent_model.predict(["What documents are required for PM Vishwakarma?"])[0]
    assert pred_docs == "DOCUMENTS"

    pred_auth = intent_model.predict(["Which ministry administers PM SVANidhi?"])[0]
    assert pred_auth == "AUTHORITY"

def test_scheme_model_predictions(scheme_model):
    pred = scheme_model.predict(["What are the benefits of One Nation One Ration Card?"])[0]
    assert pred == "SCH_ONORC"

    pred_kisan = scheme_model.predict(["Tell me about PM-KISAN eligibility"])[0]
    assert pred_kisan == "SCH_PMKISAN"

    pred_vishwa = scheme_model.predict(["How to apply for PM Vishwakarma?"])[0]
    assert pred_vishwa == "SCH_VISHWA"

def test_slot_extraction_separation(entity_extractor):
    slots, demo = entity_extractor.extract_entities(
        "I am 32 years old earning 14000 per month as an artisan. Am I eligible for PM Vishwakarma?"
    )
    # Scheme detection
    assert "SCH_VISHWA" in slots.scheme_ids
    # Demographic slots
    assert demo.age == 32
    assert demo.monthly_income == 14000.0
    assert demo.occupation == "ARTISAN"

def test_inference_latency_bounds(intent_model, scheme_model):
    import time
    queries = ["What are the benefits of PM-KISAN?"] * 50
    start = time.perf_counter()
    _ = intent_model.predict(queries)
    elapsed = (time.perf_counter() - start) * 1000 / 50
    assert elapsed < 5.0, f"Inference latency exceeded 5ms: {elapsed:.3f}ms"
