"""
Canonical Scheme Resolution Layer.
Handles:
- Exact name, abbreviation, aliases, and keyword matching.
- Person name vs Scheme name disambiguation (e.g. 'Rahul Sharma' is never a scheme).
- Ambiguity detection (e.g. 'Indira Gandhi scheme' triggers structured clarification).
- Unknown scheme detection (e.g. 'thee-shram' / 'e-shram' is caught as unknown, preventing fallback to previous scheme).
- Fuzzy / phonetic typo tolerance (e.g. 'viswakaram', 'pm vishwakarma loan', 'street vendor loan').
"""

import re
from typing import Dict, Any, List, Optional, Tuple, Set
from pydantic import BaseModel, Field
from store.database import SchemeRepository

class SchemeResolutionResult(BaseModel):
    matched_scheme_ids: List[str] = []
    matched_scheme_names: List[str] = []
    is_ambiguous: bool = False
    ambiguous_candidates: List[str] = []
    ambiguity_prompt: Optional[str] = None
    is_unknown_scheme: bool = False
    unknown_scheme_name: Optional[str] = None
    confidence: float = 1.0

class SchemeResolver:
    def __init__(self, repo: Optional[SchemeRepository] = None):
        self.repo = repo or SchemeRepository()
        self._load_scheme_index()

    def _load_scheme_index(self):
        all_schemes = self.repo.get_all_schemes()
        self.schemes_by_id: Dict[str, Dict[str, Any]] = {s["scheme_id"]: s for s in all_schemes}

        # Human names and generic occupation negative filter
        self.negative_names = {
            "rahul", "sharma", "sivaguru", "singh", "kumar", "priya", "amit", "gupta",
            "verma", "patel", "anil", "sunil", "deepak", "rohit", "pooja", "neha",
            "engineer", "doctor", "lawyer", "manager", "officer", "clerk", "accountant",
            "teacher", "worker", "employee", "student", "citizen", "person", "applicant"
        }

        # Curated canonical alias & keyword mappings
        self.scheme_aliases: Dict[str, List[str]] = {
            "SCH_SVANIDHI": [
                "pm svanidhi", "svanidhi", "street vendor loan", "vendor loan", "street vendor scheme",
                "street vendor", "pm street vendor", "thele wala loan", "rehri patri loan"
            ],
            "SCH_VISHWA": [
                "pm vishwakarma", "pm vishwakarma scheme", "vishwakarma", "vishwakarma scheme",
                "artisan loan", "artisan scheme", "traditional craftsperson loan", "vishwakarma loan",
                "pmv", "visvakaram", "vishwakarm", "viswakarma", "traditional artisan loan"
            ],
            "SCH_PMUY": [
                "pmuy", "pm ujjwala", "pm ujjwala yojana", "ujjwala", "ujjwala yojana",
                "lpg scheme", "gas cylinder scheme", "free gas connection", "ujjwala scheme"
            ],
            "SCH_NSAP_OA": [
                "ignoaps", "indira gandhi old age pension", "indira gandhi national old age pension",
                "old age pension scheme", "old age pension", "nsap old age", "nsap-oa", "national old age pension"
            ],
            "SCH_NSAP_W": [
                "ignwps", "indira gandhi widow pension", "indira gandhi national widow pension",
                "widow pension scheme", "widow pension", "nsap widow", "nsap-w", "national widow pension"
            ],
            "SCH_NSAP_D": [
                "igndps", "indira gandhi disability pension", "indira gandhi national disability pension",
                "disability pension scheme", "disability pension", "nsap disability", "nsap-d", "handicapped pension"
            ],
            "SCH_NSAP_FB": [
                "nfbs", "national family benefit scheme", "family benefit scheme", "breadwinner death benefit",
                "nsap family benefit", "nsap-fb"
            ],
            "SCH_NSAP_AP": [
                "annapurna", "annapurna scheme", "free food grains elderly", "nsap annapurna", "nsap-ap"
            ],
            "SCH_PMSYM": [
                "pm-sym", "pmsym", "pm sym", "shram yogi", "shram yogi maandhan", "shram yogi mandhan",
                "unorganised worker pension", "pradhan mantri shram yogi"
            ],
            "SCH_PMKISAN": [
                "pm-kisan", "pmkisan", "pm kisan", "kisan samman nidhi", "farmer income support",
                "kisan samman", "6000 farmer scheme"
            ],
            "SCH_PMJKMY": [
                "pm-kmy", "pmkmy", "kisan mandhan", "kisan maandhan", "farmer pension scheme", "farmer pension"
            ],
            "SCH_PMJJBY": [
                "pmjjby", "pm-jjby", "jeevan jyoti", "jeevan jyoti bima", "pradhan mantri jeevan jyoti",
                "life insurance scheme"
            ],
            "SCH_PMSBY": [
                "pmsby", "pm-sby", "suraksha bima", "suraksha bima yojana", "pradhan mantri suraksha bima",
                "accident insurance scheme"
            ],
            "SCH_PMMY": [
                "pmmy", "mudra", "mudra loan", "mudra yojana", "pradhan mantri mudra", "shishu kishor tarun"
            ],
            "SCH_PMSURYA": [
                "pm surya ghar", "surya ghar", "muft bijli", "rooftop solar", "solar subsidy",
                "surya ghar muft bijli"
            ],
            "SCH_PMAYG": [
                "pmay-g", "pmayg", "pmay gramin", "rural housing scheme", "awaas yojana gramin",
                "awaas yojana", "pradhan mantri awas yojana"
            ],
            "SCH_PMFBY": [
                "pmfby", "pm fasal bima", "fasal bima", "fasal bima yojana", "crop insurance"
            ],
            "SCH_PMJDY": [
                "pmjdy", "jan dhan", "jan dhan yojana", "pradhan mantri jan dhan", "basic bank account",
                "zero balance account"
            ],
            "SCH_ABPMJAY": [
                "ab pm-jay", "abpmjay", "ayushman bharat", "mmsby", "sehat bima", "health insurance punjab",
                "mukhmantri sehat bima"
            ],
            "SCH_APY": [
                "apy", "atal pension", "atal pension yojana", "nps-lite", "pfrda pension"
            ],
            "SCH_BOCW": [
                "bocw", "construction workers welfare", "building workers welfare", "bocw board"
            ],
            "SCH_ONORC": [
                "onorc", "one nation one ration card", "ration portability", "mera ration", "one nation ration"
            ],
            "SCH_MGNREGA": [
                "mgnrega", "nrega", "100 days work", "mgnregs", "rural employment guarantee"
            ],
            "SCH_SSY": [
                "ssy", "sukanya samriddhi", "sukanya samriddhi yojana", "girl child savings scheme"
            ],
            "SCH_DDUGKY": [
                "ddu-gky", "ddugky", "grameen kaushalya", "rural skill training"
            ],
            "SCH_DAY": [
                "day-nrlm", "antyodaya yojana", "deen dayal antyodaya"
            ],
            "SCH_GKRY": [
                "gkry", "garib kalyan rozgar"
            ],
            "SCH_HIS_WEAVERS": [
                "his weavers", "weaver health insurance"
            ],
            "SCH_NPST": [
                "nps traders", "vyapari pension", "shopkeeper pension"
            ],
            "SCH_PMKVY": [
                "pmkvy", "kaushal vikas", "skill india"
            ],
            "SCH_SRMS": [
                "srms", "manual scavengers"
            ],
            "SCH_VBG_RAMG": [
                "vb-g ram g", "viksit bharat rozgar", "125 days employment"
            ]
        }

        # Ambiguous families
        self.ambiguous_families = {
            "indira_gandhi": {
                "patterns": [
                    r'\bindira\s*gandhi(?:\s*(?:national)?\s*(?:pension|welfare)?\s*scheme)?\b',
                    r'\bnsap(?:\s*pension|\s*scheme)?\b'
                ],
                "candidates": ["SCH_NSAP_OA", "SCH_NSAP_W", "SCH_NSAP_D", "SCH_NSAP_FB"],
                "prompt": "Which Indira Gandhi scheme do you mean: Old Age Pension (IGNOAPS), Widow Pension (IGNWPS), Disability Pension (IGNDPS), or National Family Benefit Scheme (NFBS)?"
            }
        }

        # Known schemes outside knowledge base (for instant polite recognition)
        self.known_external_schemes = [
            "e-shram", "eshram", "thee-shram", "e shram", "pm kisan samman", "pm samman",
            "agnipath", "pm awas urban", "pmay-u", "kanyashree", "rythu bandhu", "kalia"
        ]

    def resolve(self, query: str, active_scheme_id: Optional[str] = None) -> SchemeResolutionResult:
        q_raw = query.strip()
        q_lower = q_raw.lower()

        # Step 0: Check if query contains human name statement (negative filter)
        # e.g., "Name: Rahul Sharma", "My name is Rahul Sharma"
        # We clean out person name prefixes so they aren't parsed as schemes
        name_clean = re.sub(r'\b(?:name|my\s*name\s*is)\s*:\s*[A-Za-z\s]+', ' ', q_lower)

        # Step 1: Check for Unknown / External Schemes
        # Catch patterns like 'thee-shram scheme', 'e-shram', 'xyz scheme'
        for ext in self.known_external_schemes:
            if re.search(r'\b' + re.escape(ext) + r'(?:\s*scheme)?\b', q_lower):
                return SchemeResolutionResult(
                    is_unknown_scheme=True,
                    unknown_scheme_name="e-Shram" if "shram" in ext else ext.title()
                )

        # Check generic unknown scheme pattern: e.g. "for <foo> scheme" / "about <foo> scheme"
        unknown_match = re.search(r'\b(?:for|about|in|of)\s+the\s+([a-z0-9\-_]+)\s+scheme\b', q_lower)
        if unknown_match:
            cand = unknown_match.group(1).strip()
            # If not a known keyword
            if cand not in ["this", "that", "first", "second", "other", "pension", "loan", "welfare", "government"]:
                # Check if it matches any internal scheme
                found_internal = False
                for sid, aliases in self.scheme_aliases.items():
                    if any(cand in a for a in aliases):
                        found_internal = True
                        break
                if not found_internal:
                    return SchemeResolutionResult(
                        is_unknown_scheme=True,
                        unknown_scheme_name=cand
                    )

        # Step 2: Check Ambiguous Schemes (e.g. "Indira Gandhi scheme")
        for fam_id, fam_data in self.ambiguous_families.items():
            for pat in fam_data["patterns"]:
                if re.search(pat, name_clean):
                    # Check if query also contains specific disambiguating keywords
                    if re.search(r'\b(?:old\s*age|elderly|60|aged|senior)\b', name_clean):
                        return SchemeResolutionResult(
                            matched_scheme_ids=["SCH_NSAP_OA"],
                            matched_scheme_names=[self.schemes_by_id["SCH_NSAP_OA"]["official_name"]],
                            confidence=0.98
                        )
                    if re.search(r'\b(?:widow|husband|spouse\s*death)\b', name_clean):
                        return SchemeResolutionResult(
                            matched_scheme_ids=["SCH_NSAP_W"],
                            matched_scheme_names=[self.schemes_by_id["SCH_NSAP_W"]["official_name"]],
                            confidence=0.98
                        )
                    if re.search(r'\b(?:disab|handicap|divyang)\b', name_clean):
                        return SchemeResolutionResult(
                            matched_scheme_ids=["SCH_NSAP_D"],
                            matched_scheme_names=[self.schemes_by_id["SCH_NSAP_D"]["official_name"]],
                            confidence=0.98
                        )
                    if re.search(r'\b(?:death|breadwinner|family\s*benefit)\b', name_clean):
                        return SchemeResolutionResult(
                            matched_scheme_ids=["SCH_NSAP_FB"],
                            matched_scheme_names=[self.schemes_by_id["SCH_NSAP_FB"]["official_name"]],
                            confidence=0.98
                        )

                    # Truly ambiguous!
                    return SchemeResolutionResult(
                        is_ambiguous=True,
                        ambiguous_candidates=fam_data["candidates"],
                        ambiguity_prompt=fam_data["prompt"],
                        confidence=0.95
                    )

        # Step 3: Exact & Alias Matching Across Curated Schemas
        matched_ids: List[str] = []
        matched_names: List[str] = []

        # Check curated aliases ordered by alias string length descending (longest match first)
        all_alias_tuples = []
        for sid, aliases in self.scheme_aliases.items():
            for a in aliases:
                all_alias_tuples.append((len(a), a, sid))
        all_alias_tuples.sort(key=lambda x: x[0], reverse=True)

        for _, alias, sid in all_alias_tuples:
            # Word boundary search
            pattern = r'\b' + re.escape(alias) + r'\b'
            if re.search(pattern, name_clean):
                if sid not in matched_ids:
                    matched_ids.append(sid)
                    if sid in self.schemes_by_id:
                        matched_names.append(self.schemes_by_id[sid]["official_name"])

        # Check DB official names & abbreviations as well
        for sid, scheme in self.schemes_by_id.items():
            if sid in matched_ids:
                continue
            off_name = scheme["official_name"].lower()
            abbrev = (scheme.get("abbreviation") or "").lower()

            STOPWORD_ABBREVIATIONS = {
                "his", "day", "in", "it", "at", "to", "on", "of", "for", "the", "and",
                "an", "as", "is", "he", "him", "her", "all", "can", "may", "so", "no", "we"
            }
            if abbrev and len(abbrev) >= 3 and abbrev not in STOPWORD_ABBREVIATIONS and re.search(r'\b' + re.escape(abbrev) + r'\b', name_clean):
                matched_ids.append(sid)
                matched_names.append(scheme["official_name"])
            elif off_name in name_clean:
                matched_ids.append(sid)
                matched_names.append(scheme["official_name"])

        return SchemeResolutionResult(
            matched_scheme_ids=matched_ids,
            matched_scheme_names=matched_names,
            confidence=0.99 if matched_ids else 0.0
        )
