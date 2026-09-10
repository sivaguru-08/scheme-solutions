"""
Trains the lightweight scikit-learn intent classifier on synthetic + domain dataset.
Evaluates accuracy on held-out test split and saves model artifact.
"""

import json
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from dataset.generate_dataset import generate_dataset, DATA_FILE
from models.intent_classifier import LightweightIntentClassifier, MODEL_PATH

def train_intent_model():
    print("Generating training dataset...")
    data = generate_dataset()

    queries = [d["query"] for d in data]
    labels = [d["intent"] for d in data]

    X_train, X_test, y_train, y_test = train_test_split(
        queries, labels, test_size=0.2, random_state=42, stratify=labels
    )

    print(f"Training on {len(X_train)} samples, testing on {len(X_test)} samples...")

    clf = LightweightIntentClassifier()
    clf.train(X_train, y_train)

    y_pred = clf.pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print(f"\nModel Accuracy on Test Set: {acc * 100:.2f}%\n")
    print("Classification Report:")
    print(classification_report(y_test, y_pred, digits=4))

    clf.save(MODEL_PATH)
    print(f"Trained intent model saved successfully to: {MODEL_PATH}")

if __name__ == "__main__":
    train_intent_model()
