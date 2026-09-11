import os
import re
import joblib
from typing import Dict, Any, Tuple, Optional
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from schemas.models import (
    IntentResult, QueryRepresentation, QueryType,
    ConfidenceScores, MultiIntentResult
)

MODEL_PATH = "/home/sivaguru/Documents/slm/gov-scheme-qa/models/intent_model.joblib"

class LightweightIntentClassifier:
    def __init__(self, model_path: str = MODEL_PATH):
        self.model_path = model_path
        self.pipeline: Optional[Pipeline] = None
        if os.path.exists(model_path):
            self.load()

    def train(self, queries: list, labels: list):
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                ngram_range=(1, 3),
                sublinear_tf=True,
                lowercase=True,
                strip_accents='unicode',
                min_df=1
            )),
            ('clf', LogisticRegression(
                C=2.0,
                max_iter=1000,
                class_weight='balanced',
                random_state=42
            ))
        ])
        self.pipeline.fit(queries, labels)

    def save(self, path: Optional[str] = None):
        target = path or self.model_path
        os.makedirs(os.path.dirname(target), exist_ok=True)
        joblib.dump(self.pipeline, target)

    def load(self, path: Optional[str] = None):
        target = path or self.model_path
        self.pipeline = joblib.load(target)

    def is_out_of_scope(self, query: str) -> bool:
        q_lower = query.strip().lower()
        out_of_scope_patterns = [
            r'\b(?:recipe|chocolate\s*cake|cake|pizza|burger|bake|cooking)\b',
            r'\b(?:who won|world\s*cup|ipl|cricket\s*score|football|fifa)\b',
            r'\b(?:capital of|president of|prime minister of france|weather in|what is the weather|weather forecast)\b',
            r'\b(?:python code|write code|javascript|programming|algorithm|write python)\b',
            r'\b(?:lyrics|song|movie|actor|actress|hollywood|bollywood|tell me a joke|joke)\b',
            r'\b(?:what are u doing|what are you doing|how are you|who are you|wassup|what\'s up)\b',
            r'\b(?:niggu|nigger|nigga|bitch|fuck|shit|asshole|idiot|bastard)\b',
        ]
        return any(re.search(p, q_lower) for p in out_of_scope_patterns)

    def predict(self, query: str) -> IntentResult:
        q_lower = query.lower()

        # 0. Strict Out of Scope Check
        if self.is_out_of_scope(query):
            return IntentResult(intent="OUT_OF_SCOPE", confidence=0.99)

        # 0b. Scheme recommendation query
        if re.search(r'\b(?:what schemes? (?:can i|could i|are|do i)|which schemes? (?:can i|could i|are)|schemes? can i get|which pension schemes?|what can i get)\b', q_lower):
            return IntentResult(intent="MULTI_SCHEME_RECOMMENDATION", confidence=0.98)

        # Authority / Helpline
        if re.search(r'\b(?:which ministry|helpline|toll free|customer care|phone number|contact details|nodal agency|grievance)\b', q_lower):
            return IntentResult(intent="AUTHORITY", confidence=0.98)

        # Informational / Overview queries for schemes
        if re.search(r'\b(?:tell me about|explain|what is|give me information about|how does .* work|information about|overview of|details of)\b', q_lower) and not re.search(r'\b(?:am i eligible|can i apply|do i qualify|what schemes|which schemes|helpline|ministry)\b', q_lower):
            return IntentResult(intent="OVERVIEW", confidence=0.98)

        # Application / procedure queries
        if re.search(r'\b(?:can i apply it now|can i apply now|how do i apply|how to apply|how can i apply|where do i apply|where to apply|how do i register|how to register|how to enroll|application process|application procedure|step by step)\b', q_lower):
            return IntentResult(intent="PROCEDURE", confidence=0.98)

        # Check eligibility intent
        if re.search(r'\b(?:am i eligible|can i apply|do i qualify|check my eligibility|can a [a-z]+ get|i am \d+)\b', q_lower):
            return IntentResult(intent="CHECK_ELIGIBILITY", confidence=0.98)

        # General eligibility intent
        if re.search(r'\b(?:who is eligible|eligibility criteria|eligibility conditions|qualification|age limit|income limit)\b', q_lower):
            return IntentResult(intent="ELIGIBILITY", confidence=0.96)

        # Exclusions
        if re.search(r'\b(?:who is excluded|who cannot apply|disqualification|ineligible|rejected)\b', q_lower):
            return IntentResult(intent="EXCLUSIONS", confidence=0.97)

        # Documents
        if re.search(r'\b(?:documents? required|papers? needed|kyc|certificates? mandatory|checklist)\b', q_lower):
            return IntentResult(intent="DOCUMENTS", confidence=0.97)

        # Procedure
        if re.search(r'\b(?:how to apply|application process|how do i register|how to enroll|step by step|portal link|how can i get|how do i get|how to get|how can i claim|how to claim)\b', q_lower) and not re.search(r'\b(?:what|which)\s*schemes?\b', q_lower):
            return IntentResult(intent="PROCEDURE", confidence=0.96)

        # Authority / Helpline
        if re.search(r'\b(?:which ministry|helpline|toll free|customer care|phone number|contact details|nodal agency|grievance)\b', q_lower):
            return IntentResult(intent="AUTHORITY", confidence=0.98)

        # Benefits
        if re.search(r'\b(?:benefits?|how much money|pension amount|subsidy amount|financial assistance|coverage)\b', q_lower):
            return IntentResult(intent="BENEFITS", confidence=0.95)

        # List schemes
        if re.search(r'\b(?:list all schemes|show all schemes|what schemes are available|schemes catalog)\b', q_lower):
            return IntentResult(intent="LIST_SCHEMES", confidence=0.99)

        # If trained pipeline is loaded, run statistical classifier
        if self.pipeline:
            probs = self.pipeline.predict_proba([query])[0]
            classes = self.pipeline.classes_
            best_idx = probs.argmax()
            best_intent = classes[best_idx]
            best_conf = float(probs[best_idx])

            # If confidence is too low or out of domain
            if best_conf < 0.25 and best_intent != "OVERVIEW":
                best_intent = "OUT_OF_SCOPE"

            all_scores = {cls: round(float(prob), 4) for cls, prob in zip(classes, probs)}
            return IntentResult(intent=best_intent, confidence=round(best_conf, 4), all_scores=all_scores)

        # Default fallback
        return IntentResult(intent="OVERVIEW", confidence=0.60)

    def predict_structured(
        self,
        query: str,
        session_state: Optional[Any] = None,
        detected_schemes: Optional[List[str]] = None
    ) -> QueryRepresentation:
        """
        Produces rich structured QueryRepresentation with QueryType, primary/secondary intents,
        and follow-up indicators.
        """
        q_lower = query.strip().lower()
        detected_schemes = detected_schemes or []

        # 1. Check Out of Scope
        if self.is_out_of_scope(query):
            return QueryRepresentation(
                query_type=QueryType.OUT_OF_SCOPE,
                primary_intent="OUT_OF_SCOPE",
                confidence=ConfidenceScores(intent=0.99, scheme=0.0, entities=0.0)
            )

        # 2. Check Slot Value Follow-up
        if session_state and session_state.pending_question_slot:
            # Check if query provides a short/direct answer
            is_short = len(query.strip().split()) <= 4
            is_number = bool(re.search(r'^\s*(?:i(?:\'m|\s*am)\s*)?\d{1,3}\b', q_lower))
            is_boolean = bool(re.search(r'\b(?:yes|no|y|n|haan|nahi|yup|nope|true|false|bpl|apl)\b', q_lower))
            is_area = bool(re.search(r'\b(?:rural|urban|village|city)\b', q_lower))
            is_state = any(st in q_lower for st in ["kerala", "gujarat", "punjab", "bihar", "tamil nadu", "delhi"])

            if is_short or is_number or is_boolean or is_area or is_state:
                return QueryRepresentation(
                    query_type="SLOT_VALUE",
                    primary_intent="SLOT_VALUE_RESPONSE",
                    is_follow_up=True,
                    pending_slot=session_state.pending_question_slot,
                    confidence=ConfidenceScores(intent=0.99, scheme=1.0, entities=0.95)
                )

        # 3. Check Comparison
        comparison_keywords = ["compare", "comparison", "difference between", " vs ", " versus "]
        if any(kw in q_lower for kw in comparison_keywords) or (len(detected_schemes) >= 2 and ("better" in q_lower or "or" in q_lower)):
            return QueryRepresentation(
                query_type=QueryType.SCHEME_COMPARISON,
                primary_intent="COMPARISON",
                candidate_scheme_ids=detected_schemes,
                confidence=ConfidenceScores(intent=0.98, scheme=0.95, entities=0.9)
            )

        # 4. Check Multi-Scheme Recommendation & Multi-Intent
        rec_patterns = [
            r'\bwhat\s*schemes?\s*(?:can\s*i|could\s*i|are\s*there|are\s*available|do\s*i)\b',
            r'\bwhich\s*schemes?\s*(?:can\s*i|could\s*i|are\s*there|are\s*available|match)\b',
            r'\bschemes?\s*(?:can\s*i\s*get|for\s*me|match\s*me|i\s*can\s*apply)\b',
            r'\bwhich\s*pension\s*schemes?\b',
            r'\bwhat\s*can\s*i\s*get\b',
            r'\b(?:could|can)\s*i\s*get\s*(?:any\s*)?(?:cash|money|benefit|help|assistance|pension|schemes?)\b',
            r'\bsuggest\s*schemes?\b',
            r'\bwhat\s*are\s*the\s*schemes?\b'
        ]
        if any(re.search(p, q_lower) for p in rec_patterns):
            secondary = []
            if re.search(r'\b(?:critera|criteria|eligib|qualif|condition|age\s*limit)\b', q_lower):
                secondary.append("ELIGIBILITY")
            if re.search(r'\b(?:benefits?|benefitt?ed|payout|financial\s*assistance|money|pension|cash)\b', q_lower):
                secondary.append("BENEFITS")
            if re.search(r'\b(?:documents?|papers?|proofs?|checklist|kyc)\b', q_lower):
                secondary.append("DOCUMENTS")
                secondary.append("DOCUMENT_REQUIREMENTS")
            if re.search(r'\b(?:how\s*to\s*apply|apply|procedure|process|steps|register)\b', q_lower):
                secondary.append("PROCEDURE")

            return QueryRepresentation(
                query_type="MULTI_SCHEME_RECOMMENDATION",
                primary_intent="MULTI_SCHEME_RECOMMENDATION",
                secondary_intents=secondary,
                confidence=ConfidenceScores(intent=0.98, scheme=0.9, entities=0.9)
            )

        # 5. Check Contextual Application Queries ("can i apply it now", "how do i apply", etc.)
        if re.search(r'\b(?:can i apply it now|can i apply now|how do i apply|how to apply|how can i apply|where do i apply|application process|application procedure)\b', q_lower):
            active_sid = None
            if detected_schemes:
                active_sid = detected_schemes[0]
            elif session_state:
                active_sid = session_state.active_scheme_id or (session_state.last_recommended_schemes[0] if session_state.last_recommended_schemes else None)

            return QueryRepresentation(
                query_type=QueryType.SPECIFIC_SCHEME_QUERY,
                primary_intent="PROCEDURE",
                scheme_id=active_sid,
                is_follow_up=True if not detected_schemes and active_sid else False,
                confidence=ConfidenceScores(intent=0.98, scheme=0.95 if active_sid else 0.5, entities=0.9)
            )

        # 6. Check Follow-Up Reference Queries (e.g. "What about the second one?", "Tell me more about the second one")
        if re.search(r'\b(?:first|second|third|fourth|1st|2nd|3rd|4th)\s*(?:one|scheme)?\b', q_lower):
            secondary = []
            if re.search(r'\b(?:documents?|papers?)\b', q_lower):
                primary = "DOCUMENTS"
            elif re.search(r'\b(?:how\s*to\s*apply|apply|procedure)\b', q_lower):
                primary = "PROCEDURE"
            elif re.search(r'\b(?:benefits?|payout)\b', q_lower):
                primary = "BENEFITS"
            elif re.search(r'\b(?:criteria|eligib)\b', q_lower):
                primary = "ELIGIBILITY"
            else:
                primary = "OVERVIEW"

            return QueryRepresentation(
                query_type="REFERENCE_QUERY",
                primary_intent=primary,
                secondary_intents=secondary,
                is_follow_up=True,
                references=[query],
                confidence=ConfidenceScores(intent=0.95, scheme=0.9, entities=0.85)
            )

        # Context-dependent query without scheme mention (e.g. "What documents do I need?", "How do I apply?")
        active_target = None
        if session_state:
            active_target = session_state.active_scheme_id or (session_state.last_recommended_schemes[0] if session_state.last_recommended_schemes else None)

        if not detected_schemes and active_target:
            if re.search(r'\b(?:documents?|papers?|proofs?)\b', q_lower):
                return QueryRepresentation(
                    query_type=QueryType.SPECIFIC_SCHEME_QUERY,
                    primary_intent="DOCUMENTS",
                    scheme_id=active_target,
                    is_follow_up=True,
                    confidence=ConfidenceScores(intent=0.95, scheme=0.9, entities=0.85)
                )
            elif re.search(r'\b(?:how\s*do\s*i\s*apply|how\s*to\s*apply|procedure|application\s*process)\b', q_lower):
                return QueryRepresentation(
                    query_type=QueryType.SPECIFIC_SCHEME_QUERY,
                    primary_intent="PROCEDURE",
                    scheme_id=active_target,
                    is_follow_up=True,
                    confidence=ConfidenceScores(intent=0.95, scheme=0.9, entities=0.85)
                )
            elif re.search(r'\b(?:benefits?|payout|pension)\b', q_lower):
                return QueryRepresentation(
                    query_type=QueryType.SPECIFIC_SCHEME_QUERY,
                    primary_intent="BENEFITS",
                    scheme_id=active_target,
                    is_follow_up=True,
                    confidence=ConfidenceScores(intent=0.95, scheme=0.9, entities=0.85)
                )

        # 7. Fall back to standard predict
        std_res = self.predict(query)

        # If low confidence (< 0.45) and no scheme detected: route safely to OUT_OF_SCOPE
        if std_res.intent == "OUT_OF_SCOPE" or (not detected_schemes and std_res.confidence < 0.45):
            return QueryRepresentation(
                query_type=QueryType.OUT_OF_SCOPE,
                primary_intent="OUT_OF_SCOPE",
                confidence=ConfidenceScores(intent=0.99, scheme=0.0, entities=0.0)
            )

        q_type = QueryType.SPECIFIC_SCHEME_QUERY if detected_schemes else QueryType.MULTI_SCHEME_QUERY
        if std_res.intent == "LIST_SCHEMES":
            q_type = QueryType.MULTI_SCHEME_QUERY

        return QueryRepresentation(
            query_type=q_type,
            primary_intent=std_res.intent,
            secondary_intents=[],
            scheme_id=detected_schemes[0] if detected_schemes else None,
            candidate_scheme_ids=detected_schemes,
            confidence=ConfidenceScores(intent=std_res.confidence, scheme=1.0 if detected_schemes else 0.5, entities=0.8)
        )

