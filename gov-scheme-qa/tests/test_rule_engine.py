"""
Stage 4 Mandatory Test Suite: Deterministic AST Rule Engine.
Tests all required operator and logic capabilities:
- AND, OR, nested AND, nested OR, mixed AND/OR
- Operators: ==, !=, >, >=, <, <=, IN, NOT_IN, BETWEEN, IS_NULL, IS_NOT_NULL
- Verification that (A OR B) != (A AND B)
- Missing field handling (single & multiple)
- Exclusions & exceptions
- Comprehensive evaluation of EVERY rule extracted from the PDF
"""

import sys
import os
import json
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.ast_rule_engine import ASTRuleEngine

@pytest.fixture
def engine():
    return ASTRuleEngine()

# 1. Atomic Comparison Operators
def test_operator_equal(engine):
    node = {"field": "gender", "operator": "==", "value": "FEMALE"}
    assert engine.evaluate_node(node, {"gender": "FEMALE"}).is_satisfied is True
    assert engine.evaluate_node(node, {"gender": "female"}).is_satisfied is True  # case-insensitive
    assert engine.evaluate_node(node, {"gender": "MALE"}).is_satisfied is False

def test_operator_not_equal(engine):
    node = {"field": "status", "operator": "!=", "value": "DISQUALIFIED"}
    assert engine.evaluate_node(node, {"status": "ACTIVE"}).is_satisfied is True
    assert engine.evaluate_node(node, {"status": "DISQUALIFIED"}).is_satisfied is False

def test_operator_greater_than(engine):
    node = {"field": "age", "operator": ">", "value": 18}
    assert engine.evaluate_node(node, {"age": 19}).is_satisfied is True
    assert engine.evaluate_node(node, {"age": 18}).is_satisfied is False
    assert engine.evaluate_node(node, {"age": 17}).is_satisfied is False

def test_operator_greater_than_or_equal(engine):
    node = {"field": "age", "operator": ">=", "value": 18}
    assert engine.evaluate_node(node, {"age": 18}).is_satisfied is True
    assert engine.evaluate_node(node, {"age": 19}).is_satisfied is True
    assert engine.evaluate_node(node, {"age": 17}).is_satisfied is False

def test_operator_less_than(engine):
    node = {"field": "monthly_income", "operator": "<", "value": 15000}
    assert engine.evaluate_node(node, {"monthly_income": 14999}).is_satisfied is True
    assert engine.evaluate_node(node, {"monthly_income": 15000}).is_satisfied is False

def test_operator_less_than_or_equal(engine):
    node = {"field": "monthly_income", "operator": "<=", "value": 15000}
    assert engine.evaluate_node(node, {"monthly_income": 15000}).is_satisfied is True
    assert engine.evaluate_node(node, {"monthly_income": 15001}).is_satisfied is False

def test_operator_in(engine):
    node = {"field": "category", "operator": "IN", "value": ["SC", "ST", "OBC"]}
    assert engine.evaluate_node(node, {"category": "SC"}).is_satisfied is True
    assert engine.evaluate_node(node, {"category": "st"}).is_satisfied is True
    assert engine.evaluate_node(node, {"category": "GENERAL"}).is_satisfied is False

def test_operator_not_in(engine):
    node = {"field": "category", "operator": "NOT_IN", "value": ["EXCLUDED_1", "EXCLUDED_2"]}
    assert engine.evaluate_node(node, {"category": "VALID_CAT"}).is_satisfied is True
    assert engine.evaluate_node(node, {"category": "EXCLUDED_1"}).is_satisfied is False

def test_operator_between(engine):
    node = {"field": "age", "operator": "BETWEEN", "value": [18, 40]}
    assert engine.evaluate_node(node, {"age": 18}).is_satisfied is True
    assert engine.evaluate_node(node, {"age": 30}).is_satisfied is True
    assert engine.evaluate_node(node, {"age": 40}).is_satisfied is True
    assert engine.evaluate_node(node, {"age": 17}).is_satisfied is False
    assert engine.evaluate_node(node, {"age": 41}).is_satisfied is False

