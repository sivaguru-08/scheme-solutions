"""
Stage 9: Deterministic Jinja2 Answer Templates.
Strictly non-generative. Every variable originates from:
- database records
- AST rule engine evaluations
- validated search results
Configured with jinja2.StrictUndefined to enforce controlled errors if variables are missing.
"""

import jinja2
from typing import Dict, Any, List

class TemplateRenderError(Exception):
    pass

# Strict Jinja2 environment that raises errors on missing variables
env_strict = jinja2.Environment(
    loader=jinja2.BaseLoader(),
    undefined=jinja2.StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True
)

# 1. OVERVIEW
OVERVIEW_TEMPLATE = """
### {{ scheme.official_name }}{% if scheme.abbreviation %} ({{ scheme.abbreviation }}){% endif %}

**Category:** {{ scheme.category }}
**Ministry:** {{ scheme.ministry }}
**Scope:** {{ scheme.geographic_scope }} | **Status:** {{ scheme.status }}

**Objective:**
{{ scheme.objective }}

**Description:**
{{ scheme.description }}

---
*Source: Statutory Scheme Guidelines (Page {{ scheme.source_pages | join(', ') }})*
"""

# 2. BENEFIT
BENEFIT_TEMPLATE = """
### Benefits of {{ scheme.official_name }}{% if scheme.abbreviation %} ({{ scheme.abbreviation }}){% endif %}

{% for b in benefits %}
{{ loop.index }}. **{{ b.benefit_type | replace('_', ' ') | title }}:**
   - {{ b.description }}
   {% if b.quantified_value %}   - **Financial/Quantified Support:** {{ b.quantified_value }}{% endif %}
   {% if b.coverage %}   - **Coverage / Scope:** {{ b.coverage }}{% endif %}
   {% if b.beneficiary_count %}   - **Beneficiaries:** {{ b.beneficiary_count }}{% endif %}

{% endfor %}
---
*Source: Official Benefit Schedules (Page {{ scheme.source_pages | join(', ') }})*
"""

# 3. DOCUMENT
DOCUMENT_TEMPLATE = """
### Documents Required for {{ scheme.official_name }}

**Mandatory Documents:**
{% for doc in documents.mandatory %}
{{ loop.index }}. **{{ doc.name }}**
   - *Description:* {{ doc.description }}
   - *Purpose:* {{ doc.purpose }}
{% endfor %}

{% if documents.optional %}
**Optional / Additional Documents:**
{% for doc in documents.optional %}
- **{{ doc.name }}** ({{ doc.purpose }})
{% endfor %}
{% endif %}

---
*Source: Official Application Checklist (Page {{ documents.source_pages | join(', ') }})*
"""

# 4. APPLICATION
APPLICATION_TEMPLATE = """
### Application Procedure: {{ scheme.official_name }}

**Mode:** {{ procedure.mode | replace('_', ' ') }}
{% if procedure.processing_time %}
**Timeline:** {{ procedure.processing_time }}
{% endif %}
{% if procedure.fees %}
**Fees:** {{ procedure.fees }}
{% endif %}

{% if procedure.online_steps %}
**Online Steps:**
{% for step in procedure.online_steps %}
{{ loop.index }}. {{ step }}
{% endfor %}
{% endif %}

{% if procedure.offline_steps %}
**Offline Steps:**
{% for step in procedure.offline_steps %}
{{ loop.index }}. {{ step }}
{% endfor %}
{% endif %}

---
*Source: Official Application Procedure (Page {{ procedure.source_pages | join(', ') }})*
"""

# 5. ELIGIBILITY PASS
ELIGIBILITY_PASS_TEMPLATE = """
### Eligibility Evaluation: {{ result.scheme_name }}

✅ **RESULT: ELIGIBLE**
You meet the qualification requirements based on the statutory guidelines.

**Conditions Met:**
{% for p in result.passed_conditions %}
- ✅ {{ p.description }} *(Provided: {{ p.actual }})*
{% endfor %}

---
*Statutory Provenance: {{ result.citations | join(', ') }}*
"""

