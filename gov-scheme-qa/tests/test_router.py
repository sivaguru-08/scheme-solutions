"""
Stage 8 Test Suite: Deterministic Query Router.
Tests all 6 routes:
1. DIRECT_LOOKUP
2. RULE_ENGINE
3. MULTI_SCHEME (including scheme = null)
4. COMPARISON
5. SEARCH (including scheme = null)
6. ABSTAIN
"""

import sys
import os
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engine.router import DeterministicRouter, RouteDestination

@pytest.fixture
def router():
    return DeterministicRouter()

# 1. DIRECT_LOOKUP
def test_route_direct_lookup_benefits(router):
    dec = router.route(
        query="What are the benefits of ONORC?",
        scheme_id="SCH_ONORC",
        intent="BENEFITS",
        confidence=0.95
    )
    assert dec.destination == RouteDestination.DIRECT_LOOKUP
    assert dec.target_scheme_id == "SCH_ONORC"

def test_route_direct_lookup_documents(router):
    dec = router.route(
        query="Required documents for PM Vishwakarma",
        scheme_id="SCH_VISHWA",
        intent="DOCUMENTS",
        confidence=0.90
    )
    assert dec.destination == RouteDestination.DIRECT_LOOKUP

# 2. RULE_ENGINE
def test_route_rule_engine_eligibility_check(router):
    dec = router.route(
        query="I am 25 years old earning 12000 per month. Am I eligible for PM-SYM?",
        scheme_id="SCH_PMSYM",
        intent="CHECK_ELIGIBILITY",
        entities={"age": 25, "income": 12000}
    )
    assert dec.destination == RouteDestination.RULE_ENGINE
    assert dec.target_scheme_id == "SCH_PMSYM"

def test_route_rule_engine_via_slots_detection(router):
    dec = router.route(
        query="Can a farmer aged 35 join PM-KISAN?",
        scheme_id="SCH_PMKISAN",
        intent="ELIGIBILITY",
        entities={"age": 35, "occupation": "FARMER"}
    )
    assert dec.destination == RouteDestination.RULE_ENGINE

# 3. MULTI_SCHEME (scheme = None)
def test_route_multi_scheme_list_intent(router):
    dec = router.route(
        query="List all government schemes",
        scheme_id=None,
        intent="LIST_SCHEMES"
    )
    assert dec.destination == RouteDestination.MULTI_SCHEME
    assert dec.target_scheme_id is None

def test_route_multi_scheme_category_inquiry(router):
    dec = router.route(
        query="Show me all schemes for farmers",
        scheme_id=None,
        intent="OVERVIEW"
    )
    assert dec.destination == RouteDestination.MULTI_SCHEME

# 4. COMPARISON
def test_route_comparison_two_schemes(router):
    dec = router.route(
        query="Compare PMJJBY vs PMSBY",
        scheme_id=None,
        detected_schemes=["SCH_PMJJBY", "SCH_PMSBY"]
    )
    assert dec.destination == RouteDestination.COMPARISON
    assert "SCH_PMJJBY" in dec.target_scheme_ids
    assert "SCH_PMSBY" in dec.target_scheme_ids

def test_route_comparison_difference_keyword(router):
    dec = router.route(
        query="What is the difference between PM-SYM and APY?",
        scheme_id="SCH_PMSYM",
        detected_schemes=["SCH_PMSYM", "SCH_APY"]
    )
    assert dec.destination == RouteDestination.COMPARISON

# 5. SEARCH (scheme = None)
def test_route_search_free_text(router):
    dec = router.route(
        query="How does the Aadhaar authentication machine work at ration shops?",
        scheme_id=None,
        intent="OVERVIEW",
        confidence=0.75
    )
    assert dec.destination == RouteDestination.SEARCH
    assert dec.target_scheme_id is None

# 6. ABSTAIN
def test_route_abstain_out_of_scope(router):
    dec = router.route(
        query="What is the capital of Australia?",
        scheme_id=None,
        intent="OUT_OF_SCOPE",
        confidence=0.99
    )
    assert dec.destination == RouteDestination.ABSTAIN

def test_route_abstain_low_confidence(router):
    dec = router.route(
        query="xyz abc random string",
        scheme_id=None,
        intent="OVERVIEW",
        confidence=0.10
    )
    assert dec.destination == RouteDestination.ABSTAIN

def test_route_abstain_empty_query(router):
    dec = router.route(query="   ", scheme_id=None)
    assert dec.destination == RouteDestination.ABSTAIN
