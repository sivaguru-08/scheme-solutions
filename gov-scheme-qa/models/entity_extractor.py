import re
from typing import List, Dict, Any, Optional, Tuple
from schemas.models import EntitySlots, UserDemographics
from store.database import SchemeRepository

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

class DeterministicEntityExtractor:
    def __init__(self, repo: Optional[SchemeRepository] = None):
        self.repo = repo or SchemeRepository()
        self.schemes = self.repo.get_all_schemes()
        self._build_alias_index()

    def _build_alias_index(self):
        self.alias_map: Dict[str, str] = {}
        # Map abbreviations, names, and aliases
        for s in self.schemes:
            sid = s["scheme_id"]
            name = s["official_name"].lower()
            self.alias_map[name] = sid
            if s.get("abbreviation"):
                self.alias_map[s["abbreviation"].lower().replace("-", "")] = sid
                self.alias_map[s["abbreviation"].lower()] = sid
            for a in s.get("aliases", []):
                self.alias_map[a.lower()] = sid
                self.alias_map[a.lower().replace("-", " ")] = sid
                self.alias_map[a.lower().replace("-", "")] = sid

        # Add common colloquial aliases
        colloquial = {
            "onorc": "SCH_ONORC",
            "one nation one ration card": "SCH_ONORC",
            "ration card portability": "SCH_ONORC",
            "mera ration": "SCH_ONORC",
            "pmsym": "SCH_PMSYM",
            "pm-sym": "SCH_PMSYM",
            "shram yogi": "SCH_PMSYM",
            "shram yogi mandhan": "SCH_PMSYM",
            "shram yogi maan-dhan": "SCH_PMSYM",
            "unorganised worker pension": "SCH_PMSYM",
            "nps traders": "SCH_NPST",
            "trader pension": "SCH_NPST",
            "pmjjby": "SCH_PMJJBY",
            "jeevan jyoti": "SCH_PMJJBY",
            "life insurance": "SCH_PMJJBY",
            "pmsby": "SCH_PMSBY",
            "suraksha bima": "SCH_PMSBY",
            "accidental insurance": "SCH_PMSBY",
            "apy": "SCH_APY",
            "atal pension": "SCH_APY",
            "atal pension yojana": "SCH_APY",
            "pm kisan": "SCH_PMKISAN",
            "pmkisan": "SCH_PMKISAN",
            "kisan samman": "SCH_PMKISAN",
            "kisan samman nidhi": "SCH_PMKISAN",
            "surya ghar": "SCH_PMSURYA",
            "pmsuryaghar": "SCH_PMSURYA",
            "solar rooftop": "SCH_PMSURYA",
            "muft bijli": "SCH_PMSURYA",
            "free solar electricity": "SCH_PMSURYA",
            "svanidhi": "SCH_SVANIDHI",
            "pm svanidhi": "SCH_SVANIDHI",
            "street vendor loan": "SCH_SVANIDHI",
            "vishwakarma": "SCH_VISHWA",
            "pm vishwakarma": "SCH_VISHWA",
            "artisan scheme": "SCH_VISHWA",
            "ujjwala": "SCH_PMUY",
            "pmuy": "SCH_PMUY",
            "free lpg": "SCH_PMUY",
            "gas cylinder": "SCH_PMUY",
            "mudra": "SCH_PMMY",
            "pmmy": "SCH_PMMY",
            "mudra loan": "SCH_PMMY",
            "fasal bima": "SCH_PMFBY",
            "pmfby": "SCH_PMFBY",
            "crop insurance": "SCH_PMFBY",
            "sukanya": "SCH_SSY",
            "ssy": "SCH_SSY",
            "sukanya samriddhi": "SCH_SSY",
            "pmay": "SCH_PMAYG",
            "pmay-g": "SCH_PMAYG",
            "pmayg": "SCH_PMAYG",
            "awaas yojana": "SCH_PMAYG",
            "gramin housing": "SCH_PMAYG",
            "jan dhan": "SCH_PMJDY",
            "pmjdy": "SCH_PMJDY",
            "zero balance account": "SCH_PMJDY",
            "mgnrega": "SCH_MGNREGA",
            "nrega": "SCH_MGNREGA",
            "100 days work": "SCH_MGNREGA",
            "rozgar yojana": "SCH_MGNREGA",
            "vb-g ram g": "SCH_VBG_RAMG",
            "viksit bharat rozgar": "SCH_VBG_RAMG",
            "kisan mandhan": "SCH_PMJKMY",
            "pm-kmy": "SCH_PMJKMY",
            "ddu-gky": "SCH_DDUGKY",
            "garib kalyan": "SCH_GKRY",
            "gkry": "SCH_GKRY",
            "day-nrlm": "SCH_DAY",
            "kaushal vikas": "SCH_PMKVY",
            "pmkvy": "SCH_PMKVY",
            "nsap": "SCH_NSAP",
            "old age pension": "SCH_NSAP_OA",
            "ignoaps": "SCH_NSAP_OA",
            "widow pension": "SCH_NSAP_W",
            "ignwps": "SCH_NSAP_W",
            "disability pension": "SCH_NSAP_D",
            "igndps": "SCH_NSAP_D",
            "family benefit": "SCH_NSAP_FB",
            "nfbs": "SCH_NSAP_FB",
            "annapurna": "SCH_NSAP_AP",
            "annapurna scheme": "SCH_NSAP_AP",
            "ayushman bharat": "SCH_ABPMJAY",
            "pmjay": "SCH_ABPMJAY",
            "sehat bima": "SCH_ABPMJAY",
            "weavers health insurance": "SCH_HIS_WEAVERS",
            "manual scavengers": "SCH_SRMS",
            "srms": "SCH_SRMS",
            "bocw": "SCH_BOCW",
            "construction worker welfare": "SCH_BOCW"
        }
        self.alias_map.update(colloquial)

        # Sort alias keys by length descending to match longest phrases first
        self.sorted_aliases = sorted(self.alias_map.keys(), key=lambda x: len(x), reverse=True)
        # Pre-compile regexes once for microsecond matching
        self.compiled_aliases = [
            (re.compile(r'\b' + re.escape(alias) + r'\b'), self.alias_map[alias])
            for alias in self.sorted_aliases
        ]

    def extract_entities(self, query: str) -> Tuple[EntitySlots, UserDemographics]:
        q_lower = query.lower()
        matched_schemes = []
        matched_names = []

        # 1. Extract Scheme IDs using pre-compiled patterns
        for pattern, sid in self.compiled_aliases:
            if pattern.search(q_lower):
                if sid not in matched_schemes:
                    matched_schemes.append(sid)
                    s_obj = self.repo.get_scheme_by_id(sid)
                    if s_obj:
                        matched_names.append(s_obj["official_name"])

        # Check domain phrases for ONORC (ration in state, ration portability, claim ration)
        if re.search(r'\b(?:get\s*ration|claim\s*ration|collect\s*ration|ration\s*in\s+[a-z]+|ration\s*from\s+[a-z]+|inter[\s-]*state\s*ration|ration\s*portability)\b', q_lower):
            if "SCH_ONORC" not in matched_schemes:
                matched_schemes.append("SCH_ONORC")
                s_obj = self.repo.get_scheme_by_id("SCH_ONORC")
                if s_obj and s_obj["official_name"] not in matched_names:
                    matched_names.append(s_obj["official_name"])

        # 2. Extract Age & Age Category
        age = None
        age_category = None
        gender = None

        # Check explicit age patterns
        age_patterns = [
            r'(\d{1,2})\s*(?:years?\s*old|yrs?\s*old|age|year\s*old)',
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

        # Check informal age categories (without guessing exact age)
        if re.search(r'\b(?:old\s*person|old\s*age|elderly|senior\s*citizen|aged(?:\s*person)?|retired)\b', q_lower) or re.search(r'\bi\'?m\s*old\b', q_lower):
            age_category = "ELDERLY"
            # exact_age remains None unless explicitly stated numerically!
        elif re.search(r'\b(?:girl\s*child|little\s*girl)\b', q_lower):
            age_category = "CHILD"
            gender = "FEMALE"
        elif re.search(r'\b(?:youth|young\s*person|student)\b', q_lower):
            age_category = "YOUTH"

        # 3. Extract Income / Turnover (with Indian currency & unit normalization)
        income = None
        turnover = None

        # 3a. Check Lakhs
        lakh_match = re.search(r'(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?)\s*(?:lakhs?|lac|lacs?|l)\b', q_lower)
        if lakh_match:
            lakh_val = float(lakh_match.group(1)) * 100000
            if "turnover" in q_lower or "annual" in q_lower or "per annum" in q_lower or "per year" in q_lower:
                turnover = lakh_val
            else:
                income = lakh_val

        # 3b. Check Crores
        cr_match = re.search(r'(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?)\s*(?:cr|crore|crores)\b', q_lower)
        if cr_match:
            turnover = float(cr_match.group(1)) * 10000000

        # 3c. Check standard income / salary patterns (e.g. 15k, 15000)
        if income is None:
            k_match = re.search(r'(?:income|salary|earn|earning|monthly)?\s*(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?)\s*k\b', q_lower)
            if k_match:
                income = float(k_match.group(1)) * 1000
            else:
                income_match = re.search(r'(?:income|salary|earn|earning|monthly)\s*(?:of|is|:)?\s*(?:rs\.?|inr|₹)?\s*(\d+[\d,]*)\s*(?:thousand)?', q_lower)
                if income_match:
                    raw_val = income_match.group(1).replace(",", "")
                    income = float(raw_val)
                    if "thousand" in income_match.group(0):
                        income *= 1000

        # 4. Extract Land holding
        land = None
        land_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:hectares?|ha|acres?)', q_lower)
        if land_match:
            land = float(land_match.group(1))
            if "acre" in land_match.group(0):
                land = land * 0.404686  # convert acres to hectares

        # 5. Extract Occupation / Employment / Trade attributes
        occupation = None
        trade = None
        is_unorganised = None

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
                occupation = "ARTISAN"
                break

        if not occupation:
            if re.search(r'\b(?:farmer|kisan|cultivator|agriculture)\b', q_lower):
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

        if "unorganised" in q_lower or "informal sector" in q_lower or "daily wager" in q_lower:
            is_unorganised = True

        # 6. Extract Tax & Formal Social Security status
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

        # 7. Extract BPL status
        is_bpl = None
        if re.search(r'\b(?:bpl|below\s*poverty\s*line|poor\s*family|poor\s*household|antyodaya)\b', q_lower):
            is_bpl = True
        elif re.search(r'\b(?:apl|above\s*poverty\s*line|non-bpl)\b', q_lower):
            is_bpl = False

        # 8. Extract Geographic / Area Type
        area_type = None
        if re.search(r'\b(?:rural|village|gramin|panchayat)\b', q_lower):
            area_type = "RURAL"
        elif re.search(r'\b(?:urban|city|shehri|town|municipality)\b', q_lower):
            area_type = "URBAN"

        # 9. Extract Gender & Marital Status
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

        # 9b. Extract State
        residence_state = None
        for st_key, st_name in sorted(INDIAN_STATES.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(r'\b' + re.escape(st_key) + r'\b', q_lower):
                residence_state = st_name
                break

        # 10. Extract Institutional flags
        has_smart_ration_card = True if "smart ration card" in q_lower else None
        has_ration_card = True if ("ration card" in q_lower or has_smart_ration_card) else None
        in_secc_2011 = True if "secc" in q_lower else None
        is_jform = True if ("j-form" in q_lower or "j form" in q_lower) else None
        is_bocw = True if "bocw" in q_lower else None
        is_journalist = True if "journalist" in q_lower else None
        is_aadhaar_seeded = True if ("aadhaar" in q_lower and ("seed" in q_lower or "link" in q_lower)) else None

        # 11. Extract Document keywords
        doc_keywords = []
        for kw in ["aadhaar", "ration card", "bank passbook", "pan card", "land record", "electricity bill", "voter id"]:
            if kw in q_lower:
                doc_keywords.append(kw)

        slots = EntitySlots(
            scheme_ids=matched_schemes,
            scheme_names=matched_names,
            age=age,
            age_category=age_category,
            income=income,
            occupation=occupation,
            trade=trade,
            gender=gender,
            area_type=area_type,
            residence_state=residence_state,
            state=residence_state,
            marital_status=marital_status,
            is_bpl=is_bpl,
            has_smart_ration_card=has_smart_ration_card,
            document_keywords=doc_keywords
        )

        demographics = UserDemographics(
            age=age,
            age_category=age_category,
            gender=gender,
            monthly_income=income,
            annual_turnover=turnover,
            land_holding_hectares=land,
            occupation=occupation,
            trade=trade,
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
        Extracts a slot value from short conversational responses (e.g. '68', 'yes', 'rural', 'carpenter', 'kerala')
        given a known pending slot.
        Returns (extracted: bool, value: Any).
        """
        q_clean = query.strip().lower()

        # Slot: age / exact_age
        if pending_slot in ["age", "exact_age", "demographic.age"]:
            m = re.search(r'^(?:i(?:\'m|\s*am)\s*)?(\d{1,3})\s*(?:years?(?:\s*old)?|yrs?)?\.?$', q_clean)
            if m:
                val = int(m.group(1))
                if 1 <= val <= 110:
                    return True, val
            # General number extractor in query
            m_num = re.search(r'\b(\d{1,3})\b', q_clean)
            if m_num:
                val = int(m_num.group(1))
                if 1 <= val <= 110:
                    return True, val

        # Boolean slots: is_bpl, is_unorganised_worker, is_income_tax_payer, has_ration_card, etc.
        boolean_slots = [
            "is_bpl", "economic.is_bpl", "is_unorganised_worker", "is_income_tax_payer",
            "is_epfo_or_esic_member", "has_ration_card", "is_aadhaar_seeded",
            "has_bank_account", "has_electricity_connection", "roof_suitable_solar"
        ]
        if pending_slot in boolean_slots:
            affirmatives = ["yes", "y", "haan", "yeah", "yup", "true", "correct", "i am", "i have", "bpl", "sure", "of course"]
            negatives = ["no", "n", "nahi", "nope", "false", "neither", "apl", "non-bpl", "i don't", "i do not", "not really", "never"]
            if any(re.search(r'\b' + re.escape(w) + r'\b', q_clean) for w in affirmatives):
                return True, True
            if any(re.search(r'\b' + re.escape(w) + r'\b', q_clean) for w in negatives):
                return True, False

        # Slot: state / residence_state
        if pending_slot in ["residence_state", "state", "geographic.state"]:
            for st_key, st_name in sorted(INDIAN_STATES.items(), key=lambda x: len(x[0]), reverse=True):
                if re.search(r'\b' + re.escape(st_key) + r'\b', q_clean):
                    return True, st_name

        # Slot: gender
        if pending_slot in ["gender", "demographic.gender"]:
            if re.search(r'\b(?:female|woman|women|girl|lady)\b', q_clean):
                return True, "FEMALE"
            if re.search(r'\b(?:male|man|men|boy)\b', q_clean):
                return True, "MALE"
            if re.search(r'\b(?:other|transgender)\b', q_clean):
                return True, "OTHER"

        # Slot: marital_status
        if pending_slot in ["marital_status", "demographic.marital_status"]:
            if re.search(r'\b(?:widow|vidhwa)\b', q_clean):
                return True, "WIDOW"
            if re.search(r'\b(?:widower)\b', q_clean):
                return True, "WIDOWER"
            if re.search(r'\b(?:married)\b', q_clean):
                return True, "MARRIED"
            if re.search(r'\b(?:single|unmarried)\b', q_clean):
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

        return False, None

    def extract_references(self, query: str) -> Dict[str, Any]:
        """
        Extracts ordinal and pronoun references (e.g. 'the second one', 'this scheme').
        """
        q_lower = query.lower()
        res = {
            "ordinal": None,
            "refers_to_active": False,
            "is_procedure_request": False,
            "is_documents_request": False,
            "is_benefits_request": False,
            "is_eligibility_request": False
        }

        # Ordinal checks (1-based index)
        if re.search(r'\b(?:first|1st)\s*(?:one|scheme)?\b', q_lower):
            res["ordinal"] = 1
        elif re.search(r'\b(?:second|2nd)\s*(?:one|scheme)?\b', q_lower):
            res["ordinal"] = 2
        elif re.search(r'\b(?:third|3rd)\s*(?:one|scheme)?\b', q_lower):
            res["ordinal"] = 3
        elif re.search(r'\b(?:fourth|4th)\s*(?:one|scheme)?\b', q_lower):
            res["ordinal"] = 4

        # Pronoun / demonstrative checks
        if re.search(r'\b(?:this\s*scheme|that\s*scheme|the\s*scheme|it)\b', q_lower):
            res["refers_to_active"] = True

        # Follow-up intent checks
        if re.search(r'\b(?:how\s*do\s*i\s*apply|how\s*to\s*apply|application\s*process|procedure)\b', q_lower):
            res["is_procedure_request"] = True
        if re.search(r'\b(?:documents?|papers?|proofs?)\b', q_lower):
            res["is_documents_request"] = True
        if re.search(r'\b(?:benefits?|payout|financial\s*assistance)\b', q_lower):
            res["is_benefits_request"] = True
        if re.search(r'\b(?:eligibility|criteria|qualify|eligible)\b', q_lower):
            res["is_eligibility_request"] = True

        return res

