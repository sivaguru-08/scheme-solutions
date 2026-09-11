import time
from typing import Optional, Dict, Any, List
from schemas.models import (
    QueryRequest, QueryResponse, UserDemographics, SourceCitation,
    GlobalOutcome, ConversationMachineState, QueryType,
    QueryRepresentation, ConfidenceScores
)
from store.database import SchemeRepository
from models.intent_classifier import LightweightIntentClassifier
from models.entity_extractor import DeterministicEntityExtractor
from engine.answer_generator import DeterministicAnswerGenerator
from engine.conversation import ConversationManager

class MasterQAPipeline:
    def __init__(
        self,
        repo: Optional[SchemeRepository] = None,
        conversation_manager: Optional[ConversationManager] = None
    ):
        self.repo = repo or SchemeRepository()
        self.intent_classifier = LightweightIntentClassifier()
        self.entity_extractor = DeterministicEntityExtractor(self.repo)
        self.answer_generator = DeterministicAnswerGenerator(self.repo)
        self.conversation_manager = conversation_manager or ConversationManager(self.repo)

    def process_query(self, request: QueryRequest) -> QueryResponse:
        start_time = time.time()
        query = request.query.strip()

        # Step 1: Session & State Machine Initialization
        session = self.conversation_manager.get_or_create_session(request.conversation_id)

        # Step 2: Contextual Follow-Up / Slot Value Extraction
        is_slot_value = False
        prev_pending_slot = session.pending_question_slot
        if prev_pending_slot:
            extracted, val = self.entity_extractor.extract_pending_slot_value(
                query, prev_pending_slot
            )
            if extracted:
                self.conversation_manager.update_profile_from_slot(
                    session, prev_pending_slot, val
                )
                is_slot_value = True

        # Step 3: Entity & Slot Extraction on Current Query
        slots, extracted_demographics = self.entity_extractor.extract_entities(query)

        # Merge extracted demographics into session user profile
        extracted_dict = extracted_demographics.model_dump(exclude_none=True)
        session.user_profile.update(extracted_dict)
        session.known_slots.update(extracted_dict)

        if request.user_context:
            req_dict = request.user_context.model_dump(exclude_none=True)
            session.user_profile.update(req_dict)
            session.known_slots.update(req_dict)

        merged_profile = UserDemographics(**session.user_profile)

        # Step 3b: Handle Profile-Only Statement (no question, no scheme mention)
        if slots.is_profile_only and not is_slot_value:
            query_rep = QueryRepresentation(
                query_type=QueryType.PROFILE_STATEMENT,
                primary_intent="PROFILE_STATEMENT",
                is_profile_only=True,
                confidence=ConfidenceScores(intent=0.99, scheme=0.0, entities=0.95)
            )
            answer = "Thanks. Your profile has been recorded. What would you like to know about your eligibility or available schemes?"
            self.conversation_manager.record_turn(
                state=session, user_query=query, query_rep=query_rep,
                active_scheme_id=None, recommended_schemes=[], candidate_schemes=[],
                pending_question_slot=None, system_answer=answer,
                state_transition=ConversationMachineState.NEW_QUERY
            )
            return QueryResponse(
                query=query, intent="PROFILE_STATEMENT", intent_confidence=0.99,
                detected_schemes=[], answer=answer, is_deterministic=True,
                retrieval_method="PROFILE_RECORDED", citations=[],
                conversation_id=session.conversation_id, turn_number=session.turn_number,
                global_outcome=GlobalOutcome.PROFILE_RECORDED,
                user_demographics=UserDemographics(**session.user_profile) if session.user_profile else None,
                metadata={"latency_ms": round((time.time() - start_time) * 1000, 2),
                           "slots_extracted": slots.model_dump(),
                           "state_transition": ConversationMachineState.NEW_QUERY,
                           "non_generative_guarantee": True}
            )

        # Step 3c: Handle Ambiguous Scheme (e.g. "Indira Gandhi scheme")
        if slots.is_ambiguous_scheme and slots.ambiguity_prompt and not is_slot_value:
            query_rep = QueryRepresentation(
                query_type=QueryType.AMBIGUOUS_SCHEME,
                primary_intent="CLARIFICATION",
                is_clarification=True,
                confidence=ConfidenceScores(intent=0.95, scheme=0.0, entities=0.9)
            )
            answer = slots.ambiguity_prompt
            self.conversation_manager.record_turn(
                state=session, user_query=query, query_rep=query_rep,
                active_scheme_id=None, recommended_schemes=[], candidate_schemes=[],
                pending_question_slot=None, system_answer=answer,
                state_transition=ConversationMachineState.CLARIFICATION
            )
            return QueryResponse(
                query=query, intent="CLARIFICATION", intent_confidence=0.95,
                detected_schemes=[], answer=answer, is_deterministic=True,
                retrieval_method="AMBIGUITY_DETECTION", citations=[],
                conversation_id=session.conversation_id, turn_number=session.turn_number,
                global_outcome=GlobalOutcome.CLARIFICATION,
                metadata={"latency_ms": round((time.time() - start_time) * 1000, 2),
                           "slots_extracted": slots.model_dump(),
                           "state_transition": ConversationMachineState.CLARIFICATION,
                           "non_generative_guarantee": True}
            )

        # Step 3d: Handle Unknown Scheme (e.g. "thee-shram scheme")
        if slots.is_unknown_scheme and not is_slot_value:
            scheme_name = slots.unknown_scheme_name or "the mentioned scheme"
            query_rep = QueryRepresentation(
                query_type=QueryType.UNKNOWN_SCHEME,
                primary_intent="UNKNOWN_SCHEME",
                unknown_scheme_name=scheme_name,
                confidence=ConfidenceScores(intent=0.99, scheme=0.0, entities=0.9)
            )
            answer = (f"The scheme \"{scheme_name}\" is not part of this system's knowledge base. "
                      f"This system covers Government of India welfare schemes such as PM SVANidhi, "
                      f"PM Vishwakarma, PMUY, Atal Pension Yojana, PM-KISAN, and others. "
                      f"Please ask about a scheme from the knowledge base, or type 'list' to see all available schemes.")
            self.conversation_manager.record_turn(
                state=session, user_query=query, query_rep=query_rep,
                active_scheme_id=None, recommended_schemes=[], candidate_schemes=[],
                pending_question_slot=None, system_answer=answer,
                state_transition=ConversationMachineState.NEW_QUERY
            )
            return QueryResponse(
                query=query, intent="UNKNOWN_SCHEME", intent_confidence=0.99,
                detected_schemes=[], answer=answer, is_deterministic=True,
                retrieval_method="UNKNOWN_SCHEME_DETECTION", citations=[],
                conversation_id=session.conversation_id, turn_number=session.turn_number,
                global_outcome=GlobalOutcome.OUT_OF_SCOPE,
                metadata={"latency_ms": round((time.time() - start_time) * 1000, 2),
                           "slots_extracted": slots.model_dump(),
                           "state_transition": ConversationMachineState.NEW_QUERY,
                           "non_generative_guarantee": True}
            )

        # Step 4: Structured Query Understanding & Classification
        if is_slot_value:
            query_rep = QueryRepresentation(
                query_type="SLOT_VALUE",
                primary_intent="SLOT_VALUE_RESPONSE",
                is_follow_up=True,
                pending_slot=prev_pending_slot,
                confidence=ConfidenceScores(intent=0.99, scheme=1.0, entities=0.95)
            )
        else:
            query_rep = self.intent_classifier.predict_structured(
                query=query,
                session_state=session,
                detected_schemes=slots.scheme_ids
            )

        # Step 5: Context & Reference Resolution
        state_trans, target_scheme_id, ord_val = self.conversation_manager.resolve_context(
            query=query,
            state=session,
            detected_schemes=slots.scheme_ids,
            query_rep=query_rep
        )

        if request.scheme_filter:
            target_scheme_id = request.scheme_filter

        # If this turn answered a pending slot question, resume previous evaluation
        intent = query_rep.primary_intent
        secondary_intents = query_rep.secondary_intents

        if is_slot_value:
            if session.primary_intent in ["MULTI_SCHEME_RECOMMENDATION", "CHECK_ELIGIBILITY"] or not session.active_scheme_id:
                intent = "MULTI_SCHEME_RECOMMENDATION"
                secondary_intents = session.secondary_intents or ["ELIGIBILITY", "BENEFITS", "DOCUMENTS"]
            elif session.active_scheme_id:
                intent = "CHECK_ELIGIBILITY"
                target_scheme_id = session.active_scheme_id
        elif query_rep.query_type == QueryType.OUT_OF_SCOPE or query_rep.primary_intent == "OUT_OF_SCOPE":
            intent = "OUT_OF_SCOPE"
            target_scheme_id = None
        elif any(r in slots.requested_information for r in ["FIRST_LOAN_AMOUNT", "LOAN_AMOUNT", "BENEFIT", "SUBSIDY", "PENSION_AMOUNT"]) and not is_slot_value and query_rep.primary_intent not in ["MULTI_SCHEME_RECOMMENDATION", "MULTI_SCHEME_QUERY", "SCHEME_RECOMMENDATION"]:
            intent = "BENEFITS"

        # Schemeless multi-scheme recommendation routing (e.g. "could he get any benefits from that state")
        if not target_scheme_id and intent != "LIST_SCHEMES" and (
            query_rep.query_type in [QueryType.MULTI_SCHEME_QUERY, QueryType.SCHEME_RECOMMENDATION, "MULTI_SCHEME_RECOMMENDATION"]
            or (intent in ["BENEFITS", "ELIGIBILITY", "CHECK_ELIGIBILITY"] and any(w in query.lower() for w in ["any", "which", "what", "can", "could", "eligible", "get", "state"]))
        ):
            intent = "MULTI_SCHEME_RECOMMENDATION"
            if not secondary_intents:
                secondary_intents = ["BENEFITS", "ELIGIBILITY", "DOCUMENTS"]

        # Step 6: Answer Generation (100% Deterministic & Non-Generative)
        extra_data = {
            "secondary_intents": secondary_intents,
            "candidate_scheme_ids": slots.scheme_ids or session.candidate_schemes,
            "known_slots": session.known_slots,
            "requested_information": slots.requested_information
        }

        gen_result = self.answer_generator.generate_answer(
            intent=intent,
            scheme_id=target_scheme_id,
            query=query,
            user_context=merged_profile if session.user_profile else None,
            extra_data=extra_data
        )

        # Step 7: Update Conversation State
        is_rec_produced = (intent == "MULTI_SCHEME_RECOMMENDATION" and gen_result.get("global_outcome") == GlobalOutcome.ANSWER_PRODUCED)
        if is_rec_produced:
            recommended_schemes = gen_result.get("candidate_schemes", [])
            session.last_recommended_schemes = recommended_schemes
            target_scheme_id = recommended_schemes[0] if recommended_schemes else None
        elif intent == "MULTI_SCHEME_RECOMMENDATION" and gen_result.get("global_outcome") == GlobalOutcome.INSUFFICIENT_INFORMATION:
            recommended_schemes = []
            target_scheme_id = None
        else:
            recommended_schemes = gen_result.get("candidate_schemes", [])

        # Update pending question in session
        session.pending_question = gen_result.get("pending_question")
        session.pending_question_slot = gen_result.get("pending_question_slot")

        self.conversation_manager.record_turn(
            state=session,
            user_query=query,
            query_rep=query_rep,
            active_scheme_id=target_scheme_id,
            recommended_schemes=recommended_schemes,
            candidate_schemes=gen_result.get("candidate_schemes", session.candidate_schemes),
            pending_question_slot=session.pending_question_slot,
            system_answer=gen_result["answer"].strip(),
            state_transition=state_trans
        )

        latency_ms = round((time.time() - start_time) * 1000, 2)

        detected = slots.scheme_names if slots.scheme_names else ([target_scheme_id] if target_scheme_id else [])

        return QueryResponse(
            query=query,
            intent=intent,
            intent_confidence=query_rep.confidence.intent,
            detected_schemes=detected,
            answer=gen_result["answer"].strip(),
            is_deterministic=True,
            retrieval_method=gen_result["retrieval_method"],
            citations=gen_result.get("citations", []),
            conversation_id=session.conversation_id,
            turn_number=session.turn_number,
            secondary_intents=secondary_intents,
            requested_information=slots.requested_information,
            pending_question=session.pending_question,
            candidate_schemes=gen_result.get("candidate_schemes", []),
            recommended_schemes=recommended_schemes,
            global_outcome=gen_result.get("global_outcome"),
            active_scheme_id=target_scheme_id,
            user_demographics=UserDemographics(**session.user_profile) if session.user_profile else None,
            metadata={
                "latency_ms": latency_ms,
                "slots_extracted": slots.model_dump(),
                "state_transition": state_trans,
                "non_generative_guarantee": True,
                "confidence": query_rep.confidence.model_dump()
            }
        )

