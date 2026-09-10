import pytest
from store.database import SchemeRepository

@pytest.fixture
def repo():
    return SchemeRepository()

def test_all_schemes_count(repo):
    schemes = repo.get_all_schemes()
    assert len(schemes) == 29
    ids = [s["scheme_id"] for s in schemes]
    assert "SCH_ONORC" in ids
    assert "SCH_PMSYM" in ids
    assert "SCH_PMKISAN" in ids
    assert "SCH_PMSURYA" in ids
    assert "SCH_VISHWA" in ids

def test_scheme_by_id(repo):
    onorc = repo.get_scheme_by_id("SCH_ONORC")
    assert onorc is not None
    assert onorc["official_name"] == "One Nation One Ration Card"
    assert onorc["geographic_scope"] == "NATIONAL"
    assert len(onorc["source_pages"]) > 0

def test_benefits_retrieval(repo):
    benefits = repo.get_benefits_for_scheme("SCH_ONORC")
    assert len(benefits) >= 1
    assert any("Fair Price Shop" in b["description"] for b in benefits)

def test_fts5_bm25_search(repo):
    results = repo.search_bm25("ration card portability")
    assert len(results) > 0
    assert results[0]["scheme_id"] == "SCH_ONORC"
    assert results[0]["score"] < 0  # BM25 scores in SQLite FTS5 are negative (lower is better)

def test_fts5_search_solar(repo):
    results = repo.search_bm25("solar rooftop electricity")
    assert len(results) > 0
    assert results[0]["scheme_id"] == "SCH_PMSURYA"
