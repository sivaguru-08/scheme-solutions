"""
Stage 6: Query Understanding Model Training Script.
Trains:
1. Intent Classifier (TF-IDF + LinearSVC)
2. Scheme Classifier (TF-IDF + LinearSVC)
Evaluates on test.jsonl and measures:
- accuracy, precision, recall, F1, confusion matrix, and inference latency.
Saves artifacts in models/artifacts/.
"""

import sys
import os
import json
import time
import joblib
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

DATASET_DIR = os.path.join(BASE_DIR, "dataset")
ARTIFACTS_DIR = os.path.join(BASE_DIR, "models", "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def load_jsonl(filename):
    data = []
    with open(os.path.join(DATASET_DIR, filename), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def train_and_evaluate():
    print("=== STAGE 6: TRAINING QUERY-UNDERSTANDING MODELS ===")

    train_data = load_jsonl("train.jsonl")
    test_data = load_jsonl("test.jsonl")

    print(f"Loaded {len(train_data)} train samples, {len(test_data)} test samples.")

    # -------------------------------------------------------------
    # 1. INTENT CLASSIFIER (TF-IDF + LinearSVC with probability calibration)
    # -------------------------------------------------------------
    print("\n[1/2] Training Intent Classifier (TF-IDF + Calibrated LinearSVC)...")
    X_train_intent = [d["query"] for d in train_data]
    y_train_intent = [d["intent"] for d in train_data]
    X_test_intent = [d["query"] for d in test_data]
    y_test_intent = [d["intent"] for d in test_data]

    intent_pipe = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 3), sublinear_tf=True, strip_accents='unicode')),
        ('clf', CalibratedClassifierCV(LinearSVC(C=1.0, random_state=42)))
    ])

    intent_pipe.fit(X_train_intent, y_train_intent)

    # Latency measurement
    start_t = time.perf_counter()
    y_pred_intent = intent_pipe.predict(X_test_intent)
    intent_latency_ms = ((time.perf_counter() - start_t) / len(X_test_intent)) * 1000

    intent_acc = accuracy_score(y_test_intent, y_pred_intent)
    intent_report = classification_report(y_test_intent, y_pred_intent, output_dict=True)
    intent_cm = confusion_matrix(y_test_intent, y_pred_intent).tolist()

    print(f"  -> Intent Accuracy: {intent_acc * 100:.2f}%")
    print(f"  -> Average Inference Latency: {intent_latency_ms:.3f} ms/query")

    intent_model_path = os.path.join(ARTIFACTS_DIR, "intent_model.joblib")
    joblib.dump(intent_pipe, intent_model_path)
    print(f"  -> Saved {intent_model_path}")

    # -------------------------------------------------------------
    # 2. SCHEME CLASSIFIER (TF-IDF + LinearSVC)
    # -------------------------------------------------------------
    print("\n[2/2] Training Scheme Classifier (TF-IDF + Calibrated LinearSVC)...")
    # For scheme classification, label is scheme_id or "NONE" for general/out-of-scope
    X_train_scheme = [d["query"] for d in train_data]
    y_train_scheme = [d["scheme_id"] if d["scheme_id"] is not None else "NONE" for d in train_data]
    X_test_scheme = [d["query"] for d in test_data]
    y_test_scheme = [d["scheme_id"] if d["scheme_id"] is not None else "NONE" for d in test_data]

    scheme_pipe = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 3), sublinear_tf=True, strip_accents='unicode')),
        ('clf', CalibratedClassifierCV(LinearSVC(C=1.0, random_state=42)))
    ])

    scheme_pipe.fit(X_train_scheme, y_train_scheme)

    start_t = time.perf_counter()
    y_pred_scheme = scheme_pipe.predict(X_test_scheme)
    scheme_latency_ms = ((time.perf_counter() - start_t) / len(X_test_scheme)) * 1000

    scheme_acc = accuracy_score(y_test_scheme, y_pred_scheme)
    scheme_report = classification_report(y_test_scheme, y_pred_scheme, output_dict=True)
    scheme_cm = confusion_matrix(y_test_scheme, y_pred_scheme).tolist()

    print(f"  -> Scheme Accuracy: {scheme_acc * 100:.2f}%")
    print(f"  -> Average Inference Latency: {scheme_latency_ms:.3f} ms/query")

    scheme_model_path = os.path.join(ARTIFACTS_DIR, "scheme_model.joblib")
    joblib.dump(scheme_pipe, scheme_model_path)
    print(f"  -> Saved {scheme_model_path}")

    # Also update the primary models/intent_model.joblib so whole pipeline uses the latest model
    joblib.dump(intent_pipe, os.path.join(BASE_DIR, "models", "intent_model.joblib"))

    # Save training metrics report
    report_data = {
        "intent_model": {
            "algorithm": "TfidfVectorizer + Calibrated LinearSVC",
            "accuracy": round(intent_acc, 4),
            "macro_f1": round(intent_report["macro avg"]["f1-score"], 4),
            "latency_ms": round(intent_latency_ms, 3),
            "classes": list(intent_pipe.classes_),
            "classification_report": intent_report
        },
        "scheme_model": {
            "algorithm": "TfidfVectorizer + Calibrated LinearSVC",
            "accuracy": round(scheme_acc, 4),
            "macro_f1": round(scheme_report["macro avg"]["f1-score"], 4),
            "latency_ms": round(scheme_latency_ms, 3),
            "classes": list(scheme_pipe.classes_),
            "classification_report": scheme_report
        }
    }

    metrics_path = os.path.join(ARTIFACTS_DIR, "training_report.json")
    with open(metrics_path, "w") as f:
        json.dump(report_data, f, indent=2)
    print(f"\nSaved metrics report to: {metrics_path}")

    return report_data

if __name__ == "__main__":
    train_and_evaluate()