# 6. ELIGIBILITY FAIL
ELIGIBILITY_FAIL_TEMPLATE = """
### Eligibility Evaluation: {{ result.scheme_name }}

❌ **RESULT: NOT ELIGIBLE**
You do not meet one or more statutory qualification requirements.

**Unmet Requirements / Disqualifications:**
{% for f in result.failed_conditions %}
- ❌ {{ f.description }} *(Provided: {{ f.actual }}, Required: {{ f.expected }})*
{% endfor %}

---
*Statutory Provenance: {{ result.citations | join(', ') }}*
"""

# 7. INSUFFICIENT DATA
INSUFFICIENT_DATA_TEMPLATE = """
### Eligibility Evaluation: {{ result.scheme_name }}

⚠️ **RESULT: INSUFFICIENT INFORMATION**
Cannot conclusively determine eligibility because required profile attributes are missing.

**Missing Mandatory Fields:**
{% for m in result.missing_fields %}
- ⚠️ {{ m }}
{% endfor %}

Please provide these missing details to complete the deterministic eligibility check.

---
*Statutory Provenance: {{ result.citations | join(', ') }}*
"""

# 8. EXCLUSION
EXCLUSION_TEMPLATE = """
### Statutory Exclusions: {{ scheme.official_name }}

The following categories/conditions strictly disqualify an applicant:

{% for ex in exclusions %}
{{ loop.index }}. ❌ **{{ ex.category | replace('_', ' ') | title }}:** {{ ex.description }}
{% endfor %}

---
*Source: Statutory Ineligibility Criteria (Page {{ scheme.source_pages | join(', ') }})*
"""

# 9. COMPARISON
COMPARISON_TEMPLATE = """
### Scheme Comparison: {{ scheme_a.official_name }} vs {{ scheme_b.official_name }}

| Attribute | {{ scheme_a.abbreviation or scheme_a.official_name }} | {{ scheme_b.abbreviation or scheme_b.official_name }} |
|---|---|---|
| **Category** | {{ scheme_a.category }} | {{ scheme_b.category }} |
| **Ministry** | {{ scheme_a.ministry }} | {{ scheme_b.ministry }} |
| **Scope** | {{ scheme_a.geographic_scope }} | {{ scheme_b.geographic_scope }} |
| **Key Objective** | {{ scheme_a.objective }} | {{ scheme_b.objective }} |

*Consult official statutory pages: {{ scheme_a.abbreviation }} (Page {{ scheme_a.source_pages | join(', ') }}) | {{ scheme_b.abbreviation }} (Page {{ scheme_b.source_pages | join(', ') }})*
"""

# 10. MULTI_SCHEME RECOMMENDATION
MULTI_SCHEME_TEMPLATE = """
### Available Schemes (Total: {{ schemes | length }})

{% for s in schemes %}
{{ loop.index }}. **{{ s.official_name }}**{% if s.abbreviation %} ({{ s.abbreviation }}){% endif %}
   - **Category:** {{ s.category }}
   - **Ministry:** {{ s.ministry }}
{% endfor %}

*Select any scheme to view detailed eligibility, benefits, documents, or application procedure.*
"""

# 11. FAQ
FAQ_TEMPLATE = """
### Frequently Asked Questions: {{ scheme.official_name }}

{% for faq in faqs %}
**Q{{ loop.index }}: {{ faq.question }}**
> **Answer:** {{ faq.answer }}

{% endfor %}
---
*Source: Official Scheme FAQs (Page {{ scheme.source_pages | join(', ') }})*
"""

# 12. ABSTENTION
ABSTENTION_TEMPLATE = """
### Inquiry Outside Knowledge Base

I cannot answer "{{ query }}" because it falls outside the official Government of India welfare schemes knowledge base.

The system deterministically answers inquiries regarding:
- Scheme eligibility qualification rules
- Benefits and financial payouts
- Required documents and proofs
- Application and registration processes
- Official ministries and helpline contacts
"""

