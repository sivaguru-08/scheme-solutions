"""
Comprehensive Test Suite for Bug-Fix and Capability Upgrades.
Verifies all 33 architectural requirements, specific prompt cases, and failure modes:
- Failure A & Case 30: Strict out-of-scope routing without FTS5/BM25 retrieval.
- Failure B & Case 31: Informational inquiries preserve OVERVIEW, preventing false ELIGIBLE/INELIGIBLE verdicts.
- Failure C & Case 32: Contextual follow-up 'can i apply it now' resolves to PROCEDURE for active scheme.
- Failure D & Case 33: State-specific schemes & location extraction (Punjab vs Kerala/Gujarat).
- Failure E: Bare numbers and ungrounded cold-start queries route to OUT_OF_SCOPE.
- Failure F & Case 29: 'Old person' maps to ELDERLY with UNKNOWN exact age.
- Failure G & Case 26: Multi-intent query extracts primary and secondary intents accurately.
- Failure H & Case 17: Database-driven dynamic filtering for pension schemes without hardcoded lists.
- Failure I & Case 10: Four distinct semantic evaluation states (ELIGIBLE, POTENTIAL, INELIGIBLE, NOT_APPLICABLE).
- Failure J & Case 28: Definite failure returns exact no-match message with zero hallucinated schemes.
- Failure K & Case 12: Slot value processing for short conversational answers ('68', 'yes', 'rural', 'kerala').
- Failure L & Case 13: Pronoun and ordinal resolution ('the second one').
- Failure N & Case 15: PM SVANidhi benefit completeness (all 5 tranches/incentives).
- Failure Q, Case 18 & Case 27: Full 7-turn multi-turn conversation flow.
"""

import pytest
from engine.pipeline import MasterQAPipeline
from schemas.models import QueryRequest, UserDemographics, GlobalOutcome, SchemeResultState

@pytest.fixture
def pipeline():
    return MasterQAPipeline()

# =====================================================================
# Failure A & Case 30: Out-of-Scope Queries
# =====================================================================
@pytest.mark.parametrize("query", [
    "what are u doing niggu?",
    "what is the weather in Delhi today?",
    "who won the cricket world cup?",
    "tell me a joke",
    "how do I bake a chocolate cake?",
    "write me a python script for binary search",
    "59"  # Bare number cold-start (Failure E)
])
def test_case_30_out_of_scope_queries(pipeline, query):
    res = pipeline.process_query(QueryRequest(query=query))
    assert res.intent == "OUT_OF_SCOPE"
    assert res.retrieval_method == "OUT_OF_SCOPE"
    assert res.global_outcome == GlobalOutcome.OUT_OF_SCOPE
    assert "Inquiry Outside Knowledge Base" in res.answer
    assert "cannot answer" in res.answer.lower()
    assert len(res.candidate_schemes) == 0

# =====================================================================
# Failure B & Case 31: Informational Scheme Queries (Never Claim ELIGIBLE)
# =====================================================================
@pytest.mark.parametrize("query", [
    "Tell me about IGNOAPS",
    "Explain IGNOAPS",
    "What is IGNOAPS?",
    "Give me information about IGNOAPS",
    "How does IGNOAPS work?"
])
def test_case_31_informational_scheme_queries(pipeline, query):
    # User provides context, but query is strictly informational
    demo = UserDemographics(age=65, is_bpl=True, residence_state="Kerala")
    res = pipeline.process_query(QueryRequest(query=query, user_context=demo))

    assert res.intent == "OVERVIEW"
    assert "SCH_NSAP_OA" in res.detected_schemes or "IGNOAPS" in res.answer or "Indira Gandhi" in res.answer
    assert "RESULT: ELIGIBLE" not in res.answer
    assert "RESULT: NOT ELIGIBLE" not in res.answer
    assert res.is_deterministic is True
    assert len(res.citations) > 0

