from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

class Condition(BaseModel):
    field: str
    operator: str
    value: Any
    description: Optional[str] = None
    citation: Optional[str] = None

class Rule(BaseModel):
    rule_id: str
    scheme_id: str
    rule_type: str = "QUALIFICATION"  # QUALIFICATION or DISQUALIFICATION
    description: str
    operator: str = "AND"  # AND or OR
    conditions: List[Condition] = []
    source_pages: List[int] = []

class Benefit(BaseModel):
    benefit_id: str
    scheme_id: str
    benefit_type: str
    description: str
    beneficiary_count: Optional[str] = None
    coverage: Optional[str] = None
    quantified_value: Optional[str] = None
    method: Optional[str] = None
    source_pages: List[int] = []

class Exclusion(BaseModel):
    exclusion_id: str
    scheme_id: str
    category: str
    description: str
    rule_condition: Optional[str] = None
    source_pages: List[int] = []

class DocumentItem(BaseModel):
    name: str
    description: Optional[str] = None
    purpose: Optional[str] = None

class DocumentRequirement(BaseModel):
    document_id: str
    scheme_id: str
    mandatory: List[DocumentItem] = []
    optional: List[DocumentItem] = []
    source_pages: List[int] = []

class Procedure(BaseModel):
    procedure_id: str
    scheme_id: str
    mode: str
    online_steps: List[str] = []
    offline_steps: List[str] = []
    processing_time: Optional[str] = None
    fees: Optional[str] = None
    source_pages: List[int] = []

class FAQ(BaseModel):
    faq_id: str
    scheme_id: str
    question: str
    answer: str
    source_pages: List[int] = []

class Authority(BaseModel):
    authority_id: str
    scheme_id: str
    ministry: str
    department: Optional[str] = None
    implementing_agency: Optional[str] = None
    portal_url: Optional[str] = None
    helpline: Optional[str] = None
    grievance_redressal: Optional[str] = None
    source_pages: List[int] = []

class Scheme(BaseModel):
    scheme_id: str
    official_name: str
    abbreviation: Optional[str] = None
    aliases: List[str] = []
    category: str
    subcategory: Optional[str] = None
    entity_type: str = "SCHEME"
    scheme_type: Optional[str] = "CENTRAL_SECTOR"
    objective: Optional[str] = None
    description: str
    ministry: str
    department: Optional[str] = None
    implementing_agency: Optional[str] = None
    geographic_scope: str = "NATIONAL"
    status: str = "ACTIVE"
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None
    version: Optional[str] = "current"
    source_pages: List[int] = []
    source_sections: List[str] = []

class UserDemographics(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None  # MALE, FEMALE, OTHER
    monthly_income: Optional[float] = None
    annual_turnover: Optional[float] = None
    land_holding_hectares: Optional[float] = None
    occupation: Optional[str] = None
    is_unorganised_worker: Optional[bool] = None
    is_income_tax_payer: Optional[bool] = None
    is_epfo_or_esic_member: Optional[bool] = None
    has_ration_card: Optional[bool] = None
    is_aadhaar_seeded: Optional[bool] = None
    has_bank_account: Optional[bool] = None
    has_pucca_house: Optional[bool] = None
    residence_state: Optional[str] = None
    category: Optional[str] = None  # GENERAL, OBC, SC, ST

class ConditionEvaluation(BaseModel):
    field: str
    required_value: Any
    actual_value: Any
    passed: bool
    description: str
    citation: Optional[str] = None

class EligibilityResult(BaseModel):
    scheme_id: str
    scheme_name: str
    is_eligible: bool
    confidence: float
    passed_conditions: List[ConditionEvaluation] = []
    failed_conditions: List[ConditionEvaluation] = []
    missing_information: List[str] = []
    reasons: List[str] = []
    citations: List[str] = []

class IntentResult(BaseModel):
    intent: str
    confidence: float
    all_scores: Optional[Dict[str, float]] = None

class EntitySlots(BaseModel):
    scheme_ids: List[str] = []
    scheme_names: List[str] = []
    age: Optional[int] = None
    income: Optional[float] = None
    occupation: Optional[str] = None
    gender: Optional[str] = None
    category: Optional[str] = None
    document_keywords: List[str] = []

class SourceCitation(BaseModel):
    scheme_id: str
    scheme_name: str
    section: str
    page_numbers: List[int] = []
    snippet: Optional[str] = None

class QueryRequest(BaseModel):
    query: str
    user_context: Optional[UserDemographics] = None
    scheme_filter: Optional[str] = None

class QueryResponse(BaseModel):
    query: str
    intent: str
    intent_confidence: float
    detected_schemes: List[str]
    answer: str
    is_deterministic: bool = True
    retrieval_method: str  # "EXACT_SLOT_DATABASE", "RULE_EVALUATOR", "FTS5_BM25"
    citations: List[SourceCitation] = []
    metadata: Dict[str, Any] = {}