# Aliases for backward compatibility
BENEFITS_TEMPLATE = BENEFIT_TEMPLATE
DOCUMENTS_TEMPLATE = DOCUMENT_TEMPLATE
PROCEDURE_TEMPLATE = APPLICATION_TEMPLATE
EXCLUSIONS_TEMPLATE = EXCLUSION_TEMPLATE
OUT_OF_SCOPE_TEMPLATE = ABSTENTION_TEMPLATE
LIST_SCHEMES_TEMPLATE = MULTI_SCHEME_TEMPLATE

AUTHORITY_TEMPLATE = """
### Administrative Authorities & Contact Details

**Scheme:** {{ scheme.official_name }}
- **Nodal Ministry:** {{ authority.ministry }}
{% if authority.department %}
- **Department:** {{ authority.department }}
{% endif %}
{% if authority.implementing_agency %}
- **Implementing Agency:** {{ authority.implementing_agency }}
{% endif %}
{% if authority.portal_url %}
- **Official Portal:** [{{ authority.portal_url }}]({{ authority.portal_url }})
{% endif %}
{% if authority.helpline %}
- **Helpline / Toll-Free Number:** {{ authority.helpline }}
{% endif %}
{% if authority.grievance_redressal %}
- **Grievance Redressal:** {{ authority.grievance_redressal }}
{% endif %}

---
*Source: Official Ministry Directory (Page {{ scheme.source_pages | join(', ') }})*
"""

# General eligibility template without personal profile
ELIGIBILITY_TEMPLATE = """
### Eligibility Requirements: {{ scheme.official_name }}

{% if rules %}
**Qualification Criteria:**
{% for r in rules %}
- **{{ r.description }}**
  {% for c in r.conditions %}
  {% if c.conditions is defined and c.conditions %}
    - *Combined Conditions ({{ c.operator }}):*
    {% for sub in c.conditions %}
      - {{ sub.description or sub.field or "Requirement" }}
    {% endfor %}
  {% else %}
    - {{ c.description or c.field or "Requirement" }}
  {% endif %}
  {% endfor %}
{% endfor %}
{% else %}
General eligibility guidelines apply as per statutory norms.
{% endif %}

{% if exclusions %}
**Statutory Exclusions & Disqualifications:**
{% for e in exclusions %}
- ❌ **{{ e.category }}:** {{ e.description }}
{% endfor %}
{% endif %}

---
*Source: Statutory Eligibility Guidelines (Page {{ scheme.source_pages | join(', ') }})*
"""

ELIGIBILITY_EVALUATION_TEMPLATE = """
### Eligibility Evaluation: {{ result.scheme_name }}

{% if result.is_eligible %}
✅ **RESULT: ELIGIBLE**
You meet the qualification requirements based on the information provided.
{% else %}
❌ **RESULT: NOT ELIGIBLE / INCONCLUSIVE**
{% endif %}

**Evaluation Breakdown:**
{% if result.passed_conditions %}
**Conditions Met:**
{% for p in result.passed_conditions %}
- ✅ {{ p.description }} *(Provided: {{ p.actual_value }})*
{% endfor %}
{% endif %}

{% if result.failed_conditions %}
**Conditions Not Met / Disqualifications:**
{% for f in result.failed_conditions %}
- ❌ {{ f.description }} *(Provided: {{ f.actual_value }}, Required: {{ f.required_value }})*
{% endfor %}
{% endif %}

{% if result.missing_information %}
**Missing Information Required for Full Verification:**
{% for m in result.missing_information %}
- ⚠️ {{ m }}
{% endfor %}
{% endif %}

**Detailed Reasons:**
{% for r in result.reasons %}
- {{ r }}
{% endfor %}

---
*Statutory Provenance: {{ result.citations | join(', ') }}*
"""

BM25_FALLBACK_TEMPLATE = """
### Information for "{{ query }}"

Based on the official scheme documentation:

{% for match in matches %}
#### From: {{ match.scheme_name or match.scheme_id }} ({{ match.section }})
{{ match.content }}

*Citations: Page {{ match.source_pages | join(', ') }}*
{% endfor %}
"""

NO_MATCH_TEMPLATE = """Sorry, there are no schemes in the available scheme database that match your requirements based on the information provided."""

