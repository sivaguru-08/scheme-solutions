"""
Intelligence Upgrade Regression Tests (Tests A-J)
Tests for the final intelligence and answer-quality upgrade.

These tests verify:
- Structured profile parsing (Test A)
- Targeted concise answers (Tests B, C)
- Multi-scheme context & switching (Tests D, E)
- Ambiguous scheme clarification (Test F)
- Profile-only statements (Test G)
- Out-of-scope rejection (Test H)
- Follow-up slot extraction (Test I)
- Pension scheme discovery (Test J)
"""
import pytest
import sys
sys.path.insert(0, "/home/sivaguru/Documents/slm/gov-scheme-qa")

from schemas.models import QueryRequest, UserDemographics
from engine.pipeline import MasterQAPipeline
from models.entity_extractor import DeterministicEntityExtractor
from models.scheme_resolver import SchemeResolver


@pytest.fixture(scope="module")
def pipeline():
    return MasterQAPipeline()


@pytest.fixture(scope="module")
def extractor():
    return DeterministicEntityExtractor()


@pytest.fixture(scope="module")
def resolver():
    return SchemeResolver()


# =====================================================================
# Test A: Structured Profile Parsing
# =====================================================================
class TestA_StructuredProfileParsing:
    def test_form_field_extraction(self, extractor):
        """Verify that structured form-like input extracts all fields correctly."""
        slots, demo = extractor.extract_entities(
            "Name: Rahul Sharma Profession: Senior Civil Engineer Age: 32 "
            "Employment Status: Regular Full-Time Private Employee Monthly Salary: ₹65,000 "
            "Location: Bangalore"
        )
        assert demo.name == "Rahul Sharma"
        assert demo.age == 32
        assert demo.occupation is not None
        assert "engineer" in demo.occupation.lower() or "civil" in demo.occupation.lower()
        assert demo.employment_status == "EMPLOYED"
        assert demo.monthly_income == 65000.0
        assert demo.location == "Bangalore"
        assert demo.residence_state == "Karnataka"

    def test_rahul_sharma_not_a_scheme(self, resolver):
        """Verify human names are never resolved as schemes."""
        result = resolver.resolve("Name: Rahul Sharma Profession: Senior Civil Engineer")
        assert not result.matched_scheme_ids
        assert not result.is_ambiguous

    def test_profile_only_detection(self, pipeline):
        """Profile-only input without a question should NOT trigger recommendation."""
        r = pipeline.process_query(QueryRequest(
            query="Name: Rahul Sharma Profession: Senior Civil Engineer Age: 32 "
                  "Employment Status: Regular Full-Time Private Employee Monthly Salary: ₹65,000 "
                  "Location: Bangalore",
            conversation_id="test_a_profile"
        ))
        assert r.intent == "PROFILE_STATEMENT"
        assert "profile" in r.answer.lower() or "recorded" in r.answer.lower()
        assert r.global_outcome == "PROFILE_RECORDED"


# =====================================================================
# Test B: SVANidhi First Loan Amount (Targeted Answer)
# =====================================================================
class TestB_SVANidhiFirstLoan:
    def test_first_loan_amount_concise(self, pipeline):
        """After asking about SVANidhi, 'How much is the first loan?' must return concise answer."""
        conv_id = "test_b_svanidhi"
        r1 = pipeline.process_query(QueryRequest(query="Tell me about PM SVANidhi", conversation_id=conv_id))
        assert "SVANidhi" in r1.answer or "Street Vendor" in r1.answer

        r2 = pipeline.process_query(QueryRequest(query="How much is the first loan amount?", conversation_id=conv_id))
        assert "10,000" in r2.answer or "10000" in r2.answer
        assert "[Source:" in r2.answer
        # Should NOT dump full benefits template
        assert "### Benefits of" not in r2.answer

    def test_requested_info_extraction(self, extractor):
        """Verify FIRST_LOAN_AMOUNT is detected in requested_information."""
        slots, _ = extractor.extract_entities("How much is the first loan amount?")
        assert "FIRST_LOAN_AMOUNT" in slots.requested_information


