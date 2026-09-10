from typing import Dict, Any, List, Optional, Tuple
from schemas.models import UserDemographics, EligibilityResult, ConditionEvaluation
from store.database import SchemeRepository

class DeterministicRuleEvaluator:
    def __init__(self, repo: Optional[SchemeRepository] = None):
        self.repo = repo or SchemeRepository()

    def evaluate_scheme(self, scheme_id: str, profile: UserDemographics) -> EligibilityResult:
        scheme = self.repo.get_scheme_by_id(scheme_id)
        if not scheme:
            return EligibilityResult(
                scheme_id=scheme_id,
                scheme_name=scheme_id,
                is_eligible=False,
                confidence=0.0,
                reasons=[f"Scheme ID {scheme_id} not found in knowledge base."]
            )

        rules = self.repo.get_rules_for_scheme(scheme_id)
        exclusions = self.repo.get_exclusions_for_scheme(scheme_id)

        passed_conditions: List[ConditionEvaluation] = []
        failed_conditions: List[ConditionEvaluation] = []
        missing_info: List[str] = []
        reasons: List[str] = []
        citations: List[str] = []

        # 1. Evaluate Disqualifying Exclusions first
        user_dict = profile.model_dump()

        if profile.is_income_tax_payer:
            # Check if scheme excludes income tax payers
            for ex in exclusions:
                if ex["category"] in ["INCOME_TAX", "TAX_EPFO", "FORMAL_SECTOR"]:
                    failed_conditions.append(ConditionEvaluation(
                        field="is_income_tax_payer",
                        required_value=False,
                        actual_value=True,
                        passed=False,
                        description=ex["description"],
                        citation=f"Page {ex['source_pages']}" if ex.get("source_pages") else None
                    ))
                    reasons.append(f"Disqualified under exclusion: {ex['description']}")
                    for p in ex.get("source_pages", []):
                        citations.append(f"Page {p}")

        if profile.is_epfo_or_esic_member:
            for ex in exclusions:
                if ex["category"] in ["FORMAL_SOCIAL_SECURITY", "FORMAL_SECTOR", "TAX_EPFO"]:
                    failed_conditions.append(ConditionEvaluation(
                        field="is_epfo_or_esic_member",
                        required_value=False,
                        actual_value=True,
                        passed=False,
                        description=ex["description"],
                        citation=f"Page {ex['source_pages']}" if ex.get("source_pages") else None
                    ))
                    reasons.append(f"Disqualified under exclusion: {ex['description']}")
                    for p in ex.get("source_pages", []):
                        citations.append(f"Page {p}")

        # 2. Evaluate Stored Rules (Qualification and Exclusion rules)
        for r in rules:
            rule_type = r.get("rule_type", "QUALIFICATION").upper()
            for p in r.get("source_pages", []):
                citations.append(f"Page {p}")

            if rule_type == "EXCLUSION":
                # For an exclusion rule: if any condition matches the applicant, they are disqualified
                for c in r.get("conditions", []):
                    field_raw = c.get("field", "")
                    op = c.get("operator", "==")
                    val = c.get("value")
                    desc = c.get("description", field_raw)
                    cit = c.get("citation", "")

                    clean_field = field_raw.split(".")[-1]
                    # Check field aliases (e.g. is_income_tax_payer, covered_by_epfo)
                    actual_val = None
                    if clean_field in user_dict:
                        actual_val = user_dict[clean_field]
                    elif "epfo" in clean_field and user_dict.get("is_epfo_or_esic_member") is not None:
                        actual_val = user_dict["is_epfo_or_esic_member"]
                    elif "esic" in clean_field and user_dict.get("is_epfo_or_esic_member") is not None:
                        actual_val = user_dict["is_epfo_or_esic_member"]
                    elif "nps" in clean_field and user_dict.get("is_epfo_or_esic_member") is not None:
                        actual_val = user_dict["is_epfo_or_esic_member"]

                    if actual_val is None:
                        continue

                    # If this condition evaluates to True, the user hits the exclusion
                    hits_exclusion = self._eval_op(actual_val, op, val)
                    if hits_exclusion:
                        failed_conditions.append(ConditionEvaluation(
                            field=clean_field,
                            required_value=f"NOT ({op} {val})",
                            actual_value=actual_val,
                            passed=False,
                            description=f"Disqualification: {desc}",
                            citation=cit
                        ))
                        reasons.append(f"Disqualified under rule: {desc}")
            else:
                # Qualification rule
                for c in r.get("conditions", []):
                    field_raw = c.get("field", "")
                    op = c.get("operator", "==")
                    val = c.get("value")
                    desc = c.get("description", field_raw)
                    cit = c.get("citation", "")

                    clean_field = field_raw.split(".")[-1]
                    actual_val = None
                    if clean_field in user_dict:
                        actual_val = user_dict[clean_field]
                    elif "income" in clean_field and user_dict.get("monthly_income") is not None:
                        actual_val = user_dict["monthly_income"]
                    elif "unorganised" in clean_field or "occupation_type" in clean_field:
                        if user_dict.get("is_unorganised_worker") is True:
                            actual_val = "UNORGANISED_WORKER"
                        elif user_dict.get("occupation"):
                            actual_val = user_dict["occupation"]
                    elif "citizenship" in clean_field:
                        actual_val = "INDIAN"  # Default assumption for national scheme query unless stated

                    if actual_val is None:
                        missing_info.append(f"{clean_field} ({desc})")
                        continue

                    cond_passed = self._eval_op(actual_val, op, val)
                    eval_obj = ConditionEvaluation(
                        field=clean_field,
                        required_value=f"{op} {val}",
                        actual_value=actual_val,
                        passed=cond_passed,
                        description=desc,
                        citation=cit
                    )

                    if cond_passed:
                        passed_conditions.append(eval_obj)
                    else:
                        failed_conditions.append(eval_obj)
                        reasons.append(f"Did not meet requirement: {desc} (Your value: {actual_val}, required: {op} {val})")

        # Determine overall eligibility
        if failed_conditions:
            is_eligible = False
        elif missing_info:
            is_eligible = False
            reasons.append(f"Cannot conclusively confirm eligibility. Missing mandatory info: {', '.join(missing_info)}")
        else:
            is_eligible = True
            reasons.append(f"All qualification conditions satisfied for {scheme['official_name']}.")

        unique_citations = sorted(list(set(citations)))
        confidence = 1.0 if not missing_info else max(0.5, 1.0 - (len(missing_info) * 0.15))

        return EligibilityResult(
            scheme_id=scheme_id,
            scheme_name=scheme["official_name"],
            is_eligible=is_eligible,
            confidence=round(confidence, 2),
            passed_conditions=passed_conditions,
            failed_conditions=failed_conditions,
            missing_information=list(set(missing_info)),
            reasons=reasons,
            citations=unique_citations
        )

    def _eval_op(self, actual: Any, op: str, expected: Any) -> bool:
        try:
            if op in ["==", "="]:
                if isinstance(actual, str) and isinstance(expected, str):
                    return actual.strip().lower() == expected.strip().lower()
                return actual == expected
            elif op == "!=":
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
                return actual in expected
            elif op in ["not in", "NOT IN"]:
                return actual not in expected
            return False
        except (ValueError, TypeError):
            return False