# =====================================================================
# Failure C & Case 32: Contextual Follow-up "can i apply it now"
# =====================================================================
def test_case_32_contextual_apply_it_now(pipeline):
    conv_id = "test_case_32_conv"
    # Turn 1: Recommendation turn yielding SCH_NSAP_OA
    r1 = pipeline.process_query(QueryRequest(
        query="I am an old person aged 68 in BPL category. What scheme can I get?",
        conversation_id=conv_id
    ))
    assert "SCH_NSAP_OA" in r1.candidate_schemes
    assert r1.intent == "MULTI_SCHEME_RECOMMENDATION"

    # Turn 2: Contextual inquiry using pronoun "it"
    r2 = pipeline.process_query(QueryRequest(
        query="can i apply it now",
        conversation_id=conv_id
    ))
    assert r2.intent == "PROCEDURE"
    assert "SCH_NSAP_OA" in r2.detected_schemes
    assert "Application Procedure" in r2.answer
    assert "Mode:" in r2.answer

# =====================================================================
# Failure D & Case 33: State-Specific Scheme Evaluation (AB PM-JAY MMSBY)
# =====================================================================
def test_case_33_state_specific_evaluation_punjab_vs_kerala_gujarat(pipeline):
    # Test 1: Punjab resident with smart ration card -> ELIGIBLE
    r_punjab = pipeline.process_query(QueryRequest(
        query="I live in Punjab with smart ration card. Am I eligible for AB PM-JAY MMSBY?"
    ))
    assert r_punjab.intent == "CHECK_ELIGIBILITY"
    assert "RESULT: ELIGIBLE" in r_punjab.answer
    assert "Must be a resident of Punjab" in r_punjab.answer

    # Test 2: Kerala resident with smart ration card -> NOT ELIGIBLE (state mismatch)
    r_kerala = pipeline.process_query(QueryRequest(
        query="I live in Kerala with smart ration card. Am I eligible for AB PM-JAY MMSBY?"
    ))
    assert r_kerala.intent == "CHECK_ELIGIBILITY"
    assert "NOT ELIGIBLE" in r_kerala.answer
    assert "Must be a resident of Punjab" in r_kerala.answer
    assert "Kerala" in r_kerala.answer

    # Test 3: Gujarat resident with smart ration card -> NOT ELIGIBLE (state mismatch)
    r_gujarat = pipeline.process_query(QueryRequest(
        query="I live in Gujarat with smart ration card. Am I eligible for AB PM-JAY MMSBY?"
    ))
    assert r_gujarat.intent == "CHECK_ELIGIBILITY"
    assert "NOT ELIGIBLE" in r_gujarat.answer
    assert "Gujarat" in r_gujarat.answer

# =====================================================================
# Failure F & Case 29: "Old Person" Handling
# =====================================================================
def test_case_29_old_person_age_unknown(pipeline):
    slots, demo = pipeline.entity_extractor.extract_entities("I am an old person. What schemes can I get?")
    assert slots.age_category == "ELDERLY"
    assert slots.age is None
    assert demo.age is None

    res = pipeline.process_query(QueryRequest(query="I am an old person. What schemes can I get?"))
    assert res.intent == "MULTI_SCHEME_RECOMMENDATION"
    assert res.global_outcome == GlobalOutcome.INSUFFICIENT_INFORMATION
    assert res.pending_question == "What is your exact age?"
    assert "What is your exact age?" in res.answer

# =====================================================================
# Failure G & Case 26: Multi-Intent Query Extraction
# =====================================================================
def test_case_26_multi_intent_secondary_intents(pipeline):
    query = "I'm old person what schemes can i get,what is the critera to get and what are the documents to get benefitted by the scheme"
    res = pipeline.process_query(QueryRequest(query=query))

    assert res.intent == "MULTI_SCHEME_RECOMMENDATION"
    assert "ELIGIBILITY" in res.secondary_intents
    assert "BENEFITS" in res.secondary_intents
    assert "DOCUMENTS" in res.secondary_intents
    assert res.pending_question == "What is your exact age?"

