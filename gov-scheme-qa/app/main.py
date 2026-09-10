import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from schemas.models import (
    QueryRequest, QueryResponse, UserDemographics,
    EligibilityResult, Scheme
)
from store.database import SchemeRepository
from engine.pipeline import MasterQAPipeline
from engine.rule_evaluator import DeterministicRuleEvaluator

app = FastAPI(
    title="Government Schemes Deterministic QA Engine",
    description="A 100% non-generative, deterministic question-answering and eligibility evaluation system for Government of India schemes.",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

repo = SchemeRepository()
pipeline = MasterQAPipeline(repo)
evaluator = DeterministicRuleEvaluator(repo)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

class DirectEligibilityRequest(BaseModel):
    scheme_id: str
    demographics: UserDemographics

@app.get("/api/health")
def health_check():
    schemes = repo.get_all_schemes()
    return {
        "status": "HEALTHY",
        "schemes_loaded": len(schemes),
        "architecture": "Deterministic Rule & FTS5 BM25 Engine with Scikit-Learn Query Understanding",
        "generative_ai_used": False,
        "llm_used": False
    }

@app.get("/api/schemes")
def list_schemes(category: Optional[str] = None):
    all_schemes = repo.get_all_schemes()
    if category:
        all_schemes = [s for s in all_schemes if s.get("category", "").lower() == category.lower()]
    return {
        "count": len(all_schemes),
        "schemes": [
            {
                "scheme_id": s["scheme_id"],
                "official_name": s["official_name"],
                "abbreviation": s.get("abbreviation"),
                "category": s.get("category"),
                "ministry": s.get("ministry"),
                "source_pages": s.get("source_pages", [])
            }
            for s in all_schemes
        ]
    }

@app.get("/api/schemes/{scheme_id}")
def get_scheme_detail(scheme_id: str):
    scheme = repo.get_scheme_by_id(scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail=f"Scheme '{scheme_id}' not found")

    benefits = repo.get_benefits_for_scheme(scheme_id)
    rules = repo.get_rules_for_scheme(scheme_id)
    exclusions = repo.get_exclusions_for_scheme(scheme_id)
    documents = repo.get_documents_for_scheme(scheme_id)
    procedure = repo.get_procedure_for_scheme(scheme_id)
    faqs = repo.get_faqs_for_scheme(scheme_id)
    authority = repo.get_authority_for_scheme(scheme_id)

    return {
        "scheme": scheme,
        "benefits": benefits,
        "rules": rules,
        "exclusions": exclusions,
        "documents": documents,
        "procedure": procedure,
        "faqs": faqs,
        "authority": authority
    }

@app.post("/api/query", response_model=QueryResponse)
def handle_query(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return pipeline.process_query(request)

@app.post("/api/check-eligibility", response_model=EligibilityResult)
def direct_check_eligibility(req: DirectEligibilityRequest):
    return evaluator.evaluate_scheme(req.scheme_id, req.demographics)

# Mount static files if index.html exists
if os.path.exists(os.path.join(STATIC_DIR, "index.html")):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def serve_ui():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
