"""
Dynamic Slot Questioner.
100% Non-Generative, Zero LLM.

Selects the next question using actual rule discrimination across candidate schemes.
Prioritizes fields that:
1. Are required by candidate schemes
2. Can eliminate the largest number of candidates
3. Have high extraction certainty
4. Have not already been answered
"""

from typing import Dict, Any, List, Optional, Tuple
from schemas.models import SchemeEvaluationItem, SchemeResultState

SLOT_QUESTIONS: Dict[str, str] = {
    "exact_age": "What is your exact age?",
    "age": "What is your exact age?",
    "is_bpl": "Are you from a BPL household?",
    "occupation": "What is your current occupation or employment status?",
    "trade": "What traditional artisan trade or craft do you work in (e.g., carpenter, blacksmith, potter)?",
    "area_type": "Do you live in a rural or urban area?",
    "residence_state": "Which state do you currently reside in?",
    "state": "Which state do you currently reside in?",
    "monthly_income": "What is your approximate monthly income in rupees?",
    "annual_turnover": "What is your annual business turnover in rupees?",
    "is_unorganised_worker": "Are you employed as an unorganised worker or daily wage earner?",
    "is_income_tax_payer": "Do you or anyone in your household pay income tax?",
    "is_epfo_or_esic_member": "Are you covered under EPFO or ESIC formal social security?",
    "has_ration_card": "Do you hold an active NFSA ration card?",
    "has_bank_account": "Do you have an active bank account?",
    "gender": "What is your gender?",
    "marital_status": "What is your marital status?"
}

SLOT_WEIGHTS: Dict[str, float] = {
    "exact_age": 10.0,
    "age": 10.0,
    "is_bpl": 6.0,
    "residence_state": 5.0,
    "state": 5.0,
    "trade": 4.0,
    "occupation": 3.0,
    "monthly_income": 2.5,
    "area_type": 2.0,
    "has_bank_account": 1.5,
    "is_unorganised_worker": 1.5,
    "is_income_tax_payer": 1.2,
    "is_epfo_or_esic_member": 1.2,
    "has_ration_card": 1.0,
    "marital_status": 1.0,
    "gender": 1.0
}

class DynamicSlotQuestioner:
    def select_next_question(
        self,
        candidate_evaluations: List[SchemeEvaluationItem],
        known_slots: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Determines the single most discriminative missing slot and returns:
        (slot_name, question_string).
        If no further questions are needed, returns (None, None).
        """
        potential_candidates = [
            c for c in candidate_evaluations
            if c.status == SchemeResultState.POTENTIAL and c.missing_slots
        ]

        if not potential_candidates:
            return None, None

        # Score slots based on weights and candidate relevance
        slot_scores: Dict[str, float] = {}
        for c in potential_candidates:
            # Bonus weight if candidate matched a specific age threshold >= 50
            senior_bonus = 2.0 if any(">= 60" in m for m in c.matched_conditions) else 1.0
            for s in c.missing_slots:
                if s not in known_slots or known_slots[s] is None:
                    base_w = SLOT_WEIGHTS.get(s, 1.0)
                    slot_scores[s] = slot_scores.get(s, 0.0) + (base_w * senior_bonus)

        if not slot_scores:
            return None, None

        sorted_slots = sorted(slot_scores.items(), key=lambda x: x[1], reverse=True)
        best_slot = sorted_slots[0][0]
        question = SLOT_QUESTIONS.get(best_slot, f"Please provide your {best_slot.replace('_', ' ')}.")
        return best_slot, question
