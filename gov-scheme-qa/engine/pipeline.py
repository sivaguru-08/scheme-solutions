import time
from typing import Optional, Dict, Any, List
from schemas.models import QueryRequest, QueryResponse, UserDemographics, SourceCitation
from store.database import SchemeRepository
from models.intent_classifier import LightweightIntentClassifier
from models.entity_extractor import DeterministicEntityExtractor
from engine.answer_generator import DeterministicAnswerGenerator

class MasterQAPipeline:
    def __init__(self, repo: Optional[SchemeRepository] = None):
        self.repo = repo or SchemeRepository()
        self.intent_classifier = LightweightIntentClassifier()
        self.entity_extractor = DeterministicEntityExtractor(self.repo)
        self.answer_generator = DeterministicAnswerGenerator(self.repo)

    def process_query(self, request: QueryRequest) -> QueryResponse:
        start_time = time.time()
        query = request.query.strip()

        # Step 1: Entity & Slot Extraction
        slots, extracted_demographics = self.entity_extractor.extract_entities(query)

        # Step 2: Intent Classification
        intent_res = self.intent_classifier.predict(query)
        intent = intent_res.intent
        confidence = intent_res.confidence

        # Step 3: Determine Target Scheme
        target_scheme_id = None
        if request.scheme_filter:
            target_scheme_id = request.scheme_filter
        elif slots.scheme_ids:
            target_scheme_id = slots.scheme_ids[0]

        # Step 4: Merge Demographics Context
        user_context = request.user_context
        if user_context is None:
            # If query had explicit slot mentions (e.g. "I am 25 years old earning 12000")
            if (extracted_demographics.age is not None or
                extracted_demographics.monthly_income is not None or
                extracted_demographics.occupation is not None or
                extracted_demographics.is_unorganised_worker is not None):
                user_context = extracted_demographics

        # If user context is provided and intent was ambiguous, promote to CHECK_ELIGIBILITY
        if user_context and intent in ["OVERVIEW", "ELIGIBILITY"]:
            intent = "CHECK_ELIGIBILITY"

        # Step 5: Answer Generation (Deterministic & Non-Generative)
        gen_result = self.answer_generator.generate_answer(
            intent=intent,
            scheme_id=target_scheme_id,
            query=query,
            user_context=user_context
        )

        latency_ms = round((time.time() - start_time) * 1000, 2)

        return QueryResponse(
            query=query,
            intent=intent,
            intent_confidence=confidence,
            detected_schemes=slots.scheme_names if slots.scheme_names else ([target_scheme_id] if target_scheme_id else []),
            answer=gen_result["answer"].strip(),
            is_deterministic=True,
            retrieval_method=gen_result["retrieval_method"],
            citations=gen_result.get("citations", []),
            metadata={
                "latency_ms": latency_ms,
                "slots_extracted": slots.model_dump(),
                "model": "scikit-learn-tfidf-logistic-regression",
                "non_generative_guarantee": True
            }
        )