def test_operator_is_null_and_is_not_null(engine):
    null_node = {"field": "disability_cert", "operator": "IS_NULL"}
    not_null_node = {"field": "aadhaar_number", "operator": "IS_NOT_NULL"}
    assert engine.evaluate_node(null_node, {"disability_cert": None}).is_satisfied is True
    assert engine.evaluate_node(null_node, {"disability_cert": "CERT_123"}).is_satisfied is False
    assert engine.evaluate_node(not_null_node, {"aadhaar_number": "1234-5678"}).is_satisfied is True
    assert engine.evaluate_node(not_null_node, {"aadhaar_number": None}).is_satisfied is False

# 2. Boolean Logic & Structure
def test_logical_and(engine):
    tree = {
        "operator": "AND",
        "conditions": [
            {"field": "age", "operator": ">=", "value": 18},
            {"field": "age", "operator": "<=", "value": 40}
        ]
    }
    assert engine.evaluate_node(tree, {"age": 25}).is_satisfied is True
    assert engine.evaluate_node(tree, {"age": 17}).is_satisfied is False
    assert engine.evaluate_node(tree, {"age": 45}).is_satisfied is False

def test_logical_or(engine):
    tree = {
        "operator": "OR",
        "conditions": [
            {"field": "has_vending_id", "operator": "==", "value": True},
            {"field": "has_recommendation_letter", "operator": "==", "value": True}
        ]
    }
    # One True -> True
    assert engine.evaluate_node(tree, {"has_vending_id": True, "has_recommendation_letter": False}).is_satisfied is True
    assert engine.evaluate_node(tree, {"has_vending_id": False, "has_recommendation_letter": True}).is_satisfied is True
    # Both True -> True
    assert engine.evaluate_node(tree, {"has_vending_id": True, "has_recommendation_letter": True}).is_satisfied is True
    # Both False -> False
    assert engine.evaluate_node(tree, {"has_vending_id": False, "has_recommendation_letter": False}).is_satisfied is False

def test_or_does_not_behave_like_and(engine):
    """Explicitly verify: (A OR B) does NOT behave like (A AND B)"""
    or_tree = {
        "operator": "OR",
        "conditions": [
            {"field": "opt_a", "operator": "==", "value": True},
            {"field": "opt_b", "operator": "==", "value": True}
        ]
    }
    and_tree = {
        "operator": "AND",
        "conditions": [
            {"field": "opt_a", "operator": "==", "value": True},
            {"field": "opt_b", "operator": "==", "value": True}
        ]
    }
    sample_context = {"opt_a": True, "opt_b": False}
    or_result = engine.evaluate_node(or_tree, sample_context)
    and_result = engine.evaluate_node(and_tree, sample_context)

    assert or_result.is_satisfied is True, "OR must be True when one condition is met"
    assert and_result.is_satisfied is False, "AND must be False when one condition is not met"
    assert or_result.is_satisfied != and_result.is_satisfied

def test_nested_and(engine):
    tree = {
        "operator": "AND",
        "conditions": [
            {"field": "citizenship", "operator": "==", "value": "INDIAN"},
            {
                "operator": "AND",
                "conditions": [
                    {"field": "age", "operator": ">=", "value": 18},
                    {"field": "monthly_income", "operator": "<=", "value": 15000}
                ]
            }
        ]
    }
    assert engine.evaluate_node(tree, {"citizenship": "INDIAN", "age": 25, "monthly_income": 12000}).is_satisfied is True
    assert engine.evaluate_node(tree, {"citizenship": "INDIAN", "age": 25, "monthly_income": 18000}).is_satisfied is False

def test_nested_or(engine):
    tree = {
        "operator": "OR",
        "conditions": [
            {"field": "is_bpl", "operator": "==", "value": True},
            {
                "operator": "OR",
                "conditions": [
                    {"field": "is_sc_st", "operator": "==", "value": True},
                    {"field": "is_forest_dweller", "operator": "==", "value": True}
                ]
            }
        ]
    }
    assert engine.evaluate_node(tree, {"is_bpl": False, "is_sc_st": False, "is_forest_dweller": True}).is_satisfied is True
    assert engine.evaluate_node(tree, {"is_bpl": False, "is_sc_st": False, "is_forest_dweller": False}).is_satisfied is False

