"""
Deterministic Conversation State Machine and Session Store.
100% Non-Generative, Zero LLM.

Manages multi-turn conversation sessions, context resolution, reference handling,
and topic change detection with sub-millisecond latency.
"""

import re
import uuid
import time
from typing import Dict, Any, List, Optional, Tuple
from schemas.models import (
    ConversationState, ConversationTurn, ConversationMachineState,
    UserDemographics, QueryRepresentation, QueryType
)
from store.database import SchemeRepository

class ConversationManager:
    def __init__(self, repo: Optional[SchemeRepository] = None):
        self.repo = repo or SchemeRepository()
        self._sessions: Dict[str, ConversationState] = {}

    def get_or_create_session(self, conversation_id: Optional[str] = None) -> ConversationState:
        if not conversation_id or conversation_id not in self._sessions:
            cid = conversation_id or f"conv_{uuid.uuid4().hex[:12]}"
            state = ConversationState(conversation_id=cid)
            self._sessions[cid] = state
            return state
        return self._sessions[conversation_id]

    def save_session(self, state: ConversationState) -> None:
        self._sessions[state.conversation_id] = state

    def resolve_context(
        self,
        query: str,
        state: ConversationState,
        detected_schemes: List[str],
        query_rep: QueryRepresentation
    ) -> Tuple[str, Optional[str], Optional[int]]:
        """
        Resolves context:
        - Detects state transition: NEW_QUERY, FOLLOW_UP, SLOT_VALUE, TOPIC_CHANGE, REFERENCE_QUERY
        - Resolves target scheme_id from ordinals ('the second one') or active scheme inheritance
        - Maintains scheme_context_stack for "go back to first scheme" / "the previous scheme"
        - Detects topic changes: switches active scheme, preserves user profile
        Returns: (state_transition, target_scheme_id, referenced_ordinal)
        """
        q_lower = query.strip().lower()

        # 1. Check Slot Value response to pending question
        if state.pending_question_slot and query_rep.query_type == "SLOT_VALUE":
            return ConversationMachineState.SLOT_VALUE, state.active_scheme_id, None

        # 2. Explicit Scheme Detection (Explicit scheme names override previous context)
        if detected_schemes:
            new_scheme_id = detected_schemes[0]
            if state.active_scheme_id and new_scheme_id != state.active_scheme_id:
                # Topic Change! Preserves profile, switches active scheme
                # Push previous scheme to context stack
                state.previous_scheme_id = state.active_scheme_id
                return ConversationMachineState.TOPIC_CHANGE, new_scheme_id, None
            else:
                return ConversationMachineState.NEW_QUERY, new_scheme_id, None

        # 3. Check Ordinal Reference (e.g. "What are the documents for the second one?")
        ordinal = None
        if "first" in q_lower or "1st" in q_lower:
            ordinal = 1
        elif "second" in q_lower or "2nd" in q_lower:
            ordinal = 2
        elif "third" in q_lower or "3rd" in q_lower:
            ordinal = 3
        elif "fourth" in q_lower or "4th" in q_lower:
            ordinal = 4

        # Check "go back to" / "the previous scheme" / "the other scheme"
        refers_to_previous = bool(re.search(r'\b(?:previous\s*scheme|the\s*other\s*scheme|go\s*back)\b', q_lower))

        if ordinal is not None:
            # First, try scheme_context_stack (all schemes ever discussed)
            if state.scheme_context_stack and ordinal <= len(state.scheme_context_stack):
                resolved_scheme_id = state.scheme_context_stack[ordinal - 1]
                return ConversationMachineState.REFERENCE_QUERY, resolved_scheme_id, ordinal
            # Fall back to last_recommended_schemes
            if state.last_recommended_schemes:
                idx = ordinal - 1
                if 0 <= idx < len(state.last_recommended_schemes):
                    resolved_scheme_id = state.last_recommended_schemes[idx]
                    return ConversationMachineState.REFERENCE_QUERY, resolved_scheme_id, ordinal

        if refers_to_previous and state.previous_scheme_id:
            return ConversationMachineState.REFERENCE_QUERY, state.previous_scheme_id, None

        # 4. Context Preservation for Schemes (e.g. "What documents do I need?", "How do I apply?", "can i apply it now")
        effective_scheme_id = state.active_scheme_id or (state.last_recommended_schemes[0] if state.last_recommended_schemes else None)
        if not detected_schemes and effective_scheme_id:
            # Check if query is an inquiry about attributes of the active scheme
            follow_up_keywords = [
                "document", "paper", "apply", "procedure", "benefit", "eligib",
                "criteria", "exclusion", "helpline", "ministry", "this scheme", "it",
                "cash", "payout", "pension"
            ]
            if any(kw in q_lower for kw in follow_up_keywords) or query_rep.primary_intent in ["PROCEDURE", "DOCUMENTS", "BENEFITS", "ELIGIBILITY"]:
                state.active_scheme_id = effective_scheme_id
                return ConversationMachineState.FOLLOW_UP, effective_scheme_id, None

        # 5. Recommendation / General Query
        if query_rep.query_type in [QueryType.SCHEME_RECOMMENDATION, "MULTI_SCHEME_RECOMMENDATION"]:
            return ConversationMachineState.NEW_QUERY, None, None

        return ConversationMachineState.NEW_QUERY, effective_scheme_id, None

    def update_profile_from_slot(
        self,
        state: ConversationState,
        slot_name: str,
        value: Any
    ) -> None:
        """
        Updates session profile and known_slots after extracting a slot value.
        Clears pending question.
        """
        state.known_slots[slot_name] = value
        state.user_profile[slot_name] = value

        # Normalize field mappings in profile
        if slot_name in ["age", "exact_age", "demographic.age"]:
            state.user_profile["age"] = value
            state.known_slots["age"] = value
            state.known_slots["exact_age"] = value
        elif slot_name in ["is_bpl", "economic.is_bpl"]:
            state.user_profile["is_bpl"] = value
            state.known_slots["is_bpl"] = value
        elif slot_name in ["area_type", "geographic.area_type"]:
            state.user_profile["area_type"] = value
            state.known_slots["area_type"] = value
        elif slot_name in ["residence_state", "state", "geographic.state"]:
            state.user_profile["residence_state"] = value
            state.known_slots["residence_state"] = value
            state.known_slots["state"] = value
        elif slot_name in ["monthly_income", "economic.monthly_income_inr"]:
            state.user_profile["monthly_income"] = value
            state.known_slots["monthly_income"] = value
        elif slot_name in ["occupation", "trade", "occupational.occupation_type", "occupational.artisan_trade"]:
            state.user_profile[slot_name] = value
            state.known_slots[slot_name] = value
        elif slot_name in ["gender", "demographic.gender"]:
            state.user_profile["gender"] = value
            state.known_slots["gender"] = value
        elif slot_name in ["marital_status", "demographic.marital_status"]:
            state.user_profile["marital_status"] = value
            state.known_slots["marital_status"] = value
        elif slot_name in ["has_bank_account", "institutional.has_bank_account"]:
            state.user_profile["has_bank_account"] = value
            state.known_slots["has_bank_account"] = value

        # Clear the answered pending question
        state.pending_question = None
        state.pending_question_slot = None

    def record_turn(
        self,
        state: ConversationState,
        user_query: str,
        query_rep: QueryRepresentation,
        active_scheme_id: Optional[str],
        recommended_schemes: List[str],
        candidate_schemes: List[str],
        pending_question_slot: Optional[str],
        system_answer: str,
        state_transition: str
    ) -> None:
        """
        Records the completed turn into conversation history and updates state.
        """
        state.turn_number += 1
        if recommended_schemes:
            state.last_recommended_schemes = recommended_schemes
            if not active_scheme_id:
                active_scheme_id = recommended_schemes[0]

        # Maintain scheme_context_stack: track every distinct scheme discussed in order
        if active_scheme_id and active_scheme_id not in state.scheme_context_stack:
            state.scheme_context_stack.append(active_scheme_id)
        # Also maintain recent_schemes (last N)
        if active_scheme_id and (not state.recent_schemes or state.recent_schemes[-1] != active_scheme_id):
            state.recent_schemes.append(active_scheme_id)
            if len(state.recent_schemes) > 10:
                state.recent_schemes = state.recent_schemes[-10:]

        state.active_scheme_id = active_scheme_id
        if state.primary_intent != "MULTI_SCHEME_RECOMMENDATION" or query_rep.query_type != "SLOT_VALUE":
            state.active_intent = query_rep.primary_intent
            state.primary_intent = query_rep.primary_intent
        state.secondary_intents = query_rep.secondary_intents
        state.candidate_schemes = candidate_schemes

        turn = ConversationTurn(
            turn_number=state.turn_number,
            user_query=user_query,
            query_type=query_rep.query_type,
            primary_intent=query_rep.primary_intent,
            secondary_intents=query_rep.secondary_intents,
            active_scheme_id=active_scheme_id,
            candidate_schemes=candidate_schemes,
            recommended_schemes=recommended_schemes,
            pending_question_slot=pending_question_slot,
            system_answer=system_answer,
            state_transition=state_transition,
            timestamp=time.time()
        )
        state.turn_history.append(turn)
        self.save_session(state)
