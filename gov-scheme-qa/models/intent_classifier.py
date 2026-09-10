import os
import re
import joblib
from typing import Dict, Any, Tuple, Optional
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from schemas.models import IntentResult

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

    def predict(self, query: str) -> IntentResult:
        # Rule-based fast-track patterns for strong disambiguation
        q_lower = query.lower()

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
        if re.search(r'\b(?:how to apply|application process|how do i register|how to enroll|step by step|portal link)\b', q_lower):
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