MULTI_INTENT_RECOMMENDATION_TEMPLATE = """
### Recommended Schemes for Your Profile (Total: {{ schemes | length }})

{% for item in schemes %}
{{ loop.index }}. **{{ item.scheme.official_name }}**{% if item.scheme.abbreviation %} ({{ item.scheme.abbreviation }}){% endif %}
   - **Category:** {{ item.scheme.category }}
   - **Ministry:** {{ item.scheme.ministry }}
   {% if item.status == "ELIGIBLE" %}   - **Status:** ✅ ELIGIBLE
   {% elif item.status == "POTENTIAL" %}   - **Status:** ⚠️ POTENTIAL MATCH
   {% endif %}
{% if "ELIGIBILITY" in secondary_intents and item.rules %}
   **Eligibility Criteria:**
   {% for r in item.rules %}
   - {{ r.description }}
   {% endfor %}
{% endif %}
{% if "BENEFITS" in secondary_intents and item.benefits %}
   **Key Benefits:**
   {% for b in item.benefits %}
   - {{ b.description }}{% if b.quantified_value %} (*{{ b.quantified_value }}*){% endif %}
   {% endfor %}
{% endif %}
{% if ("DOCUMENTS" in secondary_intents or "DOCUMENT_REQUIREMENTS" in secondary_intents) and item.documents and item.documents.mandatory %}
   **Required Documents:**
   {% for doc in item.documents.mandatory %}
   - {{ doc.name }}: {{ doc.description or doc.purpose }}
   {% endfor %}
{% endif %}

---
{% endfor %}
*Source: Statutory Scheme Guidelines and Official Gazettes*
"""

DYNAMIC_QUESTION_TEMPLATE = """{% if pre_text %}{{ pre_text }}

{% endif %}{{ question }}"""

TEMPLATE_REGISTRY = {
    "OVERVIEW": OVERVIEW_TEMPLATE,
    "BENEFIT": BENEFIT_TEMPLATE,
    "DOCUMENT": DOCUMENT_TEMPLATE,
    "APPLICATION": APPLICATION_TEMPLATE,
    "ELIGIBILITY_PASS": ELIGIBILITY_PASS_TEMPLATE,
    "ELIGIBILITY_FAIL": ELIGIBILITY_FAIL_TEMPLATE,
    "INSUFFICIENT_DATA": INSUFFICIENT_DATA_TEMPLATE,
    "EXCLUSION": EXCLUSION_TEMPLATE,
    "COMPARISON": COMPARISON_TEMPLATE,
    "MULTI_SCHEME": MULTI_SCHEME_TEMPLATE,
    "FAQ": FAQ_TEMPLATE,
    "ABSTENTION": ABSTENTION_TEMPLATE,
    "NO_MATCH": NO_MATCH_TEMPLATE,
    "MULTI_INTENT_REC": MULTI_INTENT_RECOMMENDATION_TEMPLATE,
    "DYNAMIC_QUESTION": DYNAMIC_QUESTION_TEMPLATE
}

# Pre-compile all templates at module load time for microsecond rendering
COMPILED_TEMPLATES = {
    name: env_strict.from_string(raw.strip())
    for name, raw in TEMPLATE_REGISTRY.items()
}


def render_deterministic_template(template_name: str, context: Dict[str, Any]) -> str:
    if template_name not in COMPILED_TEMPLATES:
        raise TemplateRenderError(f"Unknown template: {template_name}")

    compiled_tmpl = COMPILED_TEMPLATES[template_name]
    try:
        return compiled_tmpl.render(**context)
    except jinja2.exceptions.UndefinedError as e:
        raise TemplateRenderError(f"Controlled Template Failure: Missing required variable in {template_name}: {e}")

_CUSTOM_CACHE = {}

def render_template(template_str: str, **kwargs) -> str:
    tmpl = _CUSTOM_CACHE.get(template_str)
    if tmpl is None:
        tmpl = env_strict.from_string(template_str.strip())
        _CUSTOM_CACHE[template_str] = tmpl
    return tmpl.render(**kwargs)
