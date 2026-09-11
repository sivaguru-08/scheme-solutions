"""
Deterministic Multi-Scheme Recommendation Engine.
100% Non-Generative, Zero LLM.

Evaluates all active schemes from the SQLite database against a UserProfile / UserDemographics.
Categorizes every scheme into:
- ELIGIBLE: All mandatory conditions are known and satisfied.
- POTENTIAL: No mandatory condition failed, but one or more required fields are unknown.
- INELIGIBLE: At least one mandatory condition is definitively violated.
- NOT_APPLICABLE: Scheme is outside the scope of user context.

Derives candidate schemes dynamically from knowledge base and rule definitions without hard-coded lists.
"""

from typing import Dict, Any, List, Optional, Tuple
from schemas.models import (
    UserDemographics, SchemeResultState, GlobalOutcome,
    SchemeEvaluationItem
)
from store.database import SchemeRepository

class DeterministicRecommendationEngine:
    def __init__(self, repo: Optional[SchemeRepository] = None):
        self.repo = repo or SchemeRepository()

    def evaluate_all_schemes(
        self,
        profile: Optional[UserDemographics] = None,
        target_scheme_ids: Optional[List[str]] = None,
        query_text: Optional[str] = None
    ) -> Tuple[List[SchemeEvaluationItem], str]:
        profile = profile or UserDemographics()
        all_schemes = self.repo.get_all_schemes()
        if target_scheme_ids:
            all_schemes = [s for s in all_schemes if s["scheme_id"] in target_scheme_ids]

        results: List[SchemeEvaluationItem] = []

        for s in all_schemes:
            eval_item = self.evaluate_scheme_compatibility(s, profile, query_text)
            results.append(eval_item)

        eligible = [r for r in results if r.status == SchemeResultState.ELIGIBLE]
        potential = [r for r in results if r.status == SchemeResultState.POTENTIAL]
        ineligible = [r for r in results if r.status == SchemeResultState.INELIGIBLE]

        # Rank eligible schemes by number of matched conditions (relevance)
        eligible.sort(key=lambda x: len(x.matched_conditions), reverse=True)
        # Rank potential schemes by fewest missing slots
        potential.sort(key=lambda x: (len(x.missing_slots), -len(x.matched_conditions)))

        ordered_results = eligible + potential + ineligible

        # Determine Global Outcome
        if eligible:
            global_outcome = GlobalOutcome.ANSWER_PRODUCED
        elif potential:
            global_outcome = GlobalOutcome.INSUFFICIENT_INFORMATION
        else:
            global_outcome = GlobalOutcome.NO_MATCH

        return ordered_results, global_outcome

    def evaluate_scheme_compatibility(
        self,
        scheme: Dict[str, Any],
        profile: Optional[UserDemographics] = None,
        query_text: Optional[str] = None
    ) -> SchemeEvaluationItem:
        profile = profile or UserDemographics()
        sid = scheme["scheme_id"]
        name = scheme["official_name"]
        rules = self.repo.get_rules_for_scheme(sid)
        exclusions = self.repo.get_exclusions_for_scheme(sid)

        matched_conditions: List[str] = []
        failed_conditions: List[str] = []
        unknown_conditions: List[str] = []
        missing_slots: List[str] = []
        ranking_reasons: List[str] = []

        user_dict = profile.model_dump()
        age = profile.age
        age_category = profile.age_category

        # If user explicitly asked for pension schemes, filter out non-pension schemes
        if query_text:
            import re
            q_lower = query_text.lower()
            if re.search(r'\bpension(?:\s*schemes?)?\b', q_lower):
                scheme_corpus = f"{name} {scheme.get('category','')} {scheme.get('subcategory','')} {scheme.get('description','')} {scheme.get('objective','')}".lower()
                if not any(kw in scheme_corpus for kw in ["pension", "ignoaps", "ignwps", "igndps", "annapurna", "old age", "social assistance"]):
                    return SchemeEvaluationItem(
                        scheme_id=sid,
                        scheme_name=name,
                        status=SchemeResultState.NOT_APPLICABLE,
                        matched_conditions=[],
                        failed_conditions=[],
                        unknown_conditions=[],
                        missing_slots=[],
                        relevance_score=0.0,
                        ranking_reasons=["Scheme is not in requested pension category"]
                    )

        # Check scheme operational status (historical / discontinued vs active)
        scheme_status = (scheme.get("status") or "ACTIVE").upper()
        if scheme_status in ["DISCONTINUED", "INACTIVE", "EXPIRED", "HISTORICAL"]:
            return SchemeEvaluationItem(
                scheme_id=sid,
                scheme_name=name,
                status=SchemeResultState.NOT_APPLICABLE,
                matched_conditions=[],
                failed_conditions=[],
                unknown_conditions=[],
                missing_slots=[],
                relevance_score=0.0,
                ranking_reasons=[f"Scheme is {scheme_status} (not currently active)"]
            )

        # If scheme has no codified qualification rules in knowledge base:
        if not rules:
            return SchemeEvaluationItem(
                scheme_id=sid,
                scheme_name=name,
                status=SchemeResultState.NOT_APPLICABLE,
                matched_conditions=[],
                failed_conditions=[],
                unknown_conditions=[],
                missing_slots=[],
                relevance_score=0.0,
                ranking_reasons=["No demographic rules registered in knowledge base"]
            )

        # Check State-Specific Scheme
        if scheme.get("geographic_scope") == "STATE_SPECIFIC" or scheme.get("target_state"):
            target_st = scheme.get("target_state") or ("Punjab" if "ABPMJAY" in sid else None)
            if target_st:
                if profile.residence_state:
                    if profile.residence_state.strip().lower() == target_st.strip().lower():
                        matched_conditions.append(f"State residence requirement met: {target_st}")
                    else:
                        failed_conditions.append(f"Scheme restricted to residents of {target_st} (applicant resides in {profile.residence_state})")
                        ranking_reasons.append(f"Restricted to {target_st} residents")
                else:
                    unknown_conditions.append(f"Requires residence in {target_st}")
                    if "residence_state" not in missing_slots:
                        missing_slots.append("residence_state")

        # Check Rural/Urban Geographic Scope
        if scheme.get("geographic_scope") == "RURAL":
            if profile.area_type == "URBAN":
                failed_conditions.append("Scheme is restricted to rural residents")
                ranking_reasons.append("Requires rural residence")
            elif profile.area_type == "RURAL":
                matched_conditions.append("Rural area requirement satisfied")
            elif profile.area_type is None:
                unknown_conditions.append("Requires rural residence")
                if "area_type" not in missing_slots:
                    missing_slots.append("area_type")
        elif scheme.get("geographic_scope") == "URBAN":
            if profile.area_type == "RURAL":
                failed_conditions.append("Scheme is restricted to urban residents")
                ranking_reasons.append("Requires urban residence")
            elif profile.area_type == "URBAN":
                matched_conditions.append("Urban area requirement satisfied")
            elif profile.area_type is None:
                unknown_conditions.append("Requires urban residence")
                if "area_type" not in missing_slots:
                    missing_slots.append("area_type")

        # Check Widow Pension gender & marital status
        if "widow" in name.lower() or "ignwps" in name.lower() or "ignwps" in sid.lower():
            if profile.gender == "MALE":
                failed_conditions.append("Widow pension is restricted to female applicants")
                ranking_reasons.append("Restricted to female applicants")
            elif profile.marital_status == "WIDOW":
                matched_conditions.append("Widow status satisfied")
            elif profile.marital_status in ["MARRIED", "SINGLE", "WIDOWER"]:
                failed_conditions.append(f"Applicant marital status is {profile.marital_status}")
                ranking_reasons.append("Requires widow status")

        # Check BOCW occupation constraint
        if sid == "SCH_BOCW":
            if profile.occupation and profile.occupation not in ["CONSTRUCTION_WORKER", "BUILDING_WORKER", "UNORGANISED_WORKER"]:
                failed_conditions.append(f"Occupation {profile.occupation} does not qualify for BOCW construction worker welfare")
                ranking_reasons.append("Requires construction worker occupation")

        # 1. Evaluate Disqualifying Exclusions
        if profile.is_income_tax_payer is True:
            for ex in exclusions:
                if ex.get("category") in ["INCOME_TAX", "TAX_EPFO", "FORMAL_SECTOR"]:
                    failed_conditions.append(f"Excluded: {ex['description']}")
                    ranking_reasons.append("Income tax payer exclusion applies")

        if profile.is_epfo_or_esic_member is True:
            for ex in exclusions:
                if ex.get("category") in ["FORMAL_SOCIAL_SECURITY", "FORMAL_SECTOR", "TAX_EPFO"]:
                    failed_conditions.append(f"Excluded: {ex['description']}")
                    ranking_reasons.append("Formal social security (EPFO/ESIC) exclusion applies")

        if profile.has_pucca_house is True:
            for ex in exclusions:
                if ex.get("category") == "PUCCA_HOUSE":
                    failed_conditions.append(f"Excluded: {ex['description']}")

        # 2. Evaluate Qualification & Exclusion Rules
        for r in rules:
            rule_type = r.get("rule_type", "QUALIFICATION").upper()
            conds = r.get("conditions", [])

            if rule_type == "EXCLUSION":
                for c in conds:
                    field = c.get("field", "")
                    op = c.get("operator", "==")
                    val = c.get("value")
                    desc = c.get("description", field)
                    clean_field = field.split(".")[-1]

                    actual_val = user_dict.get(clean_field)
                    if actual_val is not None:
                        if self._eval_op(actual_val, op, val):
                            failed_conditions.append(f"Excluded under rule: {desc}")
                            ranking_reasons.append(f"Hit disqualification: {desc}")

            else:  # QUALIFICATION
                for c in conds:
                    if c.get("conditions") is not None:
                        from engine.ast_rule_engine import ASTRuleEngine
                        ast_res = ASTRuleEngine().evaluate_node(c, user_dict)
                        if ast_res.is_satisfied:
                            matched_conditions.append(f"Combined condition satisfied: {c.get('operator', 'OR')}")
                        elif ast_res.missing_fields:
                            for mf in ast_res.missing_fields:
                                unknown_conditions.append(f"Requires verification: {mf}")
                                if mf not in missing_slots:
                                    missing_slots.append(mf)
                        else:
                            failed_conditions.append(f"Did not meet combined condition: {c.get('operator', 'OR')}")
                        continue

                    field = c.get("field", "")
                    op = c.get("operator", "==")
                    val = c.get("value")
                    desc = c.get("description", field)
                    clean_field = field.split(".")[-1]

                    # Condition A: Age evaluation
                    if "age" in clean_field:
                        if age is not None:
                            if self._eval_op(age, op, val):
                                matched_conditions.append(f"Age requirement satisfied: {age} {op} {val}")
                            else:
                                failed_conditions.append(f"Age {age} does not meet requirement: {op} {val}")
                                ranking_reasons.append(f"Age {age} fails required {op} {val}")
                        elif age_category == "ELDERLY":
                            if op in ["<=", "<"] and float(val) <= 45:
                                failed_conditions.append(f"Elderly person exceeds maximum scheme age limit: {op} {val}")
                                ranking_reasons.append(f"Age exceeds scheme maximum of {val}")
                            elif op in ["<=", "<"] and float(val) < 18:
                                failed_conditions.append(f"Elderly person exceeds child age limit: {op} {val}")
                                ranking_reasons.append(f"Scheme is for children under {val}")
                            elif op in [">=", ">"] and float(val) >= 50:
                                unknown_conditions.append(f"Requires exact age {op} {val}")
                                if "exact_age" not in missing_slots and "age" not in missing_slots:
                                    missing_slots.append("exact_age")
                            elif op in ["<=", "<"] and float(val) >= 60:
                                unknown_conditions.append(f"Requires exact age {op} {val}")
                                if "exact_age" not in missing_slots and "age" not in missing_slots:
                                    missing_slots.append("exact_age")
                            else:
                                unknown_conditions.append(f"Requires exact age {op} {val}")
                                if "exact_age" not in missing_slots and "age" not in missing_slots:
                                    missing_slots.append("exact_age")
                        else:
                            unknown_conditions.append(f"Requires age {op} {val}")
                            if "age" not in missing_slots and "exact_age" not in missing_slots:
                                missing_slots.append("age")

                    # Condition B: Gender evaluation
                    elif "gender" in clean_field:
                        if profile.gender is not None:
                            if self._eval_op(profile.gender, op, val):
                                matched_conditions.append(f"Gender requirement satisfied: {profile.gender}")
                            else:
                                failed_conditions.append(f"Gender {profile.gender} does not match required {val}")
                                ranking_reasons.append(f"Scheme requires {val}")
                        else:
                            unknown_conditions.append(f"Requires gender {op} {val}")
                            if "gender" not in missing_slots:
                                missing_slots.append("gender")

                    # Condition C: BPL status
                    elif "bpl" in clean_field or "poor" in clean_field:
                        if profile.is_bpl is not None:
                            if self._eval_op(profile.is_bpl, op, val):
                                matched_conditions.append("BPL requirement satisfied")
                            else:
                                failed_conditions.append("Non-BPL household does not meet requirement")
                                ranking_reasons.append("Requires Below Poverty Line status")
                        else:
                            unknown_conditions.append("Requires Below Poverty Line (BPL) status verification")
                            if "is_bpl" not in missing_slots:
                                missing_slots.append("is_bpl")

                    # Condition D: Area Type (RURAL / URBAN)
                    elif "area_type" in clean_field:
                        if profile.area_type is not None:
                            if self._eval_op(profile.area_type, op, val):
                                matched_conditions.append(f"Area type satisfied: {profile.area_type}")
                            else:
                                failed_conditions.append(f"Area type {profile.area_type} does not match {val}")
                                ranking_reasons.append(f"Requires {val} residence")
                        else:
                            unknown_conditions.append(f"Requires {val} residence")
                            if "area_type" not in missing_slots:
                                missing_slots.append("area_type")

                    # Condition E: State / Geographic
                    elif "state" in clean_field:
                        if profile.residence_state is not None:
                            if self._eval_op(profile.residence_state, op, val):
                                matched_conditions.append(f"State requirement satisfied: {profile.residence_state}")
                            else:
                                failed_conditions.append(f"State {profile.residence_state} does not match required {val}")
                                ranking_reasons.append(f"Scheme restricted to {val}")
                        else:
                            unknown_conditions.append(f"Requires residence in {val}")
                            if "residence_state" not in missing_slots:
                                missing_slots.append("residence_state")

                    # Condition F: Ration Card
                    elif "ration_card" in clean_field:
                        if profile.has_ration_card is not None:
                            if self._eval_op(profile.has_ration_card, op, val):
                                matched_conditions.append("Ration card requirement satisfied")
                            else:
                                failed_conditions.append("Does not hold active ration card")
                                ranking_reasons.append("Requires active NFSA ration card")
                        else:
                            unknown_conditions.append("Requires active NFSA ration card")
                            if "has_ration_card" not in missing_slots:
                                missing_slots.append("has_ration_card")

                    # Condition G: Artisan Trade / Occupation
                    elif "artisan_trade" in clean_field or "trade" in clean_field:
                        if profile.trade is not None:
                            if self._eval_op(profile.trade, op, val):
                                matched_conditions.append(f"Trade recognized: {profile.trade}")
                            else:
                                failed_conditions.append(f"Trade {profile.trade} not in notified list")
                                ranking_reasons.append(f"Trade {profile.trade} not covered")
                        elif profile.occupation and profile.occupation != "ARTISAN":
                            # Non-artisan occupation cannot qualify for artisan schemes
                            failed_conditions.append(f"Occupation {profile.occupation} does not qualify for artisan scheme")
                            ranking_reasons.append("Requires traditional artisan profession")
                        elif profile.occupation == "ARTISAN":
                            unknown_conditions.append("Requires specific notified artisan trade")
                            if "trade" not in missing_slots:
                                missing_slots.append("trade")
                        else:
                            unknown_conditions.append("Requires recognized artisan trade")
                            if "trade" not in missing_slots and "occupation" not in missing_slots:
                                missing_slots.append("trade")

                    elif "occupation_type" in clean_field or "occupation" in clean_field:
                        if profile.occupation is not None:
                            if self._eval_op(profile.occupation, op, val):
                                matched_conditions.append(f"Occupation requirement met: {profile.occupation}")
                            else:
                                failed_conditions.append(f"Occupation {profile.occupation} does not match {val}")
                                ranking_reasons.append(f"Requires occupation: {val}")
                        elif "unorganised" in str(val).lower() and profile.is_unorganised_worker is True:
                            matched_conditions.append("Unorganised worker status met")
                        else:
                            unknown_conditions.append(f"Requires occupation: {val}")
                            if "occupation" not in missing_slots:
                                missing_slots.append("occupation")

                    # Condition H: Agriculture / Crops / Farmers
                    elif "crop" in clean_field or "cultivatable_land" in clean_field or "land_area" in clean_field or "farmer" in clean_field:
                        if profile.occupation and profile.occupation != "FARMER":
                            failed_conditions.append(f"Occupation {profile.occupation} does not qualify for farmer scheme")
                            ranking_reasons.append("Requires agricultural landholding/cultivation")
                        elif profile.occupation == "FARMER":
                            matched_conditions.append("Farmer occupation requirement met")
                        else:
                            unknown_conditions.append("Requires agricultural land or cultivation")
                            if "occupation" not in missing_slots:
                                missing_slots.append("occupation")

                    # Condition I: Monthly Income
                    elif "monthly_income" in clean_field:
                        if profile.monthly_income is not None:
                            if self._eval_op(profile.monthly_income, op, val):
                                matched_conditions.append(f"Income satisfied: ₹{profile.monthly_income} {op} ₹{val}")
                            else:
                                failed_conditions.append(f"Income ₹{profile.monthly_income} exceeds threshold {val}")
                                ranking_reasons.append(f"Income exceeds ₹{val}")
                        else:
                            unknown_conditions.append(f"Requires monthly income {op} ₹{val}")
                            if "monthly_income" not in missing_slots:
                                missing_slots.append("monthly_income")

                    # Condition J: Annual turnover
                    elif "turnover" in clean_field:
                        if profile.annual_turnover is not None:
                            if self._eval_op(profile.annual_turnover, op, val):
                                matched_conditions.append(f"Turnover satisfied: ₹{profile.annual_turnover} {op} ₹{val}")
                            else:
                                failed_conditions.append(f"Turnover ₹{profile.annual_turnover} exceeds {val}")
                                ranking_reasons.append(f"Turnover exceeds ₹{val}")
                        else:
                            unknown_conditions.append(f"Requires turnover {op} ₹{val}")
                            if "annual_turnover" not in missing_slots:
                                missing_slots.append("annual_turnover")

                    # Condition K: Solar / Rooftop
                    elif "electricity_connection" in clean_field or "roof" in clean_field:
                        if profile.has_electricity_connection is not None:
                            if self._eval_op(profile.has_electricity_connection, op, val):
                                matched_conditions.append("Electricity connection satisfied")
                            else:
                                failed_conditions.append("Electricity connection requirement unmet")
                        elif profile.roof_suitable_solar is False:
                            failed_conditions.append("Roof not suitable for solar")
                        else:
                            unknown_conditions.append("Requires rooftop solar feasibility and electricity connection")

                    # Default fallback
                    else:
                        actual = user_dict.get(clean_field)
                        if actual is not None:
                            if self._eval_op(actual, op, val):
                                matched_conditions.append(f"Requirement met: {desc}")
                            else:
                                failed_conditions.append(f"Requirement unmet: {desc}")
                        else:
                            unknown_conditions.append(f"Condition requires verification: {desc}")

        # Determine Final Scheme Semantic State
        if failed_conditions:
            status = SchemeResultState.INELIGIBLE
        elif matched_conditions and not unknown_conditions:
            status = SchemeResultState.ELIGIBLE
            ranking_reasons.append("All mandatory qualification conditions satisfied")
        elif unknown_conditions:
            status = SchemeResultState.POTENTIAL
            ranking_reasons.append(f"Compatible candidate pending {len(missing_slots)} verification details")
        else:
            status = SchemeResultState.NOT_APPLICABLE

        relevance_score = len(matched_conditions) * 1.0 - len(failed_conditions) * 2.0 - len(missing_slots) * 0.2

        return SchemeEvaluationItem(
            scheme_id=sid,
            scheme_name=name,
            status=status,
            matched_conditions=matched_conditions,
            failed_conditions=failed_conditions,
            unknown_conditions=unknown_conditions,
            missing_slots=missing_slots,
            relevance_score=round(relevance_score, 2),
            ranking_reasons=ranking_reasons
        )

    def _eval_op(self, actual: Any, op: str, expected: Any) -> bool:
        try:
            if op in ["==", "="]:
                if isinstance(actual, str) and isinstance(expected, str):
                    return actual.strip().lower() == expected.strip().lower()
                return actual == expected
            elif op == "!=":
                if isinstance(actual, str) and isinstance(expected, str):
                    return actual.strip().lower() != expected.strip().lower()
                return actual != expected
            elif op == ">=":
                return float(actual) >= float(expected)
            elif op == "<=":
                return float(actual) <= float(expected)
            elif op == ">":
                return float(actual) > float(expected)
            elif op == "<":
                return float(actual) < float(expected)
            elif op in ["in", "IN"]:
                if isinstance(expected, (list, tuple, set)):
                    return actual in expected or (isinstance(actual, str) and any(str(actual).lower() == str(e).lower() for e in expected))
                return False
            elif op in ["not in", "NOT IN"]:
                if isinstance(expected, (list, tuple, set)):
                    return not (actual in expected or (isinstance(actual, str) and any(str(actual).lower() == str(e).lower() for e in expected)))
                return True
            return False
        except (ValueError, TypeError):
            return False
