import pytest
from schemas.models import UserDemographics
from engine.rule_evaluator import DeterministicRuleEvaluator
from store.database import SchemeRepository

@pytest.fixture
def evaluator():
    return DeterministicRuleEvaluator()

def test_pmsym_eligible(evaluator):
    profile = UserDemographics(
        age=25,
        monthly_income=12000,
        is_unorganised_worker=True,
        is_income_tax_payer=False,
        is_epfo_or_esic_member=False
    )
    result = evaluator.evaluate_scheme("SCH_PMSYM", profile)
    assert result.is_eligible is True
    assert len(result.failed_conditions) == 0
    assert len(result.passed_conditions) >= 3
    assert result.confidence == 1.0

def test_pmsym_disqualified_income(evaluator):
    profile = UserDemographics(
        age=25,
        monthly_income=25000,  # exceeds 15,000 limit
        is_unorganised_worker=True,
        is_income_tax_payer=False,
        is_epfo_or_esic_member=False
    )
    result = evaluator.evaluate_scheme("SCH_PMSYM", profile)
    assert result.is_eligible is False
    assert any("monthly_income" in f.field for f in result.failed_conditions)

def test_pmsym_disqualified_age_too_high(evaluator):
    profile = UserDemographics(
        age=45,  # exceeds max 40
        monthly_income=10000,
        is_unorganised_worker=True,
        is_income_tax_payer=False,
        is_epfo_or_esic_member=False
    )
    result = evaluator.evaluate_scheme("SCH_PMSYM", profile)
    assert result.is_eligible is False
    assert any("age" in f.field for f in result.failed_conditions)

def test_pmsym_disqualified_taxpayer(evaluator):
    profile = UserDemographics(
        age=28,
        monthly_income=14000,
        is_unorganised_worker=True,
        is_income_tax_payer=True,  # Taxpayer excluded
        is_epfo_or_esic_member=False
    )
    result = evaluator.evaluate_scheme("SCH_PMSYM", profile)
    assert result.is_eligible is False
    assert any("tax" in f.field for f in result.failed_conditions)

def test_pmsym_disqualified_epfo(evaluator):
    profile = UserDemographics(
        age=28,
        monthly_income=14000,
        is_unorganised_worker=True,
        is_income_tax_payer=False,
        is_epfo_or_esic_member=True  # EPFO excluded
    )
    result = evaluator.evaluate_scheme("SCH_PMSYM", profile)
    assert result.is_eligible is False
    assert any("epfo" in f.field or "esic" in f.field for f in result.failed_conditions)

def test_missing_info_returns_inconclusive(evaluator):
    # Only age given, income and unorganised worker missing
    profile = UserDemographics(age=28)
    result = evaluator.evaluate_scheme("SCH_PMSYM", profile)
    assert result.is_eligible is False
    assert len(result.missing_information) > 0
