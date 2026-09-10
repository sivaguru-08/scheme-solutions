import pytest
from models.intent_classifier import LightweightIntentClassifier
from models.entity_extractor import DeterministicEntityExtractor

@pytest.fixture
def classifier():
    return LightweightIntentClassifier()

@pytest.fixture
def extractor():
    return DeterministicEntityExtractor()

def test_intent_benefits(classifier):
    res = classifier.predict("What are the benefits of PM-KISAN?")
    assert res.intent == "BENEFITS"
    assert res.confidence >= 0.7

def test_intent_check_eligibility(classifier):
    res = classifier.predict("Am I eligible for PM-SYM if my age is 30?")
    assert res.intent == "CHECK_ELIGIBILITY"
    assert res.confidence >= 0.7

def test_intent_documents(classifier):
    res = classifier.predict("What documents are required to apply for PM Vishwakarma?")
    assert res.intent == "DOCUMENTS"

def test_intent_procedure(classifier):
    res = classifier.predict("How to apply for PM Surya Ghar scheme?")
    assert res.intent == "PROCEDURE"

def test_intent_exclusions(classifier):
    res = classifier.predict("Who is excluded from PM-KISAN scheme?")
    assert res.intent == "EXCLUSIONS"

def test_intent_authority(classifier):
    res = classifier.predict("Which ministry administers PM SVANidhi and what is the helpline number?")
    assert res.intent == "AUTHORITY"

def test_entity_extractor_slots(extractor):
    slots, demo = extractor.extract_entities("I am 26 years old earning 12000 per month as a daily wager. Am I eligible for PM-SYM?")
    assert "SCH_PMSYM" in slots.scheme_ids
    assert demo.age == 26
    assert demo.monthly_income == 12000.0
    assert demo.is_unorganised_worker is True
