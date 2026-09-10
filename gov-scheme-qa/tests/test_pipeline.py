import pytest
from engine.pipeline import MasterQAPipeline
from schemas.models import QueryRequest

@pytest.fixture
def pipeline():
    return MasterQAPipeline()

def test_pipeline_onorc_benefits(pipeline):
    res = pipeline.process_query(QueryRequest(query="What are the benefits of ONORC?"))
    assert res.intent == "BENEFITS"
    assert "One Nation One Ration Card" in res.detected_schemes
    assert "Fair Price Shop" in res.answer
    assert res.is_deterministic is True
    assert len(res.citations) > 0
    assert res.metadata["latency_ms"] < 50  # Must be fast

def test_pipeline_pmsym_eligibility(pipeline):
    res = pipeline.process_query(QueryRequest(
        query="I am 26 years old earning 10000 per month as a daily wager. Am I eligible for PM-SYM?"
    ))
    assert res.intent == "CHECK_ELIGIBILITY"
    assert "ELIGIBLE" in res.answer
    assert res.retrieval_method == "RULE_EVALUATOR"

def test_pipeline_pmkisan_exclusions(pipeline):
    res = pipeline.process_query(QueryRequest(query="Who is excluded from PM-KISAN?"))
    assert res.intent == "EXCLUSIONS"
    assert "Institutional" in res.answer or "tax" in res.answer.lower()
    assert len(res.citations) > 0

def test_pipeline_catalog_list(pipeline):
    res = pipeline.process_query(QueryRequest(query="List all government schemes"))
    assert res.intent == "LIST_SCHEMES"
    assert "Available Government Schemes" in res.answer
    assert "29" in res.answer or len(res.answer) > 500