# =====================================================================
# Test C: Vishwakarma Loan Follow-up (Targeted Answer)
# =====================================================================
class TestC_VishwakarmaLoan:
    def test_loan_amount_concise(self, pipeline):
        """After asking about Vishwakarma, 'How much loan?' must return concise answer."""
        conv_id = "test_c_vishwa"
        r1 = pipeline.process_query(QueryRequest(query="Tell me about PM Vishwakarma", conversation_id=conv_id))
        assert "Vishwakarma" in r1.answer

        r2 = pipeline.process_query(QueryRequest(query="How much loan can I get?", conversation_id=conv_id))
        assert "1 lakh" in r2.answer or "1,00,000" in r2.answer or "100000" in r2.answer
        assert "[Source:" in r2.answer


# =====================================================================
# Test D: Switch to PMUY (Topic Change)
# =====================================================================
class TestD_SwitchToPMUY:
    def test_topic_change_to_pmuy(self, pipeline):
        """Switching from Vishwakarma to PMUY should show PMUY overview."""
        conv_id = "test_d_pmuy"
        pipeline.process_query(QueryRequest(query="Tell me about PM Vishwakarma", conversation_id=conv_id))
        r2 = pipeline.process_query(QueryRequest(query="What about PMUY?", conversation_id=conv_id))
        assert "Ujjwala" in r2.answer or "PMUY" in r2.answer
        assert any("Ujjwala" in s or "PMUY" in s for s in r2.detected_schemes)


# =====================================================================
# Test E: Go Back to First Scheme (Context Stack Resolution)
# =====================================================================
class TestE_GoBackToFirstScheme:
    def test_ordinal_resolution_from_context_stack(self, pipeline):
        """'Go back to the first scheme' should resolve to Vishwakarma from context stack."""
        conv_id = "test_e_goback"
        # Discuss Vishwakarma first
        pipeline.process_query(QueryRequest(query="Tell me about PM Vishwakarma", conversation_id=conv_id))
        # Switch to PMUY
        pipeline.process_query(QueryRequest(query="What about PMUY?", conversation_id=conv_id))
        # Go back to first scheme
        r3 = pipeline.process_query(QueryRequest(query="Go back to the first scheme, what are the benefits?", conversation_id=conv_id))
        assert "Vishwakarma" in r3.answer
        assert r3.intent == "BENEFITS"


# =====================================================================
# Test F: Ambiguous Indira Gandhi Scheme (Clarification)
# =====================================================================
class TestF_AmbiguousIndiraGandhi:
    def test_ambiguous_clarification(self, pipeline):
        """'Tell me about the Indira Gandhi scheme' should trigger clarification."""
        r = pipeline.process_query(QueryRequest(
            query="Tell me about the Indira Gandhi scheme",
            conversation_id="test_f_ambig"
        ))
        assert r.intent == "CLARIFICATION"
        assert "Old Age" in r.answer or "IGNOAPS" in r.answer
        assert "Widow" in r.answer or "IGNWPS" in r.answer
        assert "Disability" in r.answer or "IGNDPS" in r.answer

    def test_disambiguated_old_age(self, resolver):
        """'Indira Gandhi old age pension' should resolve to SCH_NSAP_OA."""
        result = resolver.resolve("Tell me about Indira Gandhi old age pension")
        assert "SCH_NSAP_OA" in result.matched_scheme_ids

    def test_disambiguated_widow(self, resolver):
        """'Indira Gandhi widow pension' should resolve to SCH_NSAP_W."""
        result = resolver.resolve("Tell me about Indira Gandhi widow pension")
        assert "SCH_NSAP_W" in result.matched_scheme_ids


# =====================================================================
# Test G: Profile-Only Natural Sentence
# =====================================================================
class TestG_ProfileOnlyNatural:
    def test_natural_profile_statement(self, pipeline):
        """Natural profile input without question should record profile only."""
        r = pipeline.process_query(QueryRequest(
            query="I am 32, a civil engineer, working full-time in Bangalore and earning ₹65,000",
            conversation_id="test_g_profile"
        ))
        assert r.intent == "PROFILE_STATEMENT"
        assert "recorded" in r.answer.lower() or "profile" in r.answer.lower()

    def test_working_not_mapped_to_occupation(self, extractor):
        """'I am working' should set employment_status=EMPLOYED, NOT occupation='working'."""
        slots, demo = extractor.extract_entities("I am working in Bangalore")
        assert demo.employment_status == "EMPLOYED"
        assert demo.occupation != "working"


