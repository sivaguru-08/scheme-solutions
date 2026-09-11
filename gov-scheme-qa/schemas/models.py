from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

class Condition(BaseModel):
    field: Optional[str] = None
    operator: str = "=="
    value: Optional[Any] = None
    description: Optional[str] = None
    citation: Optional[str] = None
    conditions: Optional[List["Condition"]] = None

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
    name: Optional[str] = None
    age: Optional[int] = None
    age_category: Optional[str] = None  # ELDERLY, SENIOR, ADULT, YOUTH, CHILD
    gender: Optional[str] = None  # MALE, FEMALE, OTHER
    monthly_income: Optional[float] = None
    annual_turnover: Optional[float] = None
    land_holding_hectares: Optional[float] = None
    occupation: Optional[str] = None
    trade: Optional[str] = None
    employment_status: Optional[str] = None  # EMPLOYED, UNEMPLOYED, SELF_EMPLOYED, etc.
    employment_type: Optional[str] = None    # REGULAR_FULL_TIME_PRIVATE, GOVERNMENT, CONTRACT, etc.
    location: Optional[str] = None           # City/Town/District e.g. "Bangalore"
    is_unorganised_worker: Optional[bool] = None
    is_income_tax_payer: Optional[bool] = None
    is_epfo_or_esic_member: Optional[bool] = None
    is_bpl: Optional[bool] = None
    has_ration_card: Optional[bool] = None
    is_aadhaar_seeded: Optional[bool] = None
    has_bank_account: Optional[bool] = None
    has_pucca_house: Optional[bool] = None
    has_electricity_connection: Optional[bool] = None
    roof_suitable_solar: Optional[bool] = None
    area_type: Optional[str] = None  # RURAL, URBAN
    residence_state: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    country: Optional[str] = "India"
    category: Optional[str] = None  # GENERAL, OBC, SC, ST
    marital_status: Optional[str] = None  # SINGLE, MARRIED, WIDOW
    disability_status: Optional[str] = None
    has_smart_ration_card: Optional[bool] = None
    in_secc_2011_data: Optional[bool] = None
    is_jform_farmer: Optional[bool] = None
    is_small_trader_registered: Optional[bool] = None
    is_small_marginal_farmer: Optional[bool] = None
    is_accredited_journalist: Optional[bool] = None
    is_bocw_registered_worker: Optional[bool] = None

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
    name: Optional[str] = None
    age: Optional[int] = None
    age_category: Optional[str] = None
    income: Optional[float] = None
    occupation: Optional[str] = None
    trade: Optional[str] = None
    employment_status: Optional[str] = None
    employment_type: Optional[str] = None
    location: Optional[str] = None
    gender: Optional[str] = None
    category: Optional[str] = None
    area_type: Optional[str] = None
    residence_state: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    marital_status: Optional[str] = None
    is_bpl: Optional[bool] = None
    has_smart_ration_card: Optional[bool] = None
    document_keywords: List[str] = []
    requested_information: List[str] = []
    is_profile_only: bool = False
    is_ambiguous_scheme: bool = False
    ambiguity_prompt: Optional[str] = None
    is_unknown_scheme: bool = False
    unknown_scheme_name: Optional[str] = None

class SourceCitation(BaseModel):
    scheme_id: str
    scheme_name: str
    section: str
    page_numbers: List[int] = []
    snippet: Optional[str] = None

# -------------------------------------------------------------
# ARCHITECTURAL CAPABILITY UPGRADE MODELS
# -------------------------------------------------------------

class SchemeResultState:
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    POTENTIAL = "POTENTIAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class GlobalOutcome:
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    NO_MATCH = "NO_MATCH"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    ANSWER_PRODUCED = "ANSWER_PRODUCED"
    CLARIFICATION = "CLARIFICATION"
    PROFILE_RECORDED = "PROFILE_RECORDED"

class QueryType:
    SPECIFIC_SCHEME_QUERY = "SPECIFIC_SCHEME_QUERY"
    MULTI_SCHEME_QUERY = "MULTI_SCHEME_QUERY"
    SCHEME_RECOMMENDATION = "SCHEME_RECOMMENDATION"
    SCHEME_COMPARISON = "SCHEME_COMPARISON"
    UNKNOWN_SCHEME = "UNKNOWN_SCHEME"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    PROFILE_STATEMENT = "PROFILE_STATEMENT"
    AMBIGUOUS_SCHEME = "AMBIGUOUS_SCHEME"

