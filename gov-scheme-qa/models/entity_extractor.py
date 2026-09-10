import re
from typing import List, Dict, Any, Optional, Tuple
from schemas.models import EntitySlots, UserDemographics
from store.database import SchemeRepository

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
            "old age pension": "SCH_NSAP",
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

    def extract_entities(self, query: str) -> Tuple[EntitySlots, UserDemographics]:
        q_lower = query.lower()
        matched_schemes = []
        matched_names = []

        # 1. Extract Scheme IDs
        for alias in self.sorted_aliases:
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, q_lower):
                sid = self.alias_map[alias]
                if sid not in matched_schemes:
                    matched_schemes.append(sid)
                    s_obj = self.repo.get_scheme_by_id(sid)
                    if s_obj:
                        matched_names.append(s_obj["official_name"])

        # 2. Extract Age
        age = None
        age_patterns = [
            r'(\d{1,2})\s*(?:years?\s*old|yrs?\s*old|age|year\s*old)',
            r'age\s*(?:is|of|:)?\s*(\d{1,2})',
            r'i\s*am\s*(\d{1,2})\b',
        ]
        for p in age_patterns:
            m = re.search(p, q_lower)
            if m:
                val = int(m.group(1))
                if 1 <= val <= 100:
                    age = val
                    break

        # 3. Extract Income / Turnover
        income = None
        turnover = None
        income_match = re.search(r'(?:income|salary|earn|earning|monthly)\s*(?:of|is|:)?\s*(?:rs\.?|inr)?\s*(\d+[\d,]*)\s*(?:k|thousand)?', q_lower)
        if income_match:
            raw_val = income_match.group(1).replace(",", "")
            income = float(raw_val)
            if "k" in income_match.group(0):
                income *= 1000

        turnover_match = re.search(r'turnover\s*(?:of|is|:)?\s*(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:cr|crore)', q_lower)
        if turnover_match:
            turnover = float(turnover_match.group(1)) * 10000000

        # 4. Extract Land holding
        land = None
        land_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:hectares?|ha|acres?)', q_lower)
        if land_match:
            land = float(land_match.group(1))
            if "acre" in land_match.group(0):
                land = land * 0.404686  # convert acres to hectares

        # 5. Extract Occupation / Employment attributes
        occupation = None
        is_unorganised = None
        if re.search(r'\b(?:farmer|kisan|cultivator|agriculture)\b', q_lower):
            occupation = "FARMER"
        elif re.search(r'\b(?:street vendor|hawker|vendor|rehri|thela)\b', q_lower):
            occupation = "STREET_VENDOR"
        elif re.search(r'\b(?:trader|shopkeeper|retailer|small business)\b', q_lower):
            occupation = "TRADER"
        elif re.search(r'\b(?:artisan|craftsperson|carpenter|blacksmith|potter|sculptor|tailor|cobbler)\b', q_lower):
            occupation = "ARTISAN"
        elif re.search(r'\b(?:construction worker|building worker|mason|labourer|laborer|unorganised worker|migrant worker|gig worker|platform worker|driver)\b', q_lower):
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

        # 7. Extract Gender
        gender = None
        if re.search(r'\b(?:female|woman|women|girl|mother|daughter|lady)\b', q_lower):
            gender = "FEMALE"
        elif re.search(r'\b(?:male|man|men|boy|son|father)\b', q_lower):
            gender = "MALE"

        # 8. Extract Institutional flags
        has_ration_card = True if "ration card" in q_lower else None
        is_aadhaar_seeded = True if ("aadhaar" in q_lower and ("seed" in q_lower or "link" in q_lower)) else None

        # 9. Extract Document keywords
        doc_keywords = []
        for kw in ["aadhaar", "ration card", "bank passbook", "pan card", "land record", "electricity bill", "voter id"]:
            if kw in q_lower:
                doc_keywords.append(kw)

        slots = EntitySlots(
            scheme_ids=matched_schemes,
            scheme_names=matched_names,
            age=age,
            income=income,
            occupation=occupation,
            gender=gender,
            document_keywords=doc_keywords
        )

        demographics = UserDemographics(
            age=age,
            gender=gender,
            monthly_income=income,
            annual_turnover=turnover,
            land_holding_hectares=land,
            occupation=occupation,
            is_unorganised_worker=is_unorganised,
            is_income_tax_payer=is_tax_payer,
            is_epfo_or_esic_member=is_epfo_esic,
            has_ration_card=has_ration_card,
            is_aadhaar_seeded=is_aadhaar_seeded
        )

        return slots, demographics
