import jinja2

OVERVIEW_TEMPLATE = """
### {{ scheme.official_name }}{% if scheme.abbreviation %} ({{ scheme.abbreviation }}){% endif %}

**Category:** {{ scheme.category }}{% if scheme.subcategory %} / {{ scheme.subcategory }}{% endif %}
**Ministry:** {{ scheme.ministry }}{% if scheme.department %} ({{ scheme.department }}){% endif %}
**Scope:** {{ scheme.geographic_scope }} | **Status:** {{ scheme.status }}

**Objective:**
{{ scheme.objective or scheme.description }}

**Overview:**
{{ scheme.description }}

{% if benefits %}
**Key Highlights:**
{% for b in benefits[:3] %}
- {{ b.description }}{% if b.quantified_value %} (*Value: {{ b.quantified_value }}*){% endif %}
{% endfor %}
{% endif %}

---
*Source: Official Scheme Guidelines (Page {{ scheme.source_pages | join(', ') }})*
"""

ELIGIBILITY_TEMPLATE = """
### Eligibility Requirements for {{ scheme.official_name }}

{% if rules %}
**Qualification Criteria:**
{% for r in rules %}
- **{{ r.description }}**
  {% for c in r.conditions %}
  - {{ c.description }} *(Rule: {{ c.field }} {{ c.operator }} {{ c.value }})*
  {% endfor %}
{% endfor %}
{% else %}
General eligibility applies as per scheme norms.
{% endif %}

{% if exclusions %}
**Important Disqualifications & Exclusions:**
{% for e in exclusions %}
- ❌ **{{ e.category }}:** {{ e.description }}
{% endfor %}
{% endif %}

---
*Source: Official Eligibility Guidelines (Page {{ scheme.source_pages | join(', ') }})*
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
*Verified against statutory guidelines (Provenance: {{ result.citations | join(', ') }})*
"""

BENEFITS_TEMPLATE = """
### Benefits of {{ scheme.official_name }}{% if scheme.abbreviation %} ({{ scheme.abbreviation }}){% endif %}

{% if benefits %}
{% for b in benefits %}
{{ loop.index }}. **{{ b.benefit_type | replace('_', ' ') | title }}:**
   - {{ b.description }}
   {% if b.quantified_value %}   - **Financial/Quantified Support:** {{ b.quantified_value }}{% endif %}
   {% if b.coverage %}   - **Coverage / Scope:** {{ b.coverage }}{% endif %}
   {% if b.beneficiary_count %}   - **Beneficiaries:** {{ b.beneficiary_count }}{% endif %}
   {% if b.method %}   - **Delivery Mode:** {{ b.method }}{% endif %}

{% endfor %}
{% else %}
No specific listed benefits found for this scheme.
{% endif %}

---
*Source: Official Benefit Schedules (Page {{ scheme.source_pages | join(', ') }})*
"""

DOCUMENTS_TEMPLATE = """
### Documents Required for {{ scheme.official_name }}

{% if documents %}
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

{% else %}
- Aadhaar Card / Officially Valid Document (OVD)
- Bank Account Passbook
- Category / Income certificate (if applicable)
{% endif %}

---
*Source: Official Application Checklist (Page {{ scheme.source_pages | join(', ') }})*
"""

PROCEDURE_TEMPLATE = """
### Application Process for {{ scheme.official_name }}

**Application Mode:** {{ procedure.mode | replace('_', ' ') }}
{% if procedure.processing_time %}**Standard Timeline:** {{ procedure.processing_time }}{% endif %}
{% if procedure.fees %}**Application Fees:** {{ procedure.fees }}{% endif %}

{% if procedure.online_steps %}
**Online Application Steps:**
{% for step in procedure.online_steps %}
{{ loop.index }}. {{ step }}
{% endfor %}
{% endif %}

{% if procedure.offline_steps %}
**Offline Application Steps:**
{% for step in procedure.offline_steps %}
{{ loop.index }}. {{ step }}
{% endfor %}
{% endif %}

---
*Source: Official Application Procedure (Page {{ scheme.source_pages | join(', ') }})*
"""

EXCLUSIONS_TEMPLATE = """
### Exclusions & Ineligibility: {{ scheme.official_name }}

The following individuals/categories are strictly ineligible to enroll or receive benefits under this scheme:

{% if exclusions %}
{% for e in exclusions %}
{{ loop.index }}. ❌ **{{ e.category | replace('_', ' ') | title }}:**
   {{ e.description }}
{% endfor %}
{% else %}
No specific exclusions recorded beyond general eligibility requirements.
{% endif %}

---
*Source: Official Statutory Exclusion Criteria (Page {{ scheme.source_pages | join(', ') }})*
"""

FAQ_TEMPLATE = """
### Frequently Asked Questions: {{ scheme.official_name }}

{% if faqs %}
{% for f in faqs %}
**Q{{ loop.index }}: {{ f.question }}**
> **Answer:** {{ f.answer }}

{% endfor %}
{% else %}
No specific FAQ entries recorded for this scheme.
{% endif %}

---
*Source: Official Scheme FAQ Section (Page {{ scheme.source_pages | join(', ') }})*
"""

AUTHORITY_TEMPLATE = """
### Administrative Authorities & Contact Details

**Scheme:** {{ scheme.official_name }}
- **Nodal Ministry:** {{ authority.ministry }}
{% if authority.department %}- **Department:** {{ authority.department }}{% endif %}
{% if authority.implementing_agency %}- **Implementing Agency:** {{ authority.implementing_agency }}{% endif %}
{% if authority.portal_url %}- **Official Portal:** [{{ authority.portal_url }}]({{ authority.portal_url }}){% endif %}
{% if authority.helpline %}- **Helpline / Toll-Free Number:** {{ authority.helpline }}{% endif %}
{% if authority.grievance_redressal %}- **Grievance Redressal:** {{ authority.grievance_redressal }}{% endif %}

---
*Source: Official Ministry Directory (Page {{ scheme.source_pages | join(', ') }})*
"""

LIST_SCHEMES_TEMPLATE = """
### Available Government Schemes (Total: {{ schemes | length }})

{% for s in schemes %}
{{ loop.index }}. **{{ s.official_name }}**{% if s.abbreviation %} ({{ s.abbreviation }}){% endif %}
   - *Category:* {{ s.category }}
   - *Ministry:* {{ s.ministry }}
{% endfor %}

*Ask any specific question about benefits, eligibility, required documents, or application process for any scheme listed above.*
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

OUT_OF_SCOPE_TEMPLATE = """
I could not find authoritative information in the official Government of India schemes knowledge base answering your query: "{{ query }}".

Please verify the scheme name or specify whether you are asking about:
- Scheme eligibility or qualification rules
- Benefits and financial assistance amounts
- Required documents and proofs
- Step-by-step application procedure
- Helpline numbers and administrative ministries
"""

env = jinja2.Environment(loader=jinja2.BaseLoader())

def render_template(template_str: str, **kwargs) -> str:
    tmpl = env.from_string(template_str.strip())
    return tmpl.render(**kwargs)
