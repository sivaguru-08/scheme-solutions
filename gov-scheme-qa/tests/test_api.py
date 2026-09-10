import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["schemes_loaded"] == 29
    assert data["llm_used"] is False

def test_list_schemes_api(client):
    res = client.get("/api/schemes")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 29

def test_scheme_detail_api(client):
    res = client.get("/api/schemes/SCH_ONORC")
    assert res.status_code == 200
    data = res.json()
    assert data["scheme"]["official_name"] == "One Nation One Ration Card"
    assert len(data["benefits"]) > 0

def test_query_api_onorc(client):
    res = client.post("/api/query", json={"query": "What are the benefits of ONORC?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "BENEFITS"
    assert "Fair Price Shop" in data["answer"]
    assert len(data["citations"]) > 0

def test_direct_eligibility_api(client):
    payload = {
        "scheme_id": "SCH_PMSYM",
        "demographics": {
            "age": 30,
            "monthly_income": 12000,
            "is_unorganised_worker": True,
            "is_income_tax_payer": False,
            "is_epfo_or_esic_member": False
        }
    }
    res = client.post("/api/check-eligibility", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_eligible"] is True
    assert data["confidence"] == 1.0
