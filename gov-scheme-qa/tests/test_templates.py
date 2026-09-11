"""
Stage 9 Test Suite: Deterministic Answer Templates.
Verifies all 12 templates:
1. overview
2. benefit
3. document
4. application
5. eligibility pass
6. eligibility fail
7. insufficient data
8. exclusion
9. comparison
10. multi-scheme recommendation
11. FAQ
12. abstention
And explicitly tests that missing variables cause controlled TemplateRenderError.
"""

import sys
import os
import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from templates.answer_templates import (
    render_deterministic_template,
    TemplateRenderError,
    TEMPLATE_REGISTRY
)

# Test 1: Overview template
def test_template_overview():
    ctx = {
        "scheme": {
            "official_name": "One Nation One Ration Card",
            "abbreviation": "ONORC",
            "category": "Food Security",
            "ministry": "Ministry of Consumer Affairs",
            "geographic_scope": "NATIONAL",
            "status": "ACTIVE",
            "objective": "Enable nationwide portability",
            "description": "Ration card portability across India",
            "source_pages": [1, 2]
        }
    }
    rendered = render_deterministic_template("OVERVIEW", ctx)
    assert "One Nation One Ration Card (ONORC)" in rendered
    assert "Ministry of Consumer Affairs" in rendered

# Test 2: Benefit template
def test_template_benefit():
    ctx = {
        "scheme": {"official_name": "PM-SYM", "abbreviation": "PM-SYM", "source_pages": [3]},
        "benefits": [
            {"benefit_type": "PENSION", "description": "Monthly Rs 3000 pension", "quantified_value": "Rs 3000", "coverage": "National", "beneficiary_count": None}
        ]
    }
    rendered = render_deterministic_template("BENEFIT", ctx)
    assert "Benefits of PM-SYM" in rendered
    assert "Monthly Rs 3000 pension" in rendered

# Test 3: Document template
def test_template_document():
    ctx = {
        "scheme": {"official_name": "PM Vishwakarma"},
        "documents": {
            "mandatory": [{"name": "Aadhaar Card", "description": "Biometric proof", "purpose": "KYC"}],
            "optional": [],
            "source_pages": [7]
        }
    }
    rendered = render_deterministic_template("DOCUMENT", ctx)
    assert "Documents Required for PM Vishwakarma" in rendered
    assert "Aadhaar Card" in rendered

# Test 4: Application template
def test_template_application():
    ctx = {
        "scheme": {"official_name": "PM Surya Ghar"},
        "procedure": {
            "mode": "ONLINE",
            "processing_time": "30 days",
            "fees": "Zero",
            "online_steps": ["Register on national portal"],
            "offline_steps": ["Install net meter"],
            "source_pages": [6]
        }
    }
    rendered = render_deterministic_template("APPLICATION", ctx)
    assert "Application Procedure: PM Surya Ghar" in rendered
    assert "Register on national portal" in rendered

# Test 5: Eligibility Pass template
def test_template_eligibility_pass():
    ctx = {
        "result": {
            "scheme_name": "PM-SYM",
            "passed_conditions": [{"description": "Age between 18 and 40", "actual": 25}],
            "citations": ["Page 3"]
        }
    }
    rendered = render_deterministic_template("ELIGIBILITY_PASS", ctx)
    assert "RESULT: ELIGIBLE" in rendered
    assert "Age between 18 and 40" in rendered

# Test 6: Eligibility Fail template
def test_template_eligibility_fail():
    ctx = {
        "result": {
            "scheme_name": "PM-SYM",
            "failed_conditions": [{"description": "Age limit", "actual": 45, "expected": "<= 40"}],
            "citations": ["Page 3"]
        }
    }
    rendered = render_deterministic_template("ELIGIBILITY_FAIL", ctx)
    assert "RESULT: NOT ELIGIBLE" in rendered
    assert "Age limit" in rendered

# Test 7: Insufficient Data template
def test_template_insufficient_data():
    ctx = {
        "result": {
            "scheme_name": "PM-SYM",
            "missing_fields": ["monthly_income", "occupation"],
            "citations": ["Page 3"]
        }
    }
    rendered = render_deterministic_template("INSUFFICIENT_DATA", ctx)
    assert "RESULT: INSUFFICIENT INFORMATION" in rendered
    assert "monthly_income" in rendered

# Test 8: Exclusion template
def test_template_exclusion():
    ctx = {
        "scheme": {"official_name": "PM-KISAN", "source_pages": [5]},
        "exclusions": [
            {"category": "INCOME_TAX", "description": "Paid income tax in last assessment year"}
        ]
    }
    rendered = render_deterministic_template("EXCLUSION", ctx)
    assert "Statutory Exclusions: PM-KISAN" in rendered
    assert "Paid income tax" in rendered

# Test 9: Comparison template
def test_template_comparison():
    ctx = {
        "scheme_a": {"official_name": "PMJJBY", "abbreviation": "PMJJBY", "category": "Insurance", "ministry": "MoF", "geographic_scope": "NATIONAL", "objective": "Life cover", "source_pages": [4]},
        "scheme_b": {"official_name": "PMSBY", "abbreviation": "PMSBY", "category": "Insurance", "ministry": "MoF", "geographic_scope": "NATIONAL", "objective": "Accidental cover", "source_pages": [4]}
    }
    rendered = render_deterministic_template("COMPARISON", ctx)
    assert "Scheme Comparison: PMJJBY vs PMSBY" in rendered
    assert "Life cover" in rendered
    assert "Accidental cover" in rendered

# Test 10: Multi-Scheme Recommendation template
def test_template_multi_scheme():
    ctx = {
        "schemes": [
            {"official_name": "ONORC", "abbreviation": "ONORC", "category": "Food Security", "ministry": "MoCAF&PD"},
            {"official_name": "PM-SYM", "abbreviation": "PM-SYM", "category": "Pension", "ministry": "MoL&E"}
        ]
    }
    rendered = render_deterministic_template("MULTI_SCHEME", ctx)
    assert "Available Schemes (Total: 2)" in rendered
    assert "ONORC" in rendered

# Test 11: FAQ template
def test_template_faq():
    ctx = {
        "scheme": {"official_name": "ONORC", "source_pages": [2]},
        "faqs": [
            {"question": "Can I get ration in Rajasthan?", "answer": "Yes, ONORC allows inter-state lifting."}
        ]
    }
    rendered = render_deterministic_template("FAQ", ctx)
    assert "Frequently Asked Questions: ONORC" in rendered
    assert "Can I get ration in Rajasthan?" in rendered

# Test 12: Abstention template
def test_template_abstention():
    ctx = {"query": "What is the speed of light?"}
    rendered = render_deterministic_template("ABSTENTION", ctx)
    assert "Inquiry Outside Knowledge Base" in rendered
    assert "What is the speed of light?" in rendered

# MANDATORY TEST: Controlled Failure on Missing Template Variables
def test_missing_variable_causes_controlled_failure():
    """Verify that a missing template variable triggers TemplateRenderError and not silent bad output"""
    incomplete_ctx = {
        "scheme": {
            # Missing official_name, category, ministry, objective, etc.
            "status": "ACTIVE"
        }
    }
    with pytest.raises(TemplateRenderError) as exc_info:
        render_deterministic_template("OVERVIEW", incomplete_ctx)

    assert "Controlled Template Failure" in str(exc_info.value)
