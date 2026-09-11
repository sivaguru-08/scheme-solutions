"""
Interactive Command Line Interface for Government Schemes QA Engine.
Allows asking questions in the terminal, testing eligibility profiles, and exploring schemes.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import uuid
from schemas.models import QueryRequest, UserDemographics
from engine.pipeline import MasterQAPipeline
from store.database import SchemeRepository

def run_cli():
    print("=" * 70)
    print("   GOVERNMENT OF INDIA SCHEMES DETERMINISTIC QA SYSTEM")
    print("   (Non-Generative • Zero-Hallucination • Statutory Grounding)")
    print("=" * 70)
    print("Type your question below (or 'list', 'new' to reset conversation, 'help', 'exit' to quit):\n")

    repo = SchemeRepository()
    pipeline = MasterQAPipeline(repo)
    conv_id = f"cli_{uuid.uuid4().hex[:8]}"

    while True:
        try:
            query = input(f"\n[GovScheme-QA] > ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break
            if query.lower() in ["new", "reset", "clear"]:
                conv_id = f"cli_{uuid.uuid4().hex[:8]}"
                print("--- Conversation reset. Starting a new session. ---")
                continue
            if query.lower() == "help":
                print("Examples:")
                print("  - I am an old man. What schemes can I get?")
                print("  - What are the benefits of ONORC?")
                print("  - What documents do I need for PM Vishwakarma?")
                print("  - How to apply for PM Surya Ghar?")
                print("  - Who is excluded from PM-KISAN?")
                print("  - I am 28 years old earning 11000 per month. Am I eligible for PM-SYM?")
                print("  - list")
                print("  - new (reset conversation)")
                continue

            res = pipeline.process_query(QueryRequest(query=query, conversation_id=conv_id))
            conv_id = res.conversation_id
            print("-" * 70)
            print(f"INTENT: {res.intent} (Confidence: {res.intent_confidence:.2f}) | SCHEME: {res.detected_schemes}")
            print(f"RETRIEVAL: {res.retrieval_method} | LATENCY: {res.metadata.get('latency_ms', 0)}ms | TURN: {res.turn_number}")
            print("-" * 70)
            print(res.answer)
            print("-" * 70)
            if res.citations:
                print("CITATIONS & PROVENANCE:")
                for c in res.citations:
                    print(f"  • {c.scheme_name} [{c.section}] -> Page {c.page_numbers}")
            print("=" * 70)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break
        except Exception as e:
            print(f"Error processing query: {e}")

if __name__ == "__main__":
    run_cli()
