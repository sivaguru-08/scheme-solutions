# Deterministic Government Schemes Question-Answering System

A **100% non-generative, deterministic question-answering and eligibility evaluation system** built strictly from official Government of India welfare schemes documentation.

---

## 🚫 Non-Negotiable Architectural Guarantee

- **NO Generative AI / Large Language Models (LLMs)** are used for answer generation.
- **NO LLM fallback or RAG generation**.
- **NO Hallucinations**: Every single answer is strictly derived from canonical structured data, deterministic rules, SQLite FTS5 BM25 retrieval, and pre-compiled templates.
- **Trained ML Scope**: A lightweight scikit-learn statistical model is utilized **only** for query intent classification and slot understanding (< 2ms inference).

---

## 🏛️ System Architecture

```
User Query ("What are the benefits of ONORC?" / "Am I eligible for PM-SYM with age 25?")
                                │
                                ▼
         ┌──────────────────────────────────────────────┐
         │         Stage 4: Query Understanding         │
         │  • Intent Classifier (TF-IDF + LogReg)       │
         │  • Slot / Entity Extractor (Regex + Aliases) │
         └──────────────────────┬───────────────────────┘
                                │ (Intent + SchemeID + Slots)
                                ▼
         ┌──────────────────────────────────────────────┐
         │         Stage 2 & 3: Retrieval & Rules       │
         │  • Exact Structured Query (SQLite)           │
         │  • Deterministic Rule & Exclusion Evaluator  │
         │  • FTS5 BM25 Full-Text Search (Fallback)     │
         └──────────────────────┬───────────────────────┘
                                │ (Retrieved Facts + Provenance)
                                ▼
         ┌──────────────────────────────────────────────┐
         │     Stage 3: Deterministic Answer Engine     │
         │  • Jinja2 Canonical Answer Templates         │
         │  • Statutory Page Citations & Provenance     │
         └──────────────────────┬───────────────────────┘
                                │
                                ▼
          Final Grounded, Provable Answer with Citations (< 10ms)
```

---

## 📂 Project Structure

```
gov-scheme-qa/
├── app/
│   ├── main.py              # FastAPI REST Application
│   ├── cli.py               # Interactive Terminal CLI
│   └── static/
│       └── index.html       # Modern Glassmorphic Web UI
├── engine/
│   ├── pipeline.py          # Master QA Orchestrator
│   ├── rule_evaluator.py    # Deterministic Rule Engine
│   └── answer_generator.py  # Template-Based Answer Generator
├── models/
│   ├── intent_classifier.py # Scikit-Learn TF-IDF + LogisticRegression
│   ├── entity_extractor.py  # Regex & Gazetteer Alias Slot Extractor
│   └── intent_model.joblib  # Serialized Trained Model Artifact
├── store/
│   ├── database.py          # SQLite Schema & FTS5 BM25 Search
│   └── schemes.db           # Relational Knowledge Database
├── templates/
│   └── answer_templates.py  # Canonical Jinja2 Answer Templates
├── schemas/
│   └── models.py            # Pydantic Schemas & Domain Models
├── data/                    # Canonical Machine-Readable JSONs
│   ├── schemes/             # 29 Schemes metadata
│   ├── rules/               # Qualification & Exclusion Rules
│   ├── benefits/            # 55 Quantified Benefits
│   ├── exclusions/          # Statutory Exclusion Criteria
│   ├── documents/           # Required KYC & Proof Checklist
│   ├── procedures/          # Online & Offline Application Steps
│   ├── faqs/                # Official Questions & Answers
│   ├── authorities/         # Ministries, Helplines & Portals
│   ├── relationships/       # Cross-scheme linkages
│   ├── temporal/            # Timelines & renewal cycles
│   └── source_chunks/       # PDF page text chunks
├── audit/                   # Audit & Deliverable Reports
│   ├── scheme_inventory.json
│   ├── field_inventory.json
│   ├── source_mapping.json
│   └── ambiguity_report.json
├── dataset/
│   ├── generate_dataset.py  # Intent Training Data Generator
│   └── intent_dataset.json  # 4,110 Labeled Training Samples
├── scripts/
│   ├── build_canonical_dataset.py
│   ├── load_data.py         # Database & FTS5 ETL Ingestion
│   └── train_model.py       # Model Training Script
└── tests/                   # Automated Pytest Suite (28 Tests)
    ├── test_rules.py
    ├── test_retriever.py
    ├── test_intent_classifier.py
    ├── test_pipeline.py
    ├── test_api.py
    └── test_determinism.py
```

---

## 🚀 Quick Start

### 1. Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Interactive Terminal CLI
```bash
python3 -m app.cli
```

### 3. Run FastAPI Web Application & UI
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser at: `http://localhost:8000`

### 4. Run Automated Test Suite
```bash
PYTHONPATH=. pytest tests/ -v
```

---

## 🔍 REST API Endpoints

- `POST /api/query`: Submits any natural language query and returns grounded answer, citations, and confidence.
- `POST /api/check-eligibility`: Directly evaluates user demographics (age, income, occupation, etc.) against scheme rules.
- `GET /api/schemes`: Lists all 29 indexed schemes with category and ministry metadata.
- `GET /api/schemes/{scheme_id}`: Retrieves complete scheme specifications, rules, benefits, documents, and procedures.
- `GET /api/health`: Health status and non-generative guarantee verification.