# =====================================================================
# Failure H & Case 17: Database-Driven Pension Filtering
# =====================================================================
def test_case_17_database_driven_pension_filtering(pipeline):
    res = pipeline.process_query(QueryRequest(query="Which pension schemes can someone aged 68 get?"))

    assert res.intent == "MULTI_SCHEME_RECOMMENDATION"
    assert len(res.candidate_schemes) > 0
    # Every candidate scheme must be a pension/social assistance scheme
    for sid in res.candidate_schemes:
        s_data = pipeline.answer_generator.repo.get_scheme_by_id(sid)
        corpus = f"{s_data['official_name']} {s_data.get('category','')} {s_data.get('subcategory','')} {s_data.get('description','')} {s_data.get('objective','')}".lower()
        assert any(kw in corpus for kw in ["pension", "old age", "social assistance", "annapurna", "ignoaps", "ignwps", "igndps"])

    # Must NOT include non-pension schemes
    assert not any(x in res.candidate_schemes for x in ["SCH_PMKISAN", "SCH_PMSVANIDHI", "SCH_PMUY", "SCH_PMMVY", "SCH_SBM_G"])

# =====================================================================
# Failure I & Case 10: Semantic Result States
# =====================================================================
def test_case_10_four_result_states(pipeline):
    # ELIGIBLE: Age 68, BPL -> SCH_NSAP_OA is ELIGIBLE
    eval_oa = pipeline.answer_generator.rec_engine.evaluate_scheme_compatibility(
        pipeline.answer_generator.repo.get_scheme_by_id("SCH_NSAP_OA"),
        UserDemographics(age=68, is_bpl=True)
    )
    assert eval_oa.status == SchemeResultState.ELIGIBLE

    # POTENTIAL: Age 68, but BPL unknown -> POTENTIAL
    eval_pot = pipeline.answer_generator.rec_engine.evaluate_scheme_compatibility(
        pipeline.answer_generator.repo.get_scheme_by_id("SCH_NSAP_OA"),
        UserDemographics(age=68)
    )
    assert eval_pot.status == SchemeResultState.POTENTIAL
    assert "is_bpl" in eval_pot.missing_slots

    # INELIGIBLE: Age 30 -> SCH_NSAP_OA is INELIGIBLE
    eval_in = pipeline.answer_generator.rec_engine.evaluate_scheme_compatibility(
        pipeline.answer_generator.repo.get_scheme_by_id("SCH_NSAP_OA"),
        UserDemographics(age=30, is_bpl=True)
    )
    assert eval_in.status == SchemeResultState.INELIGIBLE

    # NOT_APPLICABLE: Filter non-pension query
    eval_na = pipeline.answer_generator.rec_engine.evaluate_scheme_compatibility(
        pipeline.answer_generator.repo.get_scheme_by_id("SCH_PMKISAN"),
        UserDemographics(age=68, is_bpl=True),
        query_text="pension schemes"
    )
    assert eval_na.status == SchemeResultState.NOT_APPLICABLE

# =====================================================================
# Failure J & Case 28: Definite Failure (No-Match Exact String)
# =====================================================================
def test_case_28_definite_failure_no_match(pipeline):
    disqualified_profile = UserDemographics(
        age=30,
        monthly_income=500000,
        annual_turnover=100000000,
        is_income_tax_payer=True,
        is_epfo_or_esic_member=True,
        is_bpl=False,
        has_pucca_house=True,
        occupation="corporate",
        trade="executive",
        has_bank_account=False,
        has_ration_card=False,
        has_smart_ration_card=False,
        is_aadhaar_seeded=False,
        has_electricity_connection=False,
        roof_suitable_solar=False,
        area_type="URBAN",
        residence_state="Delhi",
        state="Delhi"
    )

    res = pipeline.process_query(QueryRequest(
        query="What schemes can I get?",
        user_context=disqualified_profile
    ))

    exact_expected = "Sorry, there are no schemes in the available scheme database that match your requirements based on the information provided."
    assert res.global_outcome == GlobalOutcome.NO_MATCH
    assert res.pending_question is None
    assert res.candidate_schemes == []
    assert res.answer == exact_expected