# =====================================================================
# Test H: Out-of-Scope (Weather)
# =====================================================================
class TestH_OutOfScope:
    def test_weather_query(self, pipeline):
        r = pipeline.process_query(QueryRequest(
            query="What is the weather in Delhi today?",
            conversation_id="test_h_oos"
        ))
        assert r.intent == "OUT_OF_SCOPE"
        assert "outside" in r.answer.lower() or "knowledge base" in r.answer.lower()

    def test_recipe_query(self, pipeline):
        r = pipeline.process_query(QueryRequest(
            query="How do I bake a chocolate cake?",
            conversation_id="test_h_oos2"
        ))
        assert r.intent == "OUT_OF_SCOPE"


# =====================================================================
# Test I: Follow-Up Slot Extraction (Age = 68)
# =====================================================================
class TestI_FollowUpSlot:
    def test_elderly_then_age_68(self, pipeline):
        """After 'I am old, what can I get?', providing '68' should produce recommendations."""
        conv_id = "test_i_slot"
        r1 = pipeline.process_query(QueryRequest(
            query="I am an old man, could I get any cash from the government?",
            conversation_id=conv_id
        ))
        assert r1.intent == "MULTI_SCHEME_RECOMMENDATION"
        assert r1.pending_question is not None
        assert "age" in r1.pending_question.lower()

        r2 = pipeline.process_query(QueryRequest(query="68", conversation_id=conv_id))
        assert r2.global_outcome == "ANSWER_PRODUCED"
        assert len(r2.candidate_schemes) >= 2


# =====================================================================
# Test J: Pension Schemes for 68-Year-Old
# =====================================================================
class TestJ_PensionSchemes:
    def test_pension_for_68(self, pipeline):
        """'Which pension schemes can I get? I am 68 years old' should return pension schemes."""
        r = pipeline.process_query(QueryRequest(
            query="Which pension schemes can I get? I am 68 years old.",
            conversation_id="test_j_pension"
        ))
        assert r.global_outcome == "ANSWER_PRODUCED"
        assert len(r.candidate_schemes) >= 1
        # Should contain pension-related schemes
        assert any("NSAP" in s or "pension" in s.lower() for s in r.candidate_schemes) or \
               "pension" in r.answer.lower() or "Annapurna" in r.answer


# =====================================================================
# Test: Unknown Scheme Detection
# =====================================================================
class TestUnknownScheme:
    def test_e_shram_unknown(self, pipeline):
        """'e-Shram' should be recognized as outside knowledge base, not fall back to previous scheme."""
        r = pipeline.process_query(QueryRequest(
            query="Tell me about thee-shram scheme",
            conversation_id="test_unknown_scheme"
        ))
        assert r.intent == "UNKNOWN_SCHEME"
        assert "knowledge base" in r.answer.lower() or "not part" in r.answer.lower()

    def test_unknown_does_not_lock(self, pipeline):
        """After asking about a known scheme, unknown scheme should NOT reuse the previous scheme."""
        conv_id = "test_unknown_lock"
        pipeline.process_query(QueryRequest(query="Tell me about APY", conversation_id=conv_id))
        r2 = pipeline.process_query(QueryRequest(query="Tell me about thee-shram scheme", conversation_id=conv_id))
        assert r2.intent == "UNKNOWN_SCHEME"
        # Must NOT show APY overview/details (the word 'Atal Pension' may appear as an example in the message)
        assert "### Atal Pension" not in r2.answer
        assert "PFRDA" not in r2.answer


# =====================================================================
# Test: Paraphrase Handling
# =====================================================================
class TestParaphrases:
    def test_loan_paraphrases(self, extractor):
        """Multiple paraphrases for loan amount should all extract LOAN_AMOUNT."""
        for q in [
            "How much loan can I get?",
            "What is the loan amount?",
            "How much does it lend?",
            "What is the credit limit?"
        ]:
            slots, _ = extractor.extract_entities(q)
            assert "LOAN_AMOUNT" in slots.requested_information, f"Failed for: {q}"

    def test_eligibility_paraphrases(self, extractor):
        """Multiple paraphrases for eligibility should all extract ELIGIBILITY."""
        for q in [
            "Am I eligible?",
            "Can I apply?",
            "Do I qualify?",
            "Who can apply?"
        ]:
            slots, _ = extractor.extract_entities(q)
            assert "ELIGIBILITY" in slots.requested_information, f"Failed for: {q}"