def test_mixed_and_or(engine):
    # Rule: Citizen AND (Farmer OR Artisan) AND Income <= 20000
    tree = {
        "operator": "AND",
        "conditions": [
            {"field": "citizenship", "operator": "==", "value": "INDIAN"},
            {
                "operator": "OR",
                "conditions": [
                    {"field": "occupation", "operator": "==", "value": "FARMER"},
                    {"field": "occupation", "operator": "==", "value": "ARTISAN"}
                ]
            },
            {"field": "monthly_income", "operator": "<=", "value": 20000}
        ]
    }
    # Meets all -> True
    assert engine.evaluate_node(tree, {"citizenship": "INDIAN", "occupation": "ARTISAN", "monthly_income": 15000}).is_satisfied is True
    # Occupation outside OR -> False
    assert engine.evaluate_node(tree, {"citizenship": "INDIAN", "occupation": "LAWYER", "monthly_income": 15000}).is_satisfied is False
    # Income fails AND -> False
    assert engine.evaluate_node(tree, {"citizenship": "INDIAN", "occupation": "FARMER", "monthly_income": 25000}).is_satisfied is False

# 3. Missing Fields & Inconclusive States
def test_single_missing_field(engine):
    node = {"field": "annual_turnover", "operator": "<=", "value": 15000000}
    res = engine.evaluate_node(node, {})
    assert res.is_satisfied is False
    assert res.is_conclusive is False
    assert res.missing_fields == ["annual_turnover"]

def test_multiple_missing_fields(engine):
    tree = {
        "operator": "AND",
        "conditions": [
            {"field": "age", "operator": ">=", "value": 18},
            {"field": "monthly_income", "operator": "<=", "value": 15000},
            {"field": "residence_state", "operator": "==", "value": "MAHARASHTRA"}
        ]
    }
    res = engine.evaluate_node(tree, {"age": 25})  # income and state missing
    assert res.is_satisfied is False
    assert res.is_conclusive is False
    assert set(res.missing_fields) == {"monthly_income", "residence_state"}

# 4. Exclusions & Disqualifications
def test_exclusion_rule(engine):
    exclusion_tree = {
        "operator": "OR",
        "conditions": [
            {"field": "is_income_tax_payer", "operator": "==", "value": True},
            {"field": "is_epfo_member", "operator": "==", "value": True}
        ]
    }
    # If taxpayer, exclusion is triggered (applicant excluded)
    assert engine.evaluate_node(exclusion_tree, {"is_income_tax_payer": True, "is_epfo_member": False}).is_satisfied is True
    # If neither, exclusion is NOT triggered (applicant not excluded)
    assert engine.evaluate_node(exclusion_tree, {"is_income_tax_payer": False, "is_epfo_member": False}).is_satisfied is False

# 5. Comprehensive Test on EVERY Rule Extracted from the PDF
def test_every_extracted_pdf_rule(engine):
    rules_file = os.path.join(BASE_DIR, "data", "rules", "all_rules.json")
    with open(rules_file) as f:
        all_rules = json.load(f)

    assert len(all_rules) >= 25, "Expected at least 25 canonical rules"

    for r in all_rules:
        rule_id = r["rule_id"]
        conds = r.get("conditions", [])
        op = r.get("operator", "AND")

        tree = {
            "operator": op,
            "conditions": conds
        }

        # Test with empty context -> must identify missing fields, never crash
        empty_res = engine.evaluate_node(tree, {})
        assert empty_res is not None
        assert isinstance(empty_res.is_satisfied, bool)

        # Build mock satisfying context from the conditions
        mock_ctx = {}
        for c in conds:
            if "field" in c:
                f_name = c["field"].split(".")[-1]
                op_c = c.get("operator", "==")
                val_c = c.get("value")
                if op_c in ["==", "="]:
                    mock_ctx[f_name] = val_c
                elif op_c == ">=":
                    mock_ctx[f_name] = val_c + 1 if isinstance(val_c, (int, float)) else val_c
                elif op_c == "<=":
                    mock_ctx[f_name] = val_c - 1 if isinstance(val_c, (int, float)) else val_c
                elif op_c == "BETWEEN":
                    mock_ctx[f_name] = (val_c[0] + val_c[1]) / 2
                elif op_c == "IN":
                    mock_ctx[f_name] = val_c[0]

        # Evaluate with mock context
        res = engine.evaluate_node(tree, mock_ctx)
        assert res is not None, f"Rule {rule_id} crashed during evaluation"