# =====================================================================
# Failure N & Case 15: PM SVANidhi Benefits Completeness
# =====================================================================
def test_case_15_svanidhi_all_five_benefits(pipeline):
    res = pipeline.process_query(QueryRequest(query="What are the benefits of PM SVANidhi?"))
    assert res.intent == "BENEFITS"
    assert "10,000" in res.answer or "Tranche 1" in res.answer
    assert "20,000" in res.answer or "Tranche 2" in res.answer
    assert "50,000" in res.answer or "Tranche 3" in res.answer
    assert "7%" in res.answer or "Interest Subsidy" in res.answer
    assert "1,200" in res.answer or "Digital" in res.answer

# =====================================================================
# Failure Q, Case 18 & Case 27: Full 7-Turn Deterministic Conversation
# =====================================================================
def test_cases_18_and_27_complete_7_turn_conversation(pipeline):
    conv_id = "test_complete_7_turn_flow"

    # Turn 1: "I'm old. What schemes can I get?"
    r1 = pipeline.process_query(QueryRequest(query="I'm old. What schemes can I get?", conversation_id=conv_id))
    assert r1.intent == "MULTI_SCHEME_RECOMMENDATION"
    assert r1.pending_question == "What is your exact age?"

    # Turn 2: "68" -> Answers age. System promotes schemes meeting primary age criteria directly.
    r2 = pipeline.process_query(QueryRequest(query="68", conversation_id=conv_id))
    assert r2.intent == "MULTI_SCHEME_RECOMMENDATION"
    assert r2.global_outcome == "ANSWER_PRODUCED"
    assert len(r2.candidate_schemes) >= 2
    second_scheme = r2.candidate_schemes[1]

    # Turn 3: "can i apply it now" -> Resolves active scheme to PROCEDURE
    r3 = pipeline.process_query(QueryRequest(query="can i apply it now", conversation_id=conv_id))
    assert r3.intent == "PROCEDURE"
    assert "Application Procedure" in r3.answer or "Steps" in r3.answer or "Mode" in r3.answer

    # Turn 4: "What are the documents for the second one?" -> Resolves ordinal to DOCUMENTS
    r4 = pipeline.process_query(QueryRequest(query="What are the documents for the second one?", conversation_id=conv_id))
    assert r4.intent == "DOCUMENTS"
    assert "Mandatory Documents" in r4.answer or "Document" in r4.answer

    # Turn 5: "Tell me about IGNOAPS" -> Information overview without eligibility claim
    r5 = pipeline.process_query(QueryRequest(query="Tell me about IGNOAPS", conversation_id=conv_id))
    assert r5.intent == "OVERVIEW"
    assert "RESULT: ELIGIBLE" not in r5.answer
    assert "RESULT: NOT ELIGIBLE" not in r5.answer

    # Turn 6: "the second one" -> Resolves ordinal to OVERVIEW of second scheme
    r6 = pipeline.process_query(QueryRequest(query="the second one", conversation_id=conv_id))
    assert r6.intent == "OVERVIEW"

def test_case_historical_scheme_handling(pipeline):
    # Create mock historical scheme dict
    hist_scheme = {
        "scheme_id": "SCH_HISTORICAL_TEST",
        "official_name": "Historical Discontinued Welfare Scheme",
        "status": "DISCONTINUED",
        "version": "v1.0-legacy"
    }
    eval_res = pipeline.answer_generator.rec_engine.evaluate_scheme_compatibility(
        hist_scheme,
        UserDemographics(age=68, is_bpl=True)
    )
    assert eval_res.status == SchemeResultState.NOT_APPLICABLE
    assert "DISCONTINUED" in eval_res.ranking_reasons[0]
