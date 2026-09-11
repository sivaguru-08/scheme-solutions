"""
Deterministic Abstract Syntax Tree (AST) Eligibility Rule Engine.
Supports:
- Logical operators: AND, OR, nested AND, nested OR, mixed AND/OR
- Comparison operators: ==, !=, >, >=, <, <=, IN, NOT_IN, BETWEEN, IS_NULL, IS_NOT_NULL
- Strict boolean evaluation: (A OR B) vs (A AND B)
- Missing field detection (single and multiple)
- Disqualifying exclusions and exceptions
"""

from typing import Any, Dict, List, Optional, Set, Tuple, Union
from pydantic import BaseModel

class ASTEvaluationResult(BaseModel):
    is_satisfied: bool
    is_conclusive: bool
    missing_fields: List[str] = []
    reasons: List[str] = []
    passed_conditions: List[Dict[str, Any]] = []
    failed_conditions: List[Dict[str, Any]] = []

class ASTRuleEngine:
    @staticmethod
    def eval_operator(actual: Any, op: str, expected: Any) -> bool:
        op = op.upper().strip()
        try:
            if op in ["==", "=", "EQUAL", "EQUALS"]:
                if isinstance(actual, str) and isinstance(expected, str):
                    return actual.strip().lower() == expected.strip().lower()
                return actual == expected
            elif op in ["!=", "<>", "NOT_EQUAL"]:
                if isinstance(actual, str) and isinstance(expected, str):
                    return actual.strip().lower() != expected.strip().lower()
                return actual != expected
            elif op in [">", "GREATER_THAN"]:
                return float(actual) > float(expected)
            elif op in [">=", "GREATER_THAN_OR_EQUAL"]:
                return float(actual) >= float(expected)
            elif op in ["<", "LESS_THAN"]:
                return float(actual) < float(expected)
            elif op in ["<=", "LESS_THAN_OR_EQUAL"]:
                return float(actual) <= float(expected)
            elif op == "IN":
                if isinstance(expected, (list, tuple, set)):
                    if isinstance(actual, str):
                        return any(str(actual).lower() == str(e).lower() for e in expected)
                    return actual in expected
                return False
            elif op == "NOT_IN":
                if isinstance(expected, (list, tuple, set)):
                    if isinstance(actual, str):
                        return not any(str(actual).lower() == str(e).lower() for e in expected)
                    return actual not in expected
                return True
            elif op == "BETWEEN":
                if isinstance(expected, (list, tuple)) and len(expected) == 2:
                    return float(expected[0]) <= float(actual) <= float(expected[1])
                return False
            elif op == "IS_NULL":
                return actual is None
            elif op == "IS_NOT_NULL":
                return actual is not None
            return False
        except (ValueError, TypeError):
            return False

    def evaluate_node(self, node: Dict[str, Any], context: Dict[str, Any]) -> ASTEvaluationResult:
        """
        Recursively evaluates an AST condition node.
        A node is either:
        - Logical node: {'operator': 'AND'|'OR', 'conditions': [...]}
        - Leaf comparison: {'field': '...', 'operator': '...', 'value': ...}
        """
        op = node.get("operator", "AND").upper().strip()
        children = node.get("conditions")

        # 1. Logical Node (AND / OR)
        if children is not None:
            if op == "AND":
                all_passed = True
                missing = []
                passed_conds = []
                failed_conds = []
                reasons = []

                for child in children:
                    res = self.evaluate_node(child, context)
                    missing.extend(res.missing_fields)
                    passed_conds.extend(res.passed_conds if hasattr(res, 'passed_conds') else res.passed_conditions)
                    failed_conds.extend(res.failed_conds if hasattr(res, 'failed_conds') else res.failed_conditions)
                    reasons.extend(res.reasons)

                    if not res.is_satisfied:
                        all_passed = False

                missing = sorted(list(set(missing)))
                # Conclusive only if an explicit failure happened or all passed with zero missing fields
                is_conclusive = len(failed_conds) > 0 or (all_passed and len(missing) == 0)

                return ASTEvaluationResult(
                    is_satisfied=all_passed and len(missing) == 0,
                    is_conclusive=is_conclusive,
                    missing_fields=missing,
                    reasons=reasons,
                    passed_conditions=passed_conds,
                    failed_conditions=failed_conds
                )

            elif op == "OR":
                any_passed = False
                all_missing = []
                passed_conds = []
                failed_conds = []
                reasons = []

                for child in children:
                    res = self.evaluate_node(child, context)
                    all_missing.extend(res.missing_fields)
                    if res.is_satisfied:
                        any_passed = True
                        passed_conds.extend(res.passed_conditions)
                    else:
                        failed_conds.extend(res.failed_conditions)
                    reasons.extend(res.reasons)

                # For OR: if at least one branch definitely passed, the OR is satisfied!
                if any_passed:
                    return ASTEvaluationResult(
                        is_satisfied=True,
                        is_conclusive=True,
                        missing_fields=[],
                        reasons=["At least one alternative qualification satisfied"],
                        passed_conditions=passed_conds,
                        failed_conditions=[]
                    )
                else:
                    unique_missing = sorted(list(set(all_missing)))
                    return ASTEvaluationResult(
                        is_satisfied=False,
                        is_conclusive=len(unique_missing) == 0,
                        missing_fields=unique_missing,
                        reasons=reasons,
                        passed_conditions=[],
                        failed_conditions=failed_conds
                    )

        # 2. Leaf Comparison Node
        field_raw = node.get("field", "")
        clean_field = field_raw.split(".")[-1]
        desc = node.get("description", field_raw)
        expected_val = node.get("value")

        # Check special operators that evaluate None
        if op in ["IS_NULL", "IS_NOT_NULL"]:
            actual_val = context.get(clean_field)
            satisfied = self.eval_operator(actual_val, op, None)
            cond_record = {"field": clean_field, "operator": op, "expected": None, "actual": actual_val, "description": desc}
            return ASTEvaluationResult(
                is_satisfied=satisfied,
                is_conclusive=True,
                missing_fields=[],
                reasons=[f"{desc}: passed" if satisfied else f"{desc}: failed"],
                passed_conditions=[cond_record] if satisfied else [],
                failed_conditions=[] if satisfied else [cond_record]
            )

        # Normal comparison requiring field presence
        if clean_field not in context or context[clean_field] is None:
            # Field is missing
            return ASTEvaluationResult(
                is_satisfied=False,
                is_conclusive=False,
                missing_fields=[clean_field],
                reasons=[f"Missing mandatory field: {clean_field} ({desc})"]
            )

        actual_val = context[clean_field]
        satisfied = self.eval_operator(actual_val, op, expected_val)

        cond_record = {
            "field": clean_field,
            "operator": op,
            "expected": expected_val,
            "actual": actual_val,
            "description": desc,
            "citation": node.get("citation")
        }

        if satisfied:
            return ASTEvaluationResult(
                is_satisfied=True,
                is_conclusive=True,
                missing_fields=[],
                reasons=[f"{desc}: satisfied (Provided: {actual_val})"],
                passed_conditions=[cond_record],
                failed_conditions=[]
            )
        else:
            return ASTEvaluationResult(
                is_satisfied=False,
                is_conclusive=True,
                missing_fields=[],
                reasons=[f"{desc}: not met (Provided: {actual_val}, required: {op} {expected_val})"],
                passed_conditions=[],
                failed_conditions=[cond_record]
            )
