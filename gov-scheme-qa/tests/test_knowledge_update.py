import pytest
import copy
from store.database import SchemeRepository
from engine.pipeline import MasterQAPipeline
from engine.ast_rule_engine import ASTRuleEngine
from schemas.models import QueryRequest
from scripts.update_knowledge import upsert_benefit, upsert_rule, upsert_document_set, rebuild_fts5_index

@pytest.fixture
def repo():
    return SchemeRepository()

@pytest.fixture
def pipeline(repo):
    return MasterQAPipeline(repo)

def test_benefit_update_without_model_retraining(repo, pipeline):
    # 1. Fetch original PM-SYM benefits
    original_benefits = repo.get_benefits_for_scheme("SCH_PMSYM")
    assert len(original_benefits) > 0
    orig_b = copy.deepcopy(original_benefits[0])

    try:
        # 2. Update benefit description & quantified value deterministically
        updated_b = copy.deepcopy(orig_b)
        updated_b["description"] = "Enhanced pension of Rs 5,000 per month after attaining 60 years of age"
        updated_b["quantified_value"] = "Rs 5,000 per month"
        success = upsert_benefit(updated_b)
        assert success is True

        # 3. Verify direct lookup returns new amount immediately
        fresh_benefits = repo.get_benefits_for_scheme("SCH_PMSYM")
        assert any("5,000" in b["description"] for b in fresh_benefits)

        # 4. Verify pipeline query delivers updated answer without ML retraining
        res = pipeline.process_query(QueryRequest(query="What are the benefits of PM-SYM?"))
        assert "5,000" in res.answer
        assert res.is_deterministic is True

    finally:
        # Revert to original benefit
        upsert_benefit(orig_b)
        reverted_benefits = repo.get_benefits_for_scheme("SCH_PMSYM")
        assert any(orig_b["description"] in b["description"] for b in reverted_benefits)

def test_ast_rule_update_without_model_retraining(repo):
    # Test updating eligibility threshold in AST engine
    engine = ASTRuleEngine()
    
    # Original condition: Income <= 15000 fails for 18000
    cond_orig = {
        "operator": "AND",
        "conditions": [
            {"field": "income", "operator": "LESS_THAN_OR_EQUAL", "value": 15000, "description": "Monthly income <= 15000"}
        ]
    }
    user_context = {"income": 18000}
    res_orig = engine.evaluate_node(cond_orig, user_context)
    assert res_orig.is_satisfied is False
    assert len(res_orig.failed_conditions) == 1

    # Statutory amendment: Income ceiling raised to 25,000
    cond_amended = {
        "operator": "AND",
        "conditions": [
            {"field": "income", "operator": "LESS_THAN_OR_EQUAL", "value": 25000, "description": "Monthly income <= 25000"}
        ]
    }
    res_amended = engine.evaluate_node(cond_amended, user_context)
    assert res_amended.is_satisfied is True
    assert len(res_amended.passed_conditions) == 1

def test_document_requirement_update(repo, pipeline):
    orig_docs = repo.get_documents_for_scheme("SCH_ONORC")
    assert orig_docs is not None
    orig_mandatory = copy.deepcopy(orig_docs["mandatory"])

    try:
        updated_docs = copy.deepcopy(orig_docs)
        updated_docs["mandatory"].append({
            "name": "Voter ID Card",
            "description": "Election photo identity card",
            "purpose": "Secondary identity proof"
        })
        success = upsert_document_set(updated_docs)
        assert success is True

        res = pipeline.process_query(QueryRequest(query="What documents do I need for ONORC?"))
        assert "Voter ID" in res.answer
        assert res.is_deterministic is True
    finally:
        orig_docs["mandatory"] = orig_mandatory
        upsert_document_set(orig_docs)

def test_fts5_index_rebuild_and_search(repo):
    success = rebuild_fts5_index()
    assert success is True
    results = repo.search_bm25("solar")
    assert len(results) > 0
    assert any("Surya" in r["scheme_name"] or "Solar" in r["scheme_name"] or "solar" in r["content"].lower() for r in results)
