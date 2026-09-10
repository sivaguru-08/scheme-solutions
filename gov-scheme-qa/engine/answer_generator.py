from typing import Dict, Any, List, Optional
from schemas.models import SourceCitation, UserDemographics, EligibilityResult
from store.database import SchemeRepository
from engine.rule_evaluator import DeterministicRuleEvaluator
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
    OUT_OF_SCOPE_TEMPLATE
)

class DeterministicAnswerGenerator:
    def __init__(self, repo: Optional[SchemeRepository] = None):
        self.repo = repo or SchemeRepository()
        self.evaluator = DeterministicRuleEvaluator(self.repo)

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

        # 1. Scheme List Intent
        if intent == "LIST_SCHEMES" or (not scheme_id and "list" in query.lower() and "scheme" in query.lower()):
            schemes = self.repo.get_all_schemes()
            text = render_template(LIST_SCHEMES_TEMPLATE, schemes=schemes)
            return {
                "answer": text,
                "citations": citations,
                "retrieval_method": "DATABASE_CATALOG"
            }

        # If scheme_id is not provided or not identified, try BM25 full-text retrieval
        if not scheme_id:
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
                    "retrieval_method": "FTS5_BM25"
                }
            else:
                text = render_template(OUT_OF_SCOPE_TEMPLATE, query=query)
                return {
                    "answer": text,
                    "citations": [],
                    "retrieval_method": "OUT_OF_SCOPE"
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
                    "fees": "No fee unless specified"
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
            text = render_template(EXCLUSIONS_TEMPLATE, scheme=scheme, exclusions=exclusions)
            citations.append(SourceCitation(
                scheme_id=scheme_id,
                scheme_name=scheme["official_name"],
                section="EXCLUSIONS",
                page_numbers=scheme.get("source_pages", [])
            ))

        elif intent == "FAQ":
            faqs = self.repo.get_faqs_for_scheme(scheme_id)
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
