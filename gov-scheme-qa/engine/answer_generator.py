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
        requested_information = extra_data.get("requested_information", [])

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

        # General Helpline / Authority inquiry without specific scheme
        if not scheme_id and (intent == "AUTHORITY" or "HELPLINE" in requested_information or "helpline" in query.lower()):
            text = ("For Government of India welfare schemes, the primary National Citizen Helpline number is **1967** (toll-free) and the National Consumer Helpline is **1915**. "
                    "Public grievances regarding any Central Government welfare scheme can be filed at the centralized portal **CPGRAMS** (pgportal.gov.in). "
                    "Each specific scheme also has designated departmental helpline numbers.")
            return {
                "answer": text,
                "citations": [],
                "retrieval_method": "NATIONAL_HELPLINE_DIRECTORY",
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

        # ===== TARGETED CONCISE ANSWER =====
        # If user asked for specific information (FIRST_LOAN_AMOUNT, LOAN_AMOUNT, AGE_REQUIREMENT, etc.)
        # produce a single concise paragraph instead of a full template dump.
        if requested_information and scheme_id:
            targeted = self._generate_targeted_answer(scheme_id, scheme, requested_information)
            if targeted:
                return targeted

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
            "retrieval_method": retrieval_method,
            "global_outcome": GlobalOutcome.ANSWER_PRODUCED
        }

    def _generate_targeted_answer(
        self,
        scheme_id: str,
        scheme: Dict[str, Any],
        requested_information: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Produce a single concise paragraph answer for specific requested information types.
        Returns None if no targeted answer can be produced (falls through to template-based routing).
        """
        scheme_name = scheme["official_name"]
        scheme_abbrev = scheme.get("abbreviation", "")
        source_pages = scheme.get("source_pages", [])
        citation_text = f"[Source: {scheme_name}, Page {', '.join(str(p) for p in source_pages)}]" if source_pages else f"[Source: {scheme_name}]"

        # FIRST_LOAN_AMOUNT or LOAN_AMOUNT
        if "FIRST_LOAN_AMOUNT" in requested_information or "LOAN_AMOUNT" in requested_information:
            benefits = self.repo.get_benefits_for_scheme(scheme_id)
            if benefits:
                loan_lines = []
                for b in benefits:
                    desc_lower = b.get("description", "").lower() if isinstance(b, dict) else b.description.lower()
                    desc = b.get("description", "") if isinstance(b, dict) else b.description
                    qv = b.get("quantified_value", "") if isinstance(b, dict) else (b.quantified_value or "")
                    bt = b.get("benefit_type", "") if isinstance(b, dict) else b.benefit_type

                    if any(kw in desc_lower for kw in ["loan", "credit", "tranche", "lakh", "lend"]):
                        line = desc
                        if qv:
                            line += f" ({qv})"
                        loan_lines.append(line)

                if loan_lines:
                    if "FIRST_LOAN_AMOUNT" in requested_information:
                        # Prefer first tranche line
                        first_lines = [l for l in loan_lines if "first" in l.lower() or "tranche" in l.lower() or "1" in l.lower()]
                        if first_lines:
                            answer_text = f"Under **{scheme_name}**, {first_lines[0].strip()}. {citation_text}"
                        else:
                            answer_text = f"Under **{scheme_name}**, {loan_lines[0].strip()}. {citation_text}"
                    else:
                        combined = "; ".join(l.strip() for l in loan_lines)
                        answer_text = f"Under **{scheme_name}**, {combined}. {citation_text}"

                    return {
                        "answer": answer_text,
                        "citations": [SourceCitation(
                            scheme_id=scheme_id, scheme_name=scheme_name,
                            section="BENEFITS", page_numbers=source_pages
                        )],
                        "retrieval_method": "TARGETED_BENEFIT_EXTRACTION",
                        "global_outcome": GlobalOutcome.ANSWER_PRODUCED
                    }

        # AGE_REQUIREMENT
        if "AGE_REQUIREMENT" in requested_information:
            rules = self.repo.get_rules_for_scheme(scheme_id)
            if rules:
                age_lines = []
                for r in rules:
                    conds = r.get("conditions", []) if isinstance(r, dict) else r.conditions
                    for c in conds:
                        field = c.get("field", "") if isinstance(c, dict) else (c.field or "")
                        if "age" in field.lower():
                            desc = c.get("description", "") if isinstance(c, dict) else (c.description or "")
                            op = c.get("operator", "") if isinstance(c, dict) else c.operator
                            val = c.get("value", "") if isinstance(c, dict) else c.value
                            if desc:
                                age_lines.append(desc)
                            else:
                                age_lines.append(f"Age {op} {val}")
                if age_lines:
                    combined = "; ".join(age_lines)
                    return {
                        "answer": f"For **{scheme_name}**: {combined}. {citation_text}",
                        "citations": [SourceCitation(
                            scheme_id=scheme_id, scheme_name=scheme_name,
                            section="ELIGIBILITY", page_numbers=source_pages
                        )],
                        "retrieval_method": "TARGETED_RULE_EXTRACTION",
                        "global_outcome": GlobalOutcome.ANSWER_PRODUCED
                    }

        # PENSION_AMOUNT
        if "PENSION_AMOUNT" in requested_information:
            benefits = self.repo.get_benefits_for_scheme(scheme_id)
            if benefits:
                pension_lines = []
                for b in benefits:
                    desc_lower = b.get("description", "").lower() if isinstance(b, dict) else b.description.lower()
                    desc = b.get("description", "") if isinstance(b, dict) else b.description
                    if any(kw in desc_lower for kw in ["pension", "monthly"]):
                        pension_lines.append(desc)
                if pension_lines:
                    combined = "; ".join(pension_lines)
                    return {
                        "answer": f"Under **{scheme_name}**, {combined}. {citation_text}",
                        "citations": [SourceCitation(
                            scheme_id=scheme_id, scheme_name=scheme_name,
                            section="BENEFITS", page_numbers=source_pages
                        )],
                        "retrieval_method": "TARGETED_BENEFIT_EXTRACTION",
                        "global_outcome": GlobalOutcome.ANSWER_PRODUCED
                    }

        # SUBSIDY
        if "SUBSIDY" in requested_information:
            benefits = self.repo.get_benefits_for_scheme(scheme_id)
            if benefits:
                subsidy_lines = []
                for b in benefits:
                    desc_lower = b.get("description", "").lower() if isinstance(b, dict) else b.description.lower()
                    desc = b.get("description", "") if isinstance(b, dict) else b.description
                    if any(kw in desc_lower for kw in ["subsidy", "interest"]):
                        subsidy_lines.append(desc)
                if subsidy_lines:
                    combined = "; ".join(subsidy_lines)
                    return {
                        "answer": f"Under **{scheme_name}**, {combined}. {citation_text}",
                        "citations": [SourceCitation(
                            scheme_id=scheme_id, scheme_name=scheme_name,
                            section="BENEFITS", page_numbers=source_pages
                        )],
                        "retrieval_method": "TARGETED_BENEFIT_EXTRACTION",
                        "global_outcome": GlobalOutcome.ANSWER_PRODUCED
                    }

        # INSURANCE_COVER
        if "INSURANCE_COVER" in requested_information:
            benefits = self.repo.get_benefits_for_scheme(scheme_id)
            if benefits:
                cover_lines = []
                for b in benefits:
                    desc_lower = b.get("description", "").lower() if isinstance(b, dict) else b.description.lower()
                    desc = b.get("description", "") if isinstance(b, dict) else b.description
                    if any(kw in desc_lower for kw in ["insurance", "cover", "sum assured", "accidental"]):
                        cover_lines.append(desc)
                if cover_lines:
                    combined = "; ".join(cover_lines)
                    return {
                        "answer": f"Under **{scheme_name}**, {combined}. {citation_text}",
                        "citations": [SourceCitation(
                            scheme_id=scheme_id, scheme_name=scheme_name,
                            section="BENEFITS", page_numbers=source_pages
                        )],
                        "retrieval_method": "TARGETED_BENEFIT_EXTRACTION",
                        "global_outcome": GlobalOutcome.ANSWER_PRODUCED
                    }

        # HELPLINE
        if "HELPLINE" in requested_information:
            auth = self.repo.get_authority_for_scheme(scheme_id)
            helpline = auth.get("helpline") if auth else "National Citizen Helpline / 1967"
            grievance = auth.get("grievance_redressal") if auth else "CPGRAMS (pgportal.gov.in)"
            answer_text = f"The official helpline for **{scheme_name}** is **{helpline}**. Public grievances can be registered via **{grievance}**. {citation_text}"
            return {
                "answer": answer_text,
                "citations": [SourceCitation(
                    scheme_id=scheme_id, scheme_name=scheme_name,
                    section="ADMINISTRATIVE_AUTHORITY", page_numbers=source_pages
                )],
                "retrieval_method": "TARGETED_AUTHORITY_EXTRACTION",
                "global_outcome": GlobalOutcome.ANSWER_PRODUCED
            }

        return None

