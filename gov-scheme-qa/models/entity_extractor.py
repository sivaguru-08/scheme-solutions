"""
Deterministic Entity & Slot Extraction Engine.
Extracts:
- Schemes (via canonical SchemeResolver with typo tolerance & ambiguity handling)
- Profile demographics (age, income, occupation, trade, employment status/type, location, gender, state, BPL, etc.)
- Form-like structured statements (e.g. 'Name: Rahul SharmaProfession: Senior Civil Engineer...')
- Natural persona statements (e.g. 'I am 32, a civil engineer, working full-time in Bangalore...')
- Requested Information types (e.g. FIRST_LOAN_AMOUNT, LOAN_AMOUNT, AGE_REQUIREMENT, DOCUMENTS, etc.)
- Pending slot values for conversational follow-ups
- Ordinals and reference pronouns
- Profile-only detection (no question asked, just demographic statement)
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from schemas.models import EntitySlots, UserDemographics
from store.database import SchemeRepository
from models.scheme_resolver import SchemeResolver, SchemeResolutionResult

INDIAN_STATES = {
    "andhra pradesh": "Andhra Pradesh", "andhra": "Andhra Pradesh",
    "arunachal pradesh": "Arunachal Pradesh", "arunachal": "Arunachal Pradesh",
    "assam": "Assam", "bihar": "Bihar", "chhattisgarh": "Chhattisgarh",
    "goa": "Goa", "gujarat": "Gujarat", "haryana": "Haryana",
    "himachal pradesh": "Himachal Pradesh", "himachal": "Himachal Pradesh",
    "jharkhand": "Jharkhand", "karnataka": "Karnataka", "kerala": "Kerala",
    "madhya pradesh": "Madhya Pradesh", "mp": "Madhya Pradesh",
    "maharashtra": "Maharashtra", "manipur": "Manipur", "meghalaya": "Meghalaya",
    "mizoram": "Mizoram", "nagaland": "Nagaland", "odisha": "Odisha", "orissa": "Odisha",
    "punjab": "Punjab", "rajasthan": "Rajasthan", "sikkim": "Sikkim",
    "tamil nadu": "Tamil Nadu", "tamilnadu": "Tamil Nadu", "telangana": "Telangana",
    "tripura": "Tripura", "uttar pradesh": "Uttar Pradesh", "up": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand", "uttaranchal": "Uttarakhand",
    "west bengal": "West Bengal", "bengal": "West Bengal",
    "delhi": "Delhi", "jammu and kashmir": "Jammu and Kashmir", "j&k": "Jammu and Kashmir",
    "ladakh": "Ladakh", "puducherry": "Puducherry", "pondicherry": "Puducherry",
    "chandigarh": "Chandigarh"
}

MAJOR_CITIES_MAP = {
    "bangalore": ("Bangalore", "Karnataka"),
    "bengaluru": ("Bengaluru", "Karnataka"),
    "mumbai": ("Mumbai", "Maharashtra"),
    "pune": ("Pune", "Maharashtra"),
    "chennai": ("Chennai", "Tamil Nadu"),
    "hyderabad": ("Hyderabad", "Telangana"),
    "kolkata": ("Kolkata", "West Bengal"),
    "delhi": ("Delhi", "Delhi"),
    "new delhi": ("New Delhi", "Delhi"),
    "ahmedabad": ("Ahmedabad", "Gujarat"),
    "jaipur": ("Jaipur", "Rajasthan"),
    "lucknow": ("Lucknow", "Uttar Pradesh"),
    "chandigarh": ("Chandigarh", "Punjab"),
    "patna": ("Patna", "Bihar"),
    "bhopal": ("Bhopal", "Madhya Pradesh"),
    "kochi": ("Kochi", "Kerala"),
    "thiruvananthapuram": ("Thiruvananthapuram", "Kerala"),
    "coimbatore": ("Coimbatore", "Tamil Nadu")
}

class DeterministicEntityExtractor:
    def __init__(self, repo: Optional[SchemeRepository] = None):
        self.repo = repo or SchemeRepository()
        self.scheme_resolver = SchemeResolver(self.repo)

    def extract_entities(self, query: str) -> Tuple[EntitySlots, UserDemographics]:
        q_raw = query.strip()
        q_lower = q_raw.lower()
        q_lower = re.sub(r'\bfro\b', 'for', q_lower)
        q_lower = re.sub(r'\beligiblity\b', 'eligibility', q_lower)
        q_lower = re.sub(r'\bdocumenta\b', 'documents', q_lower)
        q_lower = re.sub(r'\bform\s+(?:that|the|this|a)\s+state\b', 'from that state', q_lower)

        # 1. Scheme Resolution via Canonical SchemeResolver
        res_scheme: SchemeResolutionResult = self.scheme_resolver.resolve(query)
        matched_schemes = res_scheme.matched_scheme_ids
        matched_names = res_scheme.matched_scheme_names
        is_ambiguous_scheme = res_scheme.is_ambiguous
        ambiguity_prompt = res_scheme.ambiguity_prompt
        is_unknown_scheme = res_scheme.is_unknown_scheme
        unknown_scheme_name = res_scheme.unknown_scheme_name

        # 2. Extract Personal Name (Ensuring Human Names are never confused with Schemes)
        name_val = None
        # Form field Name: ...
        m_name = re.search(r'\b(?:name|my\s*name\s*is)\s*:\s*([A-Za-z\s]+?)(?:profession|occupation|age|employment|salary|income|status|location|\.|\n|$)', q_raw, re.IGNORECASE)
        if m_name:
            name_val = m_name.group(1).strip()
        else:
            # "I'm Rahul" or "My name is Rahul Sharma"
            m_pname = re.search(r'\b(?:my\s*name\s*is|i(?:\'m|\s*am))\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', q_raw)
            if m_pname:
                cand = m_pname.group(1).strip()
                if cand.lower() not in ["an", "a", "old", "poor", "not", "living", "working", "aged"]:
                    name_val = cand

        # 3. Extract Profession / Occupation / Job / Trade
        occupation = None
        trade = None
        employment_status = None
        employment_type = None

        # Form field Profession: ... or Occupation: ...
        m_prof = re.search(r'\b(?:profession|occupation|job|trade)\s*:\s*([A-Za-z\s]+?)(?:age|employment|salary|income|status|location|\.|\n|$)', q_raw, re.IGNORECASE)
        if m_prof:
            occupation = m_prof.group(1).strip()

        # Form field Employment Status: ...
        m_emp = re.search(r'\b(?:employment\s*status|employment\s*type|employment)\s*:\s*([^.\n]+?)(?:monthly|salary|income|location|\.|\n|$)', q_raw, re.IGNORECASE)
        if m_emp:
            raw_emp = m_emp.group(1).strip()
            employment_type = raw_emp
            emp_lower = raw_emp.lower()
            if any(w in emp_lower for w in ["employee", "regular", "full-time", "working", "salaried"]):
                employment_status = "EMPLOYED"
                if "private" in emp_lower and "full-time" in emp_lower:
                    employment_type = "REGULAR_FULL_TIME_PRIVATE"
            elif "unemployed" in emp_lower:
                employment_status = "UNEMPLOYED"
            elif "self-employed" in emp_lower or "freelance" in emp_lower:
                employment_status = "SELF_EMPLOYED"

        # Artisan trades
        trades = {
            "carpenter": "CARPENTER",
            "blacksmith": "BLACKSMITH",
            "potter": "POTTER",
            "sculptor": "SCULPTOR_STONE_CARVER",
            "cobbler": "COBBLER",
            "mason": "MASON",
            "barber": "BARBER",
            "tailor": "TAILOR",
            "washerman": "WASHERMAN",
            "boat maker": "BOAT_MAKER",
            "armourer": "ARMOURER",
            "locksmith": "LOCKSMITH",
            "goldsmith": "GOLDSMITH",
            "hammer maker": "HAMMER_AND_TOOL_KIT_MAKER",
            "garland maker": "GARLAND_MAKER",
            "toy maker": "DOLL_AND_TOY_MAKER",
            "fishing net maker": "FISHING_NET_MAKER",
            "coir weaver": "BASKET_MAT_BROOM_MAKER_COIR_WEAVER"
        }
        for tr_name, tr_enum in trades.items():
            if tr_name in q_lower:
                trade = tr_enum
                if not occupation:
                    occupation = "ARTISAN"
                break

        is_unorganised = None
        if not occupation:
            if re.search(r'\b(?:senior\s*civil\s*engineer|civil\s*engineer|software\s*engineer|engineer)\b', q_lower):
                m_eng = re.search(r'\b(senior\s*civil\s*engineer|civil\s*engineer|software\s*engineer|engineer)\b', q_lower)
                occupation = m_eng.group(1).title()
            elif re.search(r'\b(?:doctor|physician|surgeon)\b', q_lower):
                occupation = "DOCTOR"
            elif re.search(r'\b(?:teacher|professor|lecturer)\b', q_lower):
                occupation = "TEACHER"
            elif re.search(r'\b(?:farmer|kisan|cultivator|agriculture)\b', q_lower):
                occupation = "FARMER"
            elif re.search(r'\b(?:street vendor|hawker|vendor|rehri|thela)\b', q_lower):
                occupation = "STREET_VENDOR"
            elif re.search(r'\b(?:trader|shopkeeper|retailer|small business)\b', q_lower):
                occupation = "TRADER"
            elif re.search(r'\b(?:artisan|craftsperson)\b', q_lower):
                occupation = "ARTISAN"
            elif re.search(r'\b(?:construction worker|building worker|labourer|laborer|unorganised worker|migrant worker|gig worker|platform worker|driver)\b', q_lower):
                occupation = "UNORGANISED_WORKER"
                is_unorganised = True

        # Check general employment phrasing in natural sentences
        if not employment_status:
            if re.search(r'\b(?:working\s*full[\s-]*time|full[\s-]*time\s*employee|regular\s*employee|salaried)\b', q_lower):
                employment_status = "EMPLOYED"
                if not employment_type:
                    employment_type = "REGULAR_FULL_TIME_PRIVATE" if "private" in q_lower else "REGULAR_FULL_TIME"
            elif re.search(r'\b(?:i(?:\'m|\s*am)\s*working|working|employed|have\s*a\s*job)\b', q_lower):
                employment_status = "EMPLOYED"
                # Do NOT set occupation to "working"! Occupation remains None if not specified!

        if "unorganised" in q_lower or "informal sector" in q_lower or "daily wager" in q_lower:
            is_unorganised = True

        # 4. Extract Age & Age Category
        age = None
        age_category = None
        gender = None

        # Form field Age: ...
        m_age = re.search(r'\bage\s*:\s*(\d{1,2})\b', q_raw, re.IGNORECASE)
        if m_age:
            age = int(m_age.group(1))

        if age is None:
            age_patterns = [
                r'(\d{1,2})[\s-]*(?:years?|yrs?)[\s-]*old\b',
                r'aged\s*(\d{1,2})\b',
                r'age\s*(?:is|of|:)?\s*(\d{1,2})\b',
                r'i\s*am\s*(\d{1,2})\b',
                r'i\'?m\s*(\d{1,2})\b',
                r'\b(\d{1,2})\s*years?\b'
            ]
            for p in age_patterns:
                m = re.search(p, q_lower)
                if m:
                    val = int(m.group(1))
                    if 1 <= val <= 110:
                        age = val
                        break

        # Check age categories
        if age is not None:
            if age >= 60:
                age_category = "ELDERLY"
            elif age < 18:
                age_category = "CHILD"
            elif age <= 35:
                age_category = "YOUTH"
        else:
            if re.search(r'\b(?:old\s*person|elderly|senior\s*citizen|aged(?:\s*person)?|retired)\b', q_lower) or re.search(r'\bi\'?m\s*old\b', q_lower) or re.search(r'\bold\s+man\b', q_lower):
                age_category = "ELDERLY"
            elif re.search(r'\b(?:girl\s*child|little\s*girl)\b', q_lower):
                age_category = "CHILD"
                gender = "FEMALE"
            elif re.search(r'\b(?:youth|young\s*person|student)\b', q_lower):
                age_category = "YOUTH"

        # 5. Extract Income / Monthly Salary / Turnover
        income = None
        turnover = None

        # Form field Monthly Salary: ... or Monthly Income: ...
        m_sal = re.search(r'\b(?:monthly\s*salary|monthly\s*income|salary|monthly\s*earning)\s*:\s*(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d+)?)\s*(?:thousand|k|lakhs?)?', q_raw, re.IGNORECASE)
        if m_sal:
            raw_s = m_sal.group(1).replace(",", "").strip()
            try:
                income = float(raw_s)
                if "thousand" in m_sal.group(0).lower():
                    income *= 1000
                elif "lakh" in m_sal.group(0).lower():
                    income *= 100000
            except ValueError:
                pass

        if income is None:
            # Check Lakhs
            lakh_match = re.search(r'(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?)\s*(?:lakhs?|lac|lacs?|l)\b', q_lower)
            if lakh_match:
                lakh_val = float(lakh_match.group(1)) * 100000
                if "turnover" in q_lower or "annual" in q_lower or "per annum" in q_lower or "per year" in q_lower:
                    turnover = lakh_val
                else:
                    income = lakh_val

            # Check standard income patterns
            if income is None:
                k_match = re.search(r'(?:income|salary|earn|earning|monthly)?\s*(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?)\s*k\b', q_lower)
                if k_match:
                    income = float(k_match.group(1)) * 1000
                else:
                    income_match = re.search(r'(?:income|salary|earn|earning|monthly|earns?|earning)\s*(?:of|is|:)?\s*(?:rs\.?|inr|₹)?\s*([\d,]+)\s*(?:thousand)?', q_lower)
                    if income_match:
                        raw_val = income_match.group(1).replace(",", "")
                        try:
                            income = float(raw_val)
                            if "thousand" in income_match.group(0):
                                income *= 1000
                        except ValueError:
                            pass

        # 6. Extract Location & State
        location = None
        residence_state = None

        # Check Indian States (explicit native / home state overrides workplace city)
        for st_key, st_name in sorted(INDIAN_STATES.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(r'\b(?:native|home|from|residence|domicile)\s*(?:is|of|:)?\s*' + re.escape(st_key) + r'\b', q_lower):
                residence_state = st_name
                break

        # Check major cities
        for city_key, (city_name, st_name) in MAJOR_CITIES_MAP.items():
            if re.search(r'\b' + re.escape(city_key) + r'\b', q_lower):
                location = city_name
                if not residence_state:
                    residence_state = st_name
                break

        # Check Indian States fallback
        if not residence_state:
            for st_key, st_name in sorted(INDIAN_STATES.items(), key=lambda x: len(x[0]), reverse=True):
                if re.search(r'\b' + re.escape(st_key) + r'\b', q_lower):
                    residence_state = st_name
                    break

        # 7. Extract Land holding
        land = None
        land_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:hectares?|ha|acres?)', q_lower)
        if land_match:
            land = float(land_match.group(1))
            if "acre" in land_match.group(0):
                land = land * 0.404686

        # 8. Extract Tax & Social Security
        is_tax_payer = None
        if "pay income tax" in q_lower or "file itr" in q_lower or "tax payer" in q_lower:
            is_tax_payer = True
        elif "do not pay tax" in q_lower or "non-taxpayer" in q_lower or "no income tax" in q_lower:
            is_tax_payer = False

        is_epfo_esic = None
        if "epfo" in q_lower or "esic" in q_lower or "provident fund" in q_lower or "nps" in q_lower:
            if "no epfo" in q_lower or "without epfo" in q_lower or "not covered by epfo" in q_lower:
                is_epfo_esic = False
            else:
                is_epfo_esic = True

        # 9. Extract BPL & Area Type
        is_bpl = None
        if re.search(r'\b(?:bpl|below\s*poverty\s*line|poor\s*family|poor\s*household|antyodaya)\b', q_lower):
            is_bpl = True
        elif re.search(r'\b(?:apl|above\s*poverty\s*line|non-bpl)\b', q_lower):
            is_bpl = False

        area_type = None
        if re.search(r'\b(?:rural|village|gramin|panchayat)\b', q_lower):
            area_type = "RURAL"
        elif re.search(r'\b(?:urban|city|shehri|town|municipality)\b', q_lower):
            area_type = "URBAN"

        # 10. Extract Gender & Marital Status
        marital_status = None
        if re.search(r'\b(?:widow|widowed|vidhwa)\b', q_lower):
            marital_status = "WIDOW"
            if not gender:
                gender = "FEMALE"
        elif re.search(r'\b(?:widower)\b', q_lower):
            marital_status = "WIDOWER"
            if not gender:
                gender = "MALE"
        elif re.search(r'\b(?:married)\b', q_lower):
            marital_status = "MARRIED"
        elif re.search(r'\b(?:unmarried|single)\b', q_lower):
            marital_status = "SINGLE"

        if not gender:
            if re.search(r'\b(?:female|woman|women|girl|mother|daughter|lady)\b', q_lower):
                gender = "FEMALE"
            elif re.search(r'\b(?:male|man|men|boy|son|father)\b', q_lower):
                gender = "MALE"

        # 11. Institutional flags
        has_smart_ration_card = True if "smart ration card" in q_lower else None
        has_ration_card = True if ("ration card" in q_lower or has_smart_ration_card) else None
        in_secc_2011 = True if "secc" in q_lower else None
        is_jform = True if ("j-form" in q_lower or "j form" in q_lower) else None
        is_bocw = True if "bocw" in q_lower else None
        is_journalist = True if "journalist" in q_lower else None
        is_aadhaar_seeded = True if ("aadhaar" in q_lower and ("seed" in q_lower or "link" in q_lower)) else None

        # 12. Requested Information Extraction
        requested_info: List[str] = []
        if re.search(r'\b(?:first\s+(?:[a-z0-9\s-]+\s+)?loan|first\s*loan\s*amount|initial\s*loan|tranche\s*1\s*loan|first\s*tranche)\b', q_lower):
            requested_info.append("FIRST_LOAN_AMOUNT")
            requested_info.append("LOAN_AMOUNT")
            requested_info.append("BENEFIT")
        elif re.search(r'\b(?:how\s*much\s*loan|loan\s*amount|loan\s*provided|how\s*much\s*does\s*it\s*lend|borrow|credit\s*limit)\b', q_lower):
            requested_info.append("LOAN_AMOUNT")
            requested_info.append("BENEFIT")

        if re.search(r'\b(?:how\s*old|age\s*limit|maximum\s*age|minimum\s*age|what\s*age|age\s*requirement|age\s*criteria|entry\s*age)\b', q_lower):
            requested_info.append("AGE_REQUIREMENT")
            requested_info.append("ELIGIBILITY")

        if re.search(r'\b(?:income\s*limit|salary\s*limit|maximum\s*income|income\s*criteria)\b', q_lower):
            requested_info.append("INCOME_REQUIREMENT")
            requested_info.append("ELIGIBILITY")

        if re.search(r'\b(?:subsidy|how\s*much\s*subsidy|interest\s*subsidy)\b', q_lower):
            requested_info.append("SUBSIDY")
            requested_info.append("BENEFIT")

        if re.search(r'\b(?:pension\s*amount|how\s*much\s*pension|monthly\s*pension)\b', q_lower):
            requested_info.append("PENSION_AMOUNT")
            requested_info.append("BENEFIT")

        if re.search(r'\b(?:insurance\s*cover|how\s*much\s*coverage|sum\s*assured|accidental\s*cover|life\s*cover)\b', q_lower):
            requested_info.append("INSURANCE_COVER")
            requested_info.append("BENEFIT")

        if re.search(r'\b(?:documents?|papers?|proofs?|certificates?|what\s*documents|required\s*documents)\b', q_lower):
            requested_info.append("DOCUMENTS")

        if re.search(r'\b(?:how\s*do\s*i\s*apply|how\s*to\s*apply|where\s*to\s*apply|application\s*process|steps\s*to\s*apply|can\s*i\s*apply\s*online|how\s*can\s*i\s*register|registration\s*process)\b', q_lower):
            requested_info.append("APPLICATION_STEPS")

        if re.search(r'\b(?:helpline|toll[\s-]*free|contact\s*number|phone\s*number|call\s*center|grievance|complaint\s*number)\b', q_lower):
            requested_info.append("HELPLINE")
            requested_info.append("AUTHORITY")

        if re.search(r'\b(?:who\s*can\s*apply|who\s*is\s*eligible|am\s*i\s*eligible|can\s*i\s*apply|eligibility\s*criteria|do\s*i\s*qualify|would\s*i\s*qualify|requirements)\b', q_lower):
            if "ELIGIBILITY" not in requested_info:
                requested_info.append("ELIGIBILITY")

        if re.search(r'\b(?:what\s*do\s*i\s*get|how\s*much\s*will\s*i\s*get|what\s*benefits?|financial\s*assistance|how\s*much\s*does\s+.*?provide|how\s*much\s*does\s*it\s*provide)\b', q_lower):
            if "BENEFIT" not in requested_info:
                requested_info.append("BENEFIT")

        if re.search(r'\b(?:what\s*is|tell\s*me\s*about|explain|give\s*me\s*information|how\s*does\s*it\s*work)\b', q_lower):
            if not requested_info:
                requested_info.append("SCHEME_OVERVIEW")

        # 13. Profile-Only Detection
        # If query provides demographic fields but contains no question words, scheme mentions, or request keywords
        has_profile_fields = any([
            name_val, age is not None, occupation, trade, employment_status,
            income is not None, location, residence_state, gender, marital_status
        ])
        question_indicators = [
            r'\?',  # Explicit question mark
            r'\b(?:what|which|how|can\s*i|am\s*i|do\s*i|could\s*i|tell\s*me|explain|give\s*me)\b',
            r'\b(?:eligible|eligibility|apply|qualify|get|benefit|pension|loan|scheme|document|help|assist)\b'
        ]
        has_question = any(re.search(p, q_lower) for p in question_indicators)
        is_profile_only = has_profile_fields and not has_question and not matched_schemes

        # Document keywords
        doc_keywords = []
        for kw in ["aadhaar", "ration card", "bank passbook", "pan card", "land record", "electricity bill", "voter id"]:
            if kw in q_lower:
                doc_keywords.append(kw)

        slots = EntitySlots(
            scheme_ids=matched_schemes,
            scheme_names=matched_names,
            name=name_val,
            age=age,
            age_category=age_category,
            income=income,
            occupation=occupation,
            trade=trade,
            employment_status=employment_status,
            employment_type=employment_type,
            location=location,
            gender=gender,
            area_type=area_type,
            residence_state=residence_state,
            state=residence_state,
            marital_status=marital_status,
            is_bpl=is_bpl,
            has_smart_ration_card=has_smart_ration_card,
            document_keywords=doc_keywords,
            requested_information=requested_info,
            is_profile_only=is_profile_only,
            is_ambiguous_scheme=is_ambiguous_scheme,
            ambiguity_prompt=ambiguity_prompt,
            is_unknown_scheme=is_unknown_scheme,
            unknown_scheme_name=unknown_scheme_name
        )

        demographics = UserDemographics(
            name=name_val,
            age=age,
            age_category=age_category,
            gender=gender,
            monthly_income=income,
            annual_turnover=turnover,
            land_holding_hectares=land,
            occupation=occupation,
            trade=trade,
            employment_status=employment_status,
            employment_type=employment_type,
            location=location,
            is_unorganised_worker=is_unorganised,
            is_income_tax_payer=is_tax_payer,
            is_epfo_or_esic_member=is_epfo_esic,
            is_bpl=is_bpl,
            has_ration_card=has_ration_card,
            has_smart_ration_card=has_smart_ration_card,
            in_secc_2011_data=in_secc_2011,
            is_jform_farmer=is_jform,
            is_bocw_registered_worker=is_bocw,
            is_accredited_journalist=is_journalist,
            is_aadhaar_seeded=is_aadhaar_seeded,
            area_type=area_type,
            residence_state=residence_state,
            state=residence_state,
            marital_status=marital_status
        )

        return slots, demographics

    def extract_pending_slot_value(self, query: str, pending_slot: str) -> Tuple[bool, Any]:
        """
        Extracts a slot value from short conversational responses (e.g. '68', 'yes', 'rural', 'im working')
        given a known pending slot.
        """
        q_clean = query.strip().lower()

        # Slot: age / exact_age
        if pending_slot in ["age", "exact_age", "demographic.age"]:
            m = re.search(r'^(?:i(?:\'m|\s*am)\s*)?(\d{1,3})\s*(?:years?(?:\s*old)?|yrs?)?\.?$', q_clean)
            if m:
                val = int(m.group(1))
                if 1 <= val <= 110:
                    return True, val
            m_num = re.search(r'\b(\d{1,3})\b', q_clean)
            if m_num:
                val = int(m_num.group(1))
                if 1 <= val <= 110:
                    return True, val

        # Boolean slots: is_bpl, is_unorganised_worker, is_income_tax_payer, has_ration_card, etc.
        boolean_slots = [
            "is_bpl", "economic.is_bpl",
            "is_unorganised_worker", "occupational.is_unorganised_worker",
            "is_income_tax_payer", "economic.is_income_tax_payer",
            "is_epfo_or_esic_member", "institutional.covered_by_epfo",
            "has_ration_card", "institutional.has_ration_card",
            "has_bank_account", "institutional.has_bank_account"
        ]
        if pending_slot in boolean_slots:
            if re.search(r'^(?:yes|yep|yeah|true|i do|i have|we have|correct)\b', q_clean):
                return True, True
            elif re.search(r'^(?:no|nope|false|i do not|i don\'t|do not have|negative)\b', q_clean):
                return True, False

        # Slot: residence_state / state
        if pending_slot in ["residence_state", "state", "geographic.state"]:
            # Check city
            for city_key, (_, st_name) in MAJOR_CITIES_MAP.items():
                if re.search(r'\b' + re.escape(city_key) + r'\b', q_clean):
                    return True, st_name
            # Check state
            for st_key, st_name in sorted(INDIAN_STATES.items(), key=lambda x: len(x[0]), reverse=True):
                if re.search(r'\b' + re.escape(st_key) + r'\b', q_clean):
                    return True, st_name

        # Slot: gender
        if pending_slot in ["gender", "demographic.gender"]:
            if re.search(r'\b(?:male|man|boy)\b', q_clean):
                return True, "MALE"
            elif re.search(r'\b(?:female|woman|girl|widow)\b', q_clean):
                return True, "FEMALE"

        # Slot: marital_status
        if pending_slot in ["marital_status", "demographic.marital_status"]:
            if re.search(r'\b(?:widow|widowed|vidhwa)\b', q_clean):
                return True, "WIDOW"
            elif re.search(r'\b(?:married)\b', q_clean):
                return True, "MARRIED"
            elif re.search(r'\b(?:single|unmarried)\b', q_clean):
                return True, "SINGLE"

        # Slot: area_type
        if pending_slot in ["area_type", "geographic.area_type"]:
            if re.search(r'\b(?:rural|village|gramin|panchayat)\b', q_clean):
                return True, "RURAL"
            if re.search(r'\b(?:urban|city|shehri|town)\b', q_clean):
                return True, "URBAN"

        # Slot: monthly_income
        if pending_slot in ["monthly_income", "economic.monthly_income_inr", "income"]:
            m_k = re.search(r'(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?)\s*k\b', q_clean)
            if m_k:
                return True, float(m_k.group(1)) * 1000
            m_num = re.search(r'(?:rs\.?|inr|₹)?\s*(\d+[\d,]*)\b', q_clean)
            if m_num:
                return True, float(m_num.group(1).replace(",", ""))

        # Slot: trade / occupation
        if pending_slot in ["trade", "occupational.artisan_trade", "occupation", "occupational.occupation_type"]:
            # Rule 8: If user responds "im working", do NOT set occupation="working"!
            if re.search(r'^(?:i(?:\'m|\s*am)\s*working|im\s*working|working|employed|have\s*a\s*job)\.?$', q_clean):
                return True, {"employment_status": "EMPLOYED", "occupation": None}

            for tr_name, tr_enum in [
                ("carpenter", "CARPENTER"), ("blacksmith", "BLACKSMITH"),
                ("potter", "POTTER"), ("sculptor", "SCULPTOR_STONE_CARVER"),
                ("cobbler", "COBBLER"), ("mason", "MASON"), ("barber", "BARBER"),
                ("tailor", "TAILOR"), ("washerman", "WASHERMAN"),
                ("farmer", "FARMER"), ("street vendor", "STREET_VENDOR"),
                ("trader", "TRADER"), ("construction worker", "CONSTRUCTION_WORKER")
            ]:
                if tr_name in q_clean:
                    return True, tr_enum

            # Generic profession string (e.g. "civil engineer", "teacher", etc.)
            if len(q_clean) >= 3 and not re.search(r'\b(?:what|how|why|when|is|are)\b', q_clean):
                return True, q_clean.title()

        return False, None

    def extract_references(self, query: str) -> Dict[str, Any]:
        """
        Extracts ordinal, textual references, and follow-up intentions.
        """
        q_lower = query.lower()
        res = {
            "ordinal": None,
            "refers_to_active": False,
            "refers_to_first": False,
            "refers_to_second": False,
            "refers_to_previous": False,
            "is_procedure_request": False,
            "is_documents_request": False,
            "is_benefits_request": False,
            "is_eligibility_request": False
        }

        # Ordinal checks
        if re.search(r'\b(?:first|1st)\s*(?:one|scheme)?\b', q_lower) or "go back to the first" in q_lower or "benefit of the first scheme" in q_lower:
            res["ordinal"] = 1
            res["refers_to_first"] = True
        elif re.search(r'\b(?:second|2nd)\s*(?:one|scheme)?\b', q_lower):
            res["ordinal"] = 2
            res["refers_to_second"] = True
        elif re.search(r'\b(?:third|3rd)\s*(?:one|scheme)?\b', q_lower):
            res["ordinal"] = 3
        elif re.search(r'\b(?:fourth|4th)\s*(?:one|scheme)?\b', q_lower):
            res["ordinal"] = 4

        if re.search(r'\b(?:previous\s*scheme|the\s*other\s*scheme)\b', q_lower):
            res["refers_to_previous"] = True

        # Pronoun checks
        if re.search(r'\b(?:this\s*scheme|that\s*scheme|the\s*scheme|it)\b', q_lower):
            res["refers_to_active"] = True

        # Follow-up intent checks
        if re.search(r'\b(?:how\s*do\s*i\s*apply|how\s*to\s*apply|application\s*process|procedure|steps\s*to\s*apply)\b', q_lower):
            res["is_procedure_request"] = True
        if re.search(r'\b(?:documents?|papers?|proofs?)\b', q_lower):
            res["is_documents_request"] = True
        if re.search(r'\b(?:benefits?|payout|financial\s*assistance|loan\s*amount|how\s*much\s*loan)\b', q_lower):
            res["is_benefits_request"] = True
        if re.search(r'\b(?:eligibility|criteria|qualify|eligible|who\s*can\s*apply)\b', q_lower):
            res["is_eligibility_request"] = True

        return res
