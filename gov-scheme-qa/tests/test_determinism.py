import pytest
from engine.pipeline import MasterQAPipeline
from schemas.models import QueryRequest

def test_complete_determinism():
    pipeline = MasterQAPipeline()
    query = "What documents are required for PM Vishwakarma?"

    first_resp = pipeline.process_query(QueryRequest(query=query))

    # Run 25 consecutive times and assert exact byte equality
    for i in range(25):
        subsequent_resp = pipeline.process_query(QueryRequest(query=query))
        assert subsequent_resp.intent == first_resp.intent
        assert subsequent_resp.detected_schemes == first_resp.detected_schemes
        assert subsequent_resp.retrieval_method == first_resp.retrieval_method
        assert subsequent_resp.answer == first_resp.answer, f"Non-deterministic variance detected on run {i}!"
        assert len(subsequent_resp.citations) == len(first_resp.citations)
