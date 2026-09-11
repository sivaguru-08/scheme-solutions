import pytest
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_request_id_generated_and_propagated(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0

def test_custom_request_id_respected(client):
    custom_id = "gov-qa-custom-uuid-4567"
    response = client.get("/health/live", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("x-request-id") == custom_id

def test_response_time_ms_header_present(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert "x-response-time-ms" in response.headers
    latency = float(response.headers["x-response-time-ms"])
    assert latency >= 0.0

def test_structured_error_response_400(client):
    response = client.post("/ask", json={"query": "   "})
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "HTTPException"
    assert data["status_code"] == 400
    assert "Query/Question string cannot be empty" in data["detail"]
    assert "request_id" in data
    assert "timestamp" in data

def test_structured_error_response_404(client):
    response = client.get("/api/schemes/NON_EXISTENT_SCHEME_999")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "HTTPException"
    assert data["status_code"] == 404
    assert "not found" in data["detail"]
    assert "request_id" in data

def test_structured_error_response_422(client):
    response = client.post("/ask", json={"user_context": {"age": "not-an-integer"}})
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "ValidationError"
    assert data["status_code"] == 422
    assert "request_id" in data

def test_concurrent_requests_under_load(client):
    queries = [
        "What are the benefits of PM-SYM?",
        "What documents are needed for ONORC?",
        "How do I apply for PM-KISAN?",
        "Am I eligible for PM-SYM if I am 25 years old?",
        "List all government schemes",
        "Who is excluded from PM-KISAN?",
        "Can a doctor register for PM-KISAN?",
        "Who is the nodal authority for PM-SYM?",
        "What is PM-Surya Ghar?",
        "Tell me about Ayushman Bharat"
    ] * 3  # 30 concurrent requests

    def run_query(q):
        resp = client.post("/ask", json={"query": q})
        return resp.status_code, resp.json()

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(run_query, queries))

    assert len(results) == 30
    for status_code, data in results:
        assert status_code == 200
        assert "answer" in data
        assert len(data["answer"]) > 0

def test_health_readiness_probe(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["checks"]["db_ready"] is True
    assert data["checks"]["models_ready"] is True
    assert data["checks"]["templates_ready"] is True
    assert data["checks"]["schema_valid"] is True
    assert data["generative_ai_used"] is False
    assert data["llm_used"] is False
