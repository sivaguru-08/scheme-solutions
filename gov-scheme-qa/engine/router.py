"""
Stage 8: Deterministic Query Router.
Routes input queries into one of 6 deterministic execution paths:
1. DIRECT_LOOKUP (Structured database retrieval for known scheme & intent)
2. RULE_ENGINE (AST rule evaluation for eligibility queries)
3. MULTI_SCHEME (Cross-scheme catalogs, filters, recommendations)
4. COMPARISON (Side-by-side comparison between 2 or more schemes)
5. SEARCH (SQLite FTS5 / BM25 text search when scheme is null/general)
6. ABSTAIN (Out-of-scope or ungroundable queries)
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel

class RouteDestination(str, Enum):
    DIRECT_LOOKUP = "DIRECT_LOOKUP"
    RULE_ENGINE = "RULE_ENGINE"
    MULTI_SCHEME = "MULTI_SCHEME"
    SEARCH = "SEARCH"
    COMPARISON = "COMPARISON"
    ABSTAIN = "ABSTAIN"

class RoutingDecision(BaseModel):
    destination: RouteDestination
    target_scheme_id: Optional[str] = None
    target_scheme_ids: List[str] = []
    intent: str
    confidence: float
    reason: str

class DeterministicRouter:
    def route(
        self,
        query: str,
        scheme_id: Optional[str] = None,
        intent: str = "OVERVIEW",
        entities: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        detected_schemes: Optional[List[str]] = None
    ) -> RoutingDecision:
        q_clean = query.strip().lower()
        detected_schemes = detected_schemes or ([scheme_id] if scheme_id else [])
        entities = entities or {}

        # 1. ABSTAIN
        if not q_clean or intent == "OUT_OF_SCOPE" or confidence < 0.25:
            return RoutingDecision(
                destination=RouteDestination.ABSTAIN,
                target_scheme_id=None,
                intent=intent,
                confidence=confidence,
                reason="Query is out of domain or below minimum confidence threshold"
            )

        # 2. COMPARISON
        comparison_keywords = ["compare", "comparison", "difference between", " vs ", " versus "]
        if any(kw in q_clean for kw in comparison_keywords) or (len(detected_schemes) >= 2 and ("better" in q_clean or "or" in q_clean)):
            return RoutingDecision(
                destination=RouteDestination.COMPARISON,
                target_scheme_ids=detected_schemes,
                intent="COMPARISON",
                confidence=confidence,
                reason=f"Multi-scheme comparison requested between {detected_schemes}"
            )

        # 3. MULTI_SCHEME
        if intent == "LIST_SCHEMES" or (scheme_id is None and ("schemes for" in q_clean or "all schemes" in q_clean or "list" in q_clean or len(detected_schemes) > 1)):
            return RoutingDecision(
                destination=RouteDestination.MULTI_SCHEME,
                target_scheme_ids=detected_schemes,
                intent="LIST_SCHEMES",
                confidence=confidence,
                reason="Multi-scheme inquiry or catalog listing"
            )

        # 4. RULE_ENGINE
        # Check if user asks for personal eligibility evaluation or provides personal attributes
        has_demographic_slots = any(
            entities.get(k) is not None for k in ["age", "income", "occupation", "land", "turnover"]
        )
        if intent == "CHECK_ELIGIBILITY" or (has_demographic_slots and scheme_id is not None):
            return RoutingDecision(
                destination=RouteDestination.RULE_ENGINE,
                target_scheme_id=scheme_id,
                target_scheme_ids=[scheme_id] if scheme_id else [],
                intent="CHECK_ELIGIBILITY",
                confidence=confidence,
                reason="Personal eligibility evaluation with AST rules requested"
            )

        # 5. DIRECT_LOOKUP
        if scheme_id is not None and intent in [
            "OVERVIEW", "BENEFITS", "DOCUMENTS", "PROCEDURE",
            "EXCLUSIONS", "AUTHORITY", "FAQ", "ELIGIBILITY"
        ]:
            return RoutingDecision(
                destination=RouteDestination.DIRECT_LOOKUP,
                target_scheme_id=scheme_id,
                target_scheme_ids=[scheme_id],
                intent=intent,
                confidence=confidence,
                reason=f"Direct database attribute lookup for scheme {scheme_id} with intent {intent}"
            )

        # 6. SEARCH (Fallback for free-text or null scheme queries)
        return RoutingDecision(
            destination=RouteDestination.SEARCH,
            target_scheme_id=scheme_id,
            target_scheme_ids=detected_schemes,
            intent=intent,
            confidence=confidence,
            reason="Unscoped or keyword text search routed to FTS5 BM25 index"
        )
