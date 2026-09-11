"""
Stage 3: Direct Deterministic Lookup Tests.
Tests deterministic retrieval of:
1. Overview lookup
2. Benefits lookup
3. Documents lookup
4. Application procedure lookup
5. Registration lookup
6. Administrative authorities lookup
7. FAQ lookup
All tests run against actual records derived from scheme 2.pdf.
"""

import sys
import os
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from store.database import SchemeRepository

@pytest.fixture
def repo():
    return SchemeRepository()

# 1. Overview Lookup
def test_direct_overview_lookup_onorc(repo):
    scheme = repo.get_scheme_by_id("SCH_ONORC")
    assert scheme is not None
    assert scheme["scheme_id"] == "SCH_ONORC"
    assert scheme["official_name"] == "One Nation One Ration Card"
    assert "portability" in scheme["description"].lower()
    assert scheme["ministry"] == "Ministry of Consumer Affairs, Food & Public Distribution"
    assert scheme["source_pages"] == [1, 2]

def test_direct_overview_lookup_pmsurya(repo):
    scheme = repo.get_scheme_by_id("SCH_PMSURYA")
    assert scheme is not None
    assert "Muft Bijli" in scheme["official_name"]
    assert scheme["category"] == "Renewable Energy"
    assert scheme["geographic_scope"] == "NATIONAL"

# 2. Benefits Lookup
def test_direct_benefits_lookup_onorc(repo):
    benefits = repo.get_benefits_for_scheme("SCH_ONORC")
    assert len(benefits) >= 1
    benefit = benefits[0]
    assert benefit["scheme_id"] == "SCH_ONORC"
    assert benefit["benefit_type"] == "PDS_PORTABILITY"
    assert "81 crore" in benefit["beneficiary_count"].lower()
    assert "36 States/UTs" in benefit["coverage"]
    assert benefit["source_pages"] == [1]

def test_direct_benefits_lookup_pmsym(repo):
    benefits = repo.get_benefits_for_scheme("SCH_PMSYM")
    assert len(benefits) >= 1
    assert any("3000" in b.get("description", "") for b in benefits)

# 3. Documents Required Lookup
def test_direct_documents_lookup_onorc(repo):
    docs = repo.get_documents_for_scheme("SCH_ONORC")
    assert docs is not None
    assert docs["scheme_id"] == "SCH_ONORC"
    mandatory_names = [d["name"] for d in docs["mandatory"]]
    assert "Ration Card" in mandatory_names
    assert "Aadhaar Card" in mandatory_names
    assert docs["source_pages"] == [2]

def test_direct_documents_lookup_pmsurya(repo):
    docs = repo.get_documents_for_scheme("SCH_PMSURYA")
    assert docs is not None
    mandatory_names = [d["name"] for d in docs["mandatory"]]
    assert "Electricity Bill" in mandatory_names
    assert "Aadhaar Card" in mandatory_names

# 4. Application Procedure Lookup
def test_direct_procedure_application_lookup_onorc(repo):
    proc = repo.get_procedure_for_scheme("SCH_ONORC")
    assert proc is not None
    assert proc["mode"] == "HYBRID"
    assert len(proc["online_steps"]) > 0
    assert any("MERA RATION" in step for step in proc["online_steps"])
    assert len(proc["offline_steps"]) > 0
    assert any("Fair Price Shop" in step for step in proc["offline_steps"])
    assert "Zero" in proc["fees"]

# 5. Registration Lookup
def test_direct_registration_lookup_pmsym(repo):
    proc = repo.get_procedure_for_scheme("SCH_PMSYM")
    assert proc is not None
    assert proc["mode"] == "OFFLINE_AND_ONLINE"
    assert any("maandhan.in" in s or "e-Shram" in s for s in proc["online_steps"])
    assert any("Common Services Centre" in s or "CSC" in s for s in proc["offline_steps"])
    assert proc["source_pages"] == [3]

# 6. Authorities Lookup
def test_direct_authorities_lookup_onorc(repo):
    auth = repo.get_authority_for_scheme("SCH_ONORC")
    assert auth is not None
    assert auth["scheme_id"] == "SCH_ONORC"
    assert "Food & Public Distribution" in auth["ministry"]
    assert "1967" in auth["helpline"]
    assert auth["source_pages"] == [1]

def test_direct_authorities_lookup_pmkisan(repo):
    auth = repo.get_authority_for_scheme("SCH_PMKISAN")
    assert auth is not None
    assert "Agriculture and Farmers Welfare" in auth["ministry"]
    assert "155261" in auth["helpline"]
    assert auth["portal_url"] == "https://pmkisan.gov.in"

# 7. FAQ Lookup
def test_direct_faq_lookup_onorc(repo):
    faqs = repo.get_faqs_for_scheme("SCH_ONORC")
    assert len(faqs) >= 3
    q_texts = [f["question"] for f in faqs]
    assert any("Mumbai" in q and "Rajasthan" in q for q in q_texts)
    assert any("FPS" in q for q in q_texts)
    # Validate exact answer
    mumbai_faq = next(f for f in faqs if "Mumbai" in f["question"])
    assert "same Ration Card" in mumbai_faq["answer"]
    assert mumbai_faq["source_pages"] == [2]

def test_direct_faq_lookup_pmkisan(repo):
    faqs = repo.get_faqs_for_scheme("SCH_PMKISAN")
    assert len(faqs) >= 2
    assert any("6,000" in f["answer"] for f in faqs)
    assert any("eKYC" in f["question"] for f in faqs)

# 8. Non-existent ID Lookup Behavior
def test_direct_lookup_nonexistent_returns_none(repo):
    res = repo.get_scheme_by_id("SCH_NON_EXISTENT")
    assert res is None
    docs = repo.get_documents_for_scheme("SCH_NON_EXISTENT")
    assert docs is None
    faqs = repo.get_faqs_for_scheme("SCH_NON_EXISTENT")
    assert faqs == []
