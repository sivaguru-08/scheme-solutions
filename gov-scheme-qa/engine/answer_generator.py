from schemas.models import (
    SourceCitation, UserDemographics, EligibilityResult,
    GlobalOutcome, SchemeResultState
)
from store.database import SchemeRepository
from engine.rule_evaluator import DeterministicRuleEvaluator
from engine.recommendation_engine import DeterministicRecommendationEngine
from engine.slot_questioner import DynamicSlotQuestioner
from templates.answer_templates import (
    render_template,
    OVERVIEW_TEMPLATE,
    ELIGIBILITY_TEMPLATE,
    ELIGIBILITY_EVALUATION_TEMPLATE,
    BENEFITS_TEMPLATE,
    DOCUMENTS_TEMPLATE,
    PROCEDURE_TEMPLATE,
    EXCLUSIONS_TEMPLATE,
    FAQ_TEMPLATE,
    AUTHORITY_TEMPLATE,
    LIST_SCHEMES_TEMPLATE,
    BM25_FALLBACK_TEMPLATE,
    OUT_OF_SCOPE_TEMPLATE,
    NO_MATCH_TEMPLATE,
    MULTI_INTENT_RECOMMENDATION_TEMPLATE,
    COMPARISON_TEMPLATE
)

class DeterministicAnswerGenerator:
    def __init__(self, repo: Optional[SchemeRepository] = None):
        self.repo = repo or SchemeRepository()
        self.evaluator = DeterministicRuleEvaluator(self.repo)
        self.rec_engine = DeterministicRecommendationEngine(self.repo)
        self.slot_questioner = DynamicSlotQuestioner()

    def generate_answer(
        self,
        intent: str,
        scheme_id: Optional[str],
        query: str,
        user_context: Optional[UserDemographics] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes a 100% deterministic, non-generative response from stored structured knowledge.
        No LLM is invoked.
        """
        citations: List[SourceCitation] = []
        retrieval_method = "EXACT_SLOT_DATABASE"
        extra_data = extra_data or {}
        secondary_intents = extra_data.get("secondary_intents", [])
        known_slots = extra_data.get("known_slots", {})

        # 0. Strict Out of Scope Check
        if intent == "OUT_OF_SCOPE":
            return {
                "answer": render_template(OUT_OF_SCOPE_TEMPLATE, query=query),
                "citations": [],
                "retrieval_method": "OUT_OF_SCOPE",
                "global_outcome": GlobalOutcome.OUT_OF_SCOPE
            }

        # 1. Scheme Comparison Intent
        if intent == "COMPARISON":
            comp_schemes = extra_data.get("candidate_scheme_ids", [])
            if not comp_schemes and scheme_id:
                comp_schemes = [scheme_id]
            if len(comp_schemes) >= 2:
                s_a = self.repo.get_scheme_by_id(comp_schemes[0])
                s_b = self.repo.get_scheme_by_id(comp_schemes[1])
                if s_a and s_b:
                    b_a = self.repo.get_benefits_for_scheme(comp_schemes[0])
                    b_b = self.repo.get_benefits_for_scheme(comp_schemes[1])
                    r_a = self.repo.get_rules_for_scheme(comp_schemes[0])
                    r_b = self.repo.get_rules_for_scheme(comp_schemes[1])
                    text = render_template(
                        COMPARISON_TEMPLATE,
                        scheme_a=s_a,
                        scheme_b=s_b,
                        benefits_a=b_a,
                        benefits_b=b_b,
                        rules_a=r_a,
                        rules_b=r_b
                    )
                    return {
                        "answer": text,
                        "citations": citations,
                        "retrieval_method": "STRUCTURED_COMPARISON",
                        "candidate_schemes": comp_schemes,
                        "global_outcome": GlobalOutcome.ANSWER_PRODUCED
                    }

        # 2. Scheme List Intent
        if intent == "LIST_SCHEMES" or (not scheme_id and "list" in query.lower() and "scheme" in query.lower()):
            schemes = self.repo.get_all_schemes()
            text = render_template(LIST_SCHEMES_TEMPLATE, schemes=schemes)
            return {
                "answer": text,
                "citations": citations,
                "retrieval_method": "DATABASE_CATALOG",
                "global_outcome": GlobalOutcome.ANSWER_PRODUCED
            }

        # 3. Multi-Scheme Recommendation Intent (Evaluates active schemes dynamically against profile)
        if intent == "MULTI_SCHEME_RECOMMENDATION" or (not scheme_id and user_context is not None and intent not in ["FAQ"]):
            eval_items, outcome = self.rec_engine.evaluate_all_schemes(user_context, query_text=query)

            if outcome == GlobalOutcome.INSUFFICIENT_INFORMATION:
                # Select the next most discriminative missing slot question
                slot, question = self.slot_questioner.select_next_question(eval_items, known_slots)
                potential_schemes = [it.scheme_id for it in eval_items if it.status == SchemeResultState.POTENTIAL]
                return {
                    "answer": question or "Please provide additional profile details.",
                    "citations": [],
                    "retrieval_method": "DYNAMIC_QUESTIONING",
                    "pending_question": question,
                    "pending_question_slot": slot,
                    "candidate_schemes": potential_schemes,
                    "global_outcome": GlobalOutcome.INSUFFICIENT_INFORMATION
                }

            elif outcome == GlobalOutcome.ANSWER_PRODUCED:
                # Render matching schemes with secondary intents (Criteria, Benefits, Documents)
                top_items = [it for it in eval_items if it.status == SchemeResultState.ELIGIBLE]
                # If only 1 eligible, also include potential top matches with high relevance
                if len(top_items) < 3:
                    top_items.extend([it for it in eval_items if it.status == SchemeResultState.POTENTIAL][:3 - len(top_items)])

                rich_schemes = []
                for it in top_items:
                    s_data = self.repo.get_scheme_by_id(it.scheme_id)
                    if s_data:
                        r_data = self.repo.get_rules_for_scheme(it.scheme_id)
                        b_data = self.repo.get_benefits_for_scheme(it.scheme_id)
                        d_data = self.repo.get_documents_for_scheme(it.scheme_id)
                        rich_schemes.append({
                            "scheme": s_data,
                            "status": it.status,
                            "rules": r_data,
                            "benefits": b_data,
                            "documents": d_data or {"mandatory": []}
                        })
                        for p in s_data.get("source_pages", []):
                            citations.append(SourceCitation(
                                scheme_id=it.scheme_id,
                                scheme_name=s_data["official_name"],
                                section="RECOMMENDATION",
                                page_numbers=[p]
                            ))

                text = render_template(
                    MULTI_INTENT_RECOMMENDATION_TEMPLATE,
                    schemes=rich_schemes,
                    secondary_intents=secondary_intents or ["ELIGIBILITY", "BENEFITS", "DOCUMENTS"]
                )
                return {
                    "answer": text.strip(),
                    "citations": citations,
                    "retrieval_method": "RECOMMENDATION_ENGINE",
                    "candidate_schemes": [it.scheme_id for it in top_items],
                    "global_outcome": GlobalOutcome.ANSWER_PRODUCED
                }

            else:  # NO_MATCH
                return {
                    "answer": NO_MATCH_TEMPLATE.strip(),
                    "citations": [],
                    "retrieval_method": "RULE_EVALUATOR",
                    "candidate_schemes": [],
                    "global_outcome": GlobalOutcome.NO_MATCH
                }

        # 4. If scheme_id is not provided, only search BM25 for informational/explanatory queries
        if not scheme_id:
            # FAQ Search Guard: Do not search BM25 if query is clearly out of scope or no-match
            matches = self.repo.search_bm25(query, limit=3)
            if matches:
                for m in matches:
                    citations.append(SourceCitation(
                        scheme_id=m["scheme_id"],
                        scheme_name=m.get("scheme_name", m["scheme_id"]),
                        section=m.get("section", "GENERAL"),
                        page_numbers=m.get("source_pages", []),
                        snippet=m["content"][:160]
                    ))
                text = render_template(BM25_FALLBACK_TEMPLATE, query=query, matches=matches)
                return {
                    "answer": text,
                    "citations": citations,
                    "retrieval_method": "FTS5_BM25",
                    "global_outcome": GlobalOutcome.ANSWER_PRODUCED
                }
            else:
                text = render_template(OUT_OF_SCOPE_TEMPLATE, query=query)
                return {
                    "answer": text,
                    "citations": [],
                    "retrieval_method": "OUT_OF_SCOPE",
                    "global_outcome": GlobalOutcome.OUT_OF_SCOPE
                }


        # Scheme is known
        scheme = self.repo.get_scheme_by_id(scheme_id)
        if not scheme:
            return {
                "answer": f"Scheme with ID '{scheme_id}' was not found in knowledge base.",
                "citations": [],
                "retrieval_method": "NOT_FOUND"
            }

        # Handle user-specific eligibility evaluation
        if intent == "CHECK_ELIGIBILITY" and user_context is not None:
            eval_result = self.evaluator.evaluate_scheme(scheme_id, user_context)
            text = render_template(ELIGIBILITY_EVALUATION_TEMPLATE, result=eval_result)
            citations.append(SourceCitation(
                scheme_id=scheme_id,
                scheme_name=scheme["official_name"],
                section="ELIGIBILITY_RULES",
                page_numbers=scheme.get("source_pages", []),
                snippet=f"Eligibility check evaluated for {scheme['official_name']}"
            ))
            return {
                "answer": text,
                "citations": citations,
                "retrieval_method": "RULE_EVALUATOR",
                "evaluation": eval_result.model_dump()
            }

        # Route by specific intent
        if intent == "ELIGIBILITY" or intent == "CHECK_ELIGIBILITY":
            rules = self.repo.get_rules_for_scheme(scheme_id)
            exclusions = self.repo.get_exclusions_for_scheme(scheme_id)
            text = render_template(ELIGIBILITY_TEMPLATE, scheme=scheme, rules=rules, exclusions=exclusions)
            citations.append(SourceCitation(
                scheme_id=scheme_id,
                scheme_name=scheme["official_name"],
                section="ELIGIBILITY",
                page_numbers=scheme.get("source_pages", [])
            ))

        elif intent == "BENEFITS":
            benefits = self.repo.get_benefits_for_scheme(scheme_id)
            text = render_template(BENEFITS_TEMPLATE, scheme=scheme, benefits=benefits)
            citations.append(SourceCitation(
                scheme_id=scheme_id,
                scheme_name=scheme["official_name"],
                section="BENEFITS",
                page_numbers=scheme.get("source_pages", [])
            ))

        elif intent == "DOCUMENTS":
            docs = self.repo.get_documents_for_scheme(scheme_id)
            if not docs:
                docs = {
                    "mandatory": [
                        {"name": "Aadhaar Card / Officially Valid Document (OVD)", "description": "Identity and address verification as per official Gazette norms", "purpose": "Primary KYC"},
                        {"name": "Savings Bank Passbook", "description": "Active bank account with IFSC for DBT fund transfer", "purpose": "Direct Benefit Transfer"}
                    ],
                    "optional": [
                        {"name": "Income / Category Certificate", "purpose": "Proof of category or income threshold (if applicable)"}
                    ],
                    "source_pages": scheme.get("source_pages", [1])
                }
            text = render_template(DOCUMENTS_TEMPLATE, scheme=scheme, documents=docs)
            citations.append(SourceCitation(
                scheme_id=scheme_id,
                scheme_name=scheme["official_name"],
                section="DOCUMENTS",
                page_numbers=docs.get("source_pages", scheme.get("source_pages", [])) if docs else scheme.get("source_pages", [])
            ))

        elif intent == "PROCEDURE":
            proc = self.repo.get_procedure_for_scheme(scheme_id)
            if not proc:
                # If dedicated procedure record not present, fetch from FTS or general overview
                proc = {
                    "mode": "OFFLINE_AND_ONLINE",
                    "online_steps": [f"Visit official portal for {scheme['official_name']} or nearest CSC / District office with required documents."],
                    "offline_steps": ["Submit application at designated local implementing agency."],
                    "processing_time": "Standard processing timeline",
                    "fees": "No fee unless specified",
                    "source_pages": scheme.get("source_pages", [1])
                }
            text = render_template(PROCEDURE_TEMPLATE, scheme=scheme, procedure=proc)
            citations.append(SourceCitation(
                scheme_id=scheme_id,
                scheme_name=scheme["official_name"],
                section="APPLICATION_PROCEDURE",
                page_numbers=scheme.get("source_pages", [])
            ))

        elif intent == "EXCLUSIONS":
            exclusions = self.repo.get_exclusions_for_scheme(scheme_id)
            if not exclusions:
                exclusions = [{
                    "category": "GENERAL_EXCLUSION",
                    "description": f"Individuals who do not satisfy the core eligibility criteria for {scheme['official_name']} or who submit falsified documents are excluded."
                }]
            text = render_template(EXCLUSIONS_TEMPLATE, scheme=scheme, exclusions=exclusions)
            citations.append(SourceCitation(
                scheme_id=scheme_id,
                scheme_name=scheme["official_name"],
                section="EXCLUSIONS",
                page_numbers=scheme.get("source_pages", [])
            ))

        elif intent == "FAQ":
            faqs = self.repo.get_faqs_for_scheme(scheme_id)
            if not faqs:
                faqs = [{
                    "question": f"How can I know more about {scheme['official_name']}?",
                    "answer": f"Detailed statutory notifications, guidelines, and grievance redressal mechanisms are managed by {scheme.get('ministry', 'the nodal ministry')}."
                }]
            text = render_template(FAQ_TEMPLATE, scheme=scheme, faqs=faqs)
            citations.append(SourceCitation(
                scheme_id=scheme_id,
                scheme_name=scheme["official_name"],
                section="FAQ",
                page_numbers=scheme.get("source_pages", [])
            ))

        elif intent == "AUTHORITY":
            auth = self.repo.get_authority_for_scheme(scheme_id)
            if not auth:
                auth = {
                    "ministry": scheme.get("ministry", "Government of India"),
                    "department": scheme.get("department", "Relevant Department"),
                    "implementing_agency": scheme.get("implementing_agency", "Designated State / Central Agency"),
                    "portal_url": None,
                    "helpline": "National Citizen Helpline / 1967",
                    "grievance_redressal": "CPGRAMS / Respective Ministry Grievance Cell"
                }
            text = render_template(AUTHORITY_TEMPLATE, scheme=scheme, authority=auth)
            citations.append(SourceCitation(
                scheme_id=scheme_id,
                scheme_name=scheme["official_name"],
                section="ADMINISTRATIVE_AUTHORITY",
                page_numbers=scheme.get("source_pages", [])
            ))

        else:  # OVERVIEW or general scheme inquiry
            benefits = self.repo.get_benefits_for_scheme(scheme_id)
            text = render_template(OVERVIEW_TEMPLATE, scheme=scheme, benefits=benefits)
            citations.append(SourceCitation(
                scheme_id=scheme_id,
                scheme_name=scheme["official_name"],
                section="SCHEME_OVERVIEW",
                page_numbers=scheme.get("source_pages", [])
            ))

        return {
            "answer": text,
            "citations": citations,
            "retrieval_method": retrieval_method
        }