class ConversationMachineState:
    NEW_QUERY = "NEW_QUERY"
    FOLLOW_UP = "FOLLOW_UP"
    SLOT_VALUE = "SLOT_VALUE"
    CLARIFICATION = "CLARIFICATION"
    REFERENCE_QUERY = "REFERENCE_QUERY"
    TOPIC_CHANGE = "TOPIC_CHANGE"
    COMPLETED = "COMPLETED"

class MultiIntentResult(BaseModel):
    primary_intent: str
    secondary_intents: List[str] = []
    requested_information: List[str] = []
    query_type: str = "SPECIFIC_SCHEME_QUERY"
    confidence: float = 1.0
    is_follow_up: bool = False
    referenced_ordinal: Optional[int] = None

class ConfidenceScores(BaseModel):
    intent: float = 1.0
    scheme: float = 1.0
    entities: float = 1.0

class QueryRepresentation(BaseModel):
    query_type: str = "SPECIFIC_SCHEME_QUERY"
    primary_intent: str = "OVERVIEW"
    secondary_intents: List[str] = []
    requested_information: List[str] = Field(default_factory=list)
    scheme_id: Optional[str] = None
    candidate_scheme_ids: List[str] = []
    ambiguous_candidates: List[str] = Field(default_factory=list)
    unknown_scheme_name: Optional[str] = None
    is_clarification: bool = False
    is_profile_only: bool = False
    entities: Dict[str, Any] = Field(default_factory=dict)
    user_profile_updates: Dict[str, Any] = Field(default_factory=dict)
    references: List[str] = Field(default_factory=list)
    is_follow_up: bool = False
    pending_slot: Optional[str] = None
    confidence: ConfidenceScores = Field(default_factory=ConfidenceScores)

class ConversationTurn(BaseModel):
    turn_number: int
    user_query: str
    query_type: str = "SPECIFIC_SCHEME_QUERY"
    primary_intent: str = "OVERVIEW"
    secondary_intents: List[str] = []
    requested_information: List[str] = []
    active_scheme_id: Optional[str] = None
    candidate_schemes: List[str] = []
    recommended_schemes: List[str] = []
    pending_question_slot: Optional[str] = None
    system_answer: str = ""
    state_transition: str = "NEW_QUERY"
    timestamp: float = 0.0

class ConversationState(BaseModel):
    conversation_id: str
    turn_number: int = 0
    active_scheme_id: Optional[str] = None
    previous_scheme_id: Optional[str] = None
    active_intent: Optional[str] = None
    primary_intent: Optional[str] = None
    secondary_intents: List[str] = Field(default_factory=list)
    requested_information: List[str] = Field(default_factory=list)
    last_requested_information: List[str] = Field(default_factory=list)
    scheme_context_stack: List[str] = Field(default_factory=list)
    recent_schemes: List[str] = Field(default_factory=list)
    user_profile: Dict[str, Any] = Field(default_factory=dict)
    known_slots: Dict[str, Any] = Field(default_factory=dict)
    missing_slots: List[str] = Field(default_factory=list)
    pending_question: Optional[str] = None
    pending_question_slot: Optional[str] = None
    candidate_schemes: List[str] = Field(default_factory=list)
    last_recommended_schemes: List[str] = Field(default_factory=list)
    last_answer_type: Optional[str] = None
    turn_history: List[ConversationTurn] = Field(default_factory=list)

class SchemeEvaluationItem(BaseModel):
    scheme_id: str
    scheme_name: str
    status: str = "POTENTIAL"  # ELIGIBLE, POTENTIAL, INELIGIBLE, NOT_APPLICABLE
    matched_conditions: List[str] = []
    failed_conditions: List[str] = []
    unknown_conditions: List[str] = []
    missing_slots: List[str] = []
    relevance_score: float = 0.0
    ranking_reasons: List[str] = []

class QueryRequest(BaseModel):
    query: str
    user_context: Optional[UserDemographics] = None
    scheme_filter: Optional[str] = None
    conversation_id: Optional[str] = None

class QueryResponse(BaseModel):
    query: str
    intent: str
    intent_confidence: float
    detected_schemes: List[str]
    answer: str
    is_deterministic: bool = True
    retrieval_method: str  # "EXACT_SLOT_DATABASE", "RULE_EVALUATOR", "FTS5_BM25", "RECOMMENDATION_ENGINE"
    citations: List[SourceCitation] = []
    metadata: Dict[str, Any] = {}
    conversation_id: Optional[str] = None
    turn_number: Optional[int] = None
    secondary_intents: List[str] = []
    requested_information: List[str] = []
    pending_question: Optional[str] = None
    candidate_schemes: List[str] = []
    recommended_schemes: List[str] = []
    global_outcome: Optional[str] = None
    active_scheme_id: Optional[str] = None
    user_demographics: Optional[UserDemographics] = None

