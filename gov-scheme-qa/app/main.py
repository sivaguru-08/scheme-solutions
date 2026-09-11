import os
import sys
import time
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.config import config
from app.logging_config import logger
from schemas.models import (
    QueryRequest, QueryResponse, UserDemographics,
    EligibilityResult, Scheme
)
from store.database import DB_PATH, SchemeRepository
from engine.pipeline import MasterQAPipeline
from engine.rule_evaluator import DeterministicRuleEvaluator
from templates.answer_templates import env_strict, TEMPLATE_REGISTRY

# Lifespan startup/shutdown state
startup_state = {
    "db_ready": False,
    "models_ready": False,
    "templates_ready": False,
    "schema_valid": False
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Verify database exists and connects
    if os.path.exists(config.DB_PATH) and os.path.getsize(config.DB_PATH) > 0:
        startup_state["db_ready"] = True
    else:
        logger.error("Database check failed: missing or empty", extra={"db_path": config.DB_PATH})
        raise RuntimeError(f"Database missing at {config.DB_PATH}")

    # 2. Verify model artifacts exist
    intent_model_path = os.path.join(BASE_DIR, "models", "artifacts", "intent_model.joblib")
    legacy_model_path = os.path.join(BASE_DIR, "models", "intent_model.joblib")
    if os.path.exists(intent_model_path) or os.path.exists(legacy_model_path):
        startup_state["models_ready"] = True
    else:
        logger.error("Model artifact missing", extra={"path": intent_model_path})
        raise RuntimeError(f"Model artifact missing at {intent_model_path}")

    # 3. Verify templates compile
    for name, raw_tmpl in TEMPLATE_REGISTRY.items():
        try:
            env_strict.from_string(raw_tmpl)
        except Exception as e:
            logger.error(f"Template compilation failed for {name}", extra={"error": str(e)})
            raise RuntimeError(f"Template compilation failed for {name}: {e}")
    startup_state["templates_ready"] = True

    # 4. Verify schema validity
    repo_check = SchemeRepository()
    schemes = repo_check.get_all_schemes()
    if len(schemes) >= 25:
        startup_state["schema_valid"] = True
    else:
        logger.error("Schema validation failed: too few schemes", extra={"count": len(schemes)})
        raise RuntimeError(f"Schema check failed: only {len(schemes)} schemes found")

    logger.info("All startup readiness checks passed: DB, Models, Templates, Schema.")
    yield
    # Graceful shutdown
    logger.info("Application shutting down gracefully.")

app = FastAPI(
    title="Government Schemes Deterministic QA Engine",
    description="A 100% non-generative, deterministic question-answering system for Government of India schemes.",
    version="1.0.0",
    lifespan=lifespan
)

# -------------------------------------------------------------
# PRODUCTION MIDDLEWARE
# -------------------------------------------------------------
class RequestAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Extract or generate Request ID
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        
        client_ip = request.client.host if request.client else "unknown"
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)

            # Attach headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time-Ms"] = str(duration_ms)

            # Log request
            extra = {
                "request_id": request_id,
                "client_ip": client_ip,
                "latency_ms": duration_ms
            }
            logger.info(
                f"{request.method} {request.url.path} returned {response.status_code} in {duration_ms}ms",
                extra=extra
            )
            return response
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 3)
            extra = {
                "request_id": request_id,
                "client_ip": client_ip,
                "latency_ms": duration_ms
            }
            logger.error(
                f"Unhandled error processing {request.method} {request.url.path}: {exc}",
                extra=extra,
                exc_info=True
            )
            raise exc

app.add_middleware(RequestAuditMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# GLOBAL EXCEPTION HANDLERS
# -------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    return JSONResponse(
        status_code=exc.status_code,
        headers={"X-Request-ID": request_id},
        content={
            "error": "HTTPException",
            "status_code": exc.status_code,
            "detail": exc.detail,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        headers={"X-Request-ID": request_id},
        content={
            "error": "ValidationError",
            "status_code": 422,
            "detail": exc.errors(),
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    logger.error(f"Internal server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers={"X-Request-ID": request_id},
        content={
            "error": "InternalServerError",
            "status_code": 500,
            "detail": "An internal server error occurred.",
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )

repo = SchemeRepository()
pipeline = MasterQAPipeline(repo)
evaluator = DeterministicRuleEvaluator(repo)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

class AskRequest(BaseModel):
    question: Optional[str] = None
    query: Optional[str] = None
    scheme_filter: Optional[str] = None
    user_context: Optional[UserDemographics] = None
    conversation_id: Optional[str] = None

class DirectEligibilityRequest(BaseModel):
    scheme_id: str
    demographics: UserDemographics

# -------------------------------------------------------------
# MANDATORY HEALTH & OPERATIONAL ENDPOINTS
# -------------------------------------------------------------

@app.get("/health/live")
def liveness_check():
    """Liveness probe confirming process is running."""
    return {"status": "ALIVE"}

@app.get("/health/ready")
def readiness_check():
    """Readiness probe verifying DB, models, templates, and schema."""
    is_ready = all(startup_state.values())
    status_code = 200 if is_ready else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "READY" if is_ready else "NOT_READY",
            "checks": startup_state,
            "generative_ai_used": False,
            "llm_used": False
        }
    )

@app.post("/ask")
def ask_question(req: AskRequest):
    """Primary question answering endpoint with multi-turn support."""
    q = (req.question or req.query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Query/Question string cannot be empty")

    query_req = QueryRequest(
        query=q,
        scheme_filter=req.scheme_filter,
        user_context=req.user_context,
        conversation_id=req.conversation_id
    )
    res = pipeline.process_query(query_req)

    return {
        "question": q,
        "answer": res.answer,
        "intent": res.intent,
        "intent_confidence": res.intent_confidence,
        "detected_schemes": res.detected_schemes,
        "retrieval_method": res.retrieval_method,
        "is_deterministic": res.is_deterministic,
        "citations": [c.model_dump() for c in res.citations],
        "conversation_id": res.conversation_id,
        "turn_number": res.turn_number,
        "secondary_intents": res.secondary_intents,
        "pending_question": res.pending_question,
        "candidate_schemes": res.candidate_schemes,
        "global_outcome": res.global_outcome,
        "metadata": res.metadata
    }


# -------------------------------------------------------------
# EXISTING EXTENDED API ENDPOINTS
# -------------------------------------------------------------

@app.get("/api/health")
def api_health():
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

    return {
        "scheme": scheme,
        "benefits": repo.get_benefits_for_scheme(scheme_id),
        "rules": repo.get_rules_for_scheme(scheme_id),
        "exclusions": repo.get_exclusions_for_scheme(scheme_id),
        "documents": repo.get_documents_for_scheme(scheme_id),
        "procedure": repo.get_procedure_for_scheme(scheme_id),
        "faqs": repo.get_faqs_for_scheme(scheme_id),
        "authority": repo.get_authority_for_scheme(scheme_id)
    }

@app.post("/api/query", response_model=QueryResponse)
def handle_query(request: QueryRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    return pipeline.process_query(request)

@app.post("/api/check-eligibility", response_model=EligibilityResult)
def direct_check_eligibility(req: DirectEligibilityRequest):
    return evaluator.evaluate_scheme(req.scheme_id, req.demographics)

if os.path.exists(os.path.join(STATIC_DIR, "index.html")):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def serve_ui():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
