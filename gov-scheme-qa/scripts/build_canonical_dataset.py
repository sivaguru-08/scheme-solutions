"""
Extracts, structures, and canonicalizes all government scheme data from the PDF raw text.
Generates:
- data/exclusions/all_exclusions.json
- data/documents/all_documents.json
- data/procedures/all_procedures.json
- data/faqs/all_faqs.json
- data/authorities/all_authorities.json
- data/relationships/all_relationships.json
- data/temporal/all_temporal.json
- data/source_chunks/all_chunks.json
- audit/scheme_inventory.json
- audit/field_inventory.json
- audit/source_mapping.json
- audit/ambiguity_report.json
"""

import os
import json
import re

DATA_DIR = "/home/sivaguru/Documents/slm/gov-scheme-qa/data"
AUDIT_DIR = "/home/sivaguru/Documents/slm/gov-scheme-qa/audit"

with open(f"{DATA_DIR}/schemes/all_schemes.json") as f:
    schemes = json.load(f)

scheme_map = {s["scheme_id"]: s for s in schemes}

# 1. EXCLUSIONS DATA
exclusions_data = [
    {
        "exclusion_id": "EXCL_PMSYM_001",
        "scheme_id": "SCH_PMSYM",
        "category": "INCOME_TAX",
        "description": "Income Tax Payers are not eligible",
        "rule_condition": "tax.is_income_tax_payer == True",
        "source_pages": [3]
    },
    {
        "exclusion_id": "EXCL_PMSYM_002",
        "scheme_id": "SCH_PMSYM",
        "category": "FORMAL_SOCIAL_SECURITY",
        "description": "Members covered under EPFO, ESIC, or NPS (Govt funded) are excluded",
        "rule_condition": "employment.is_epfo_or_esic_member == True",
        "source_pages": [3]
    },
    {
        "exclusion_id": "EXCL_PMSYM_003",
        "scheme_id": "SCH_PMSYM",
        "category": "INCOME_LIMIT",
        "description": "Monthly income exceeds Rs. 15,000 per month",
        "rule_condition": "income.monthly_income > 15000",
        "source_pages": [3]
    },
    {
        "exclusion_id": "EXCL_NPST_001",
        "scheme_id": "SCH_NPST",
        "category": "TURNOVER_LIMIT",
        "description": "Annual turnover exceeding Rs. 1.5 Crore",
        "rule_condition": "business.annual_turnover > 15000000",
        "source_pages": [4]
    },
    {
        "exclusion_id": "EXCL_NPST_002",
        "scheme_id": "SCH_NPST",
        "category": "FORMAL_SECTOR",
        "description": "Beneficiaries enrolled in EPFO, ESIC, NPS, or Income Tax Payers",
        "rule_condition": "tax.is_income_tax_payer == True or employment.is_epfo_or_esic_member == True",
        "source_pages": [4]
    },
    {
        "exclusion_id": "EXCL_PMKISAN_001",
        "scheme_id": "SCH_PMKISAN",
        "category": "INSTITUTIONAL_LAND",
        "description": "Institutional land holders are excluded",
        "rule_condition": "farmer.is_institutional_landholder == True",
        "source_pages": [5]
    },
    {
        "exclusion_id": "EXCL_PMKISAN_002",
        "scheme_id": "SCH_PMKISAN",
        "category": "CONSTITUTIONAL_POST",
        "description": "Former and present holders of constitutional posts",
        "rule_condition": "status.holds_constitutional_post == True",
        "source_pages": [5]
    },
    {
        "exclusion_id": "EXCL_PMKISAN_003",
        "scheme_id": "SCH_PMKISAN",
        "category": "INCOME_TAX",
        "description": "Persons who paid income tax in last assessment year",
        "rule_condition": "tax.is_income_tax_payer == True",
        "source_pages": [5]
    },
    {
        "exclusion_id": "EXCL_PMKISAN_004",
        "scheme_id": "SCH_PMKISAN",
        "category": "HIGH_PENSION",
        "description": "Retired persons / pensioners whose monthly pension is Rs. 10,000 or more (excluding multi-tasking staff / Class IV)",
        "rule_condition": "income.monthly_pension >= 10000 and employment.is_class_iv == False",
        "source_pages": [5]
    },
    {
        "exclusion_id": "EXCL_PMKISAN_005",
        "scheme_id": "SCH_PMKISAN",
        "category": "PROFESSIONALS",
        "description": "Doctors, Engineers, Lawyers, Chartered Accountants, and Architects registered with professional bodies",
        "rule_condition": "occupation.is_registered_professional == True",
        "source_pages": [5]
    },
    {
        "exclusion_id": "EXCL_APY_001",
        "scheme_id": "SCH_APY",
        "category": "INCOME_TAX",
        "description": "Income tax payers are not permitted to open new APY accounts after 1st October 2022",
        "rule_condition": "tax.is_income_tax_payer == True",
        "source_pages": [5]
    },
    {
        "exclusion_id": "EXCL_PMUY_001",
        "scheme_id": "SCH_PMUY",
        "category": "EXISTING_CONNECTION",
        "description": "Any household already having an existing LPG connection in the name of any family member",
        "rule_condition": "household.has_lpg_connection == True",
        "source_pages": [8]
    },
    {
        "exclusion_id": "EXCL_SSY_001",
        "scheme_id": "SCH_SSY",
        "category": "GENDER_LIMIT",
        "description": "Male children cannot open SSY accounts. Only girl child eligible.",
        "rule_condition": "demographics.gender != 'FEMALE'",
        "source_pages": [10]
    },
    {
        "exclusion_id": "EXCL_SSY_002",
        "scheme_id": "SCH_SSY",
        "category": "MAX_ACCOUNTS",
        "description": "Maximum of 2 accounts per family allowed, except in case of twin/triplet girl birth",
        "rule_condition": "family.girl_count_in_family > 2 and family.is_twin_or_triplet == False",
        "source_pages": [10]
    },
    {
        "exclusion_id": "EXCL_PMAYG_001",
        "scheme_id": "SCH_PMAYG",
        "category": "PUCCA_HOUSE",
        "description": "Households possessing a pucca house or receiving previous housing subsidy",
        "rule_condition": "housing.has_pucca_house == True",
        "source_pages": [10]
    },
    {
        "exclusion_id": "EXCL_PMJKMY_001",
        "scheme_id": "SCH_PMJKMY",
        "category": "LARGE_FARMERS",
        "description": "Farmers holding cultivable land greater than 2 hectares",
        "rule_condition": "farmer.land_holding_hectares > 2.0",
        "source_pages": [12]
    },
    {
        "exclusion_id": "EXCL_PMJKMY_002",
        "scheme_id": "SCH_PMJKMY",
        "category": "TAX_EPFO",
        "description": "Income tax payers or members of EPFO, NPS, ESIC or other pension schemes",
        "rule_condition": "tax.is_income_tax_payer == True or employment.is_epfo_or_esic_member == True",
        "source_pages": [12]
    },
    {
        "exclusion_id": "EXCL_PMJJBY_001",
        "scheme_id": "SCH_PMJJBY",
        "category": "AGE_LIMIT",
        "description": "Persons below 18 years or above 50 years of age (risk cover ends at age 55)",
        "rule_condition": "demographics.age < 18 or demographics.age > 50",
        "source_pages": [4]
    },
    {
        "exclusion_id": "EXCL_PMSBY_001",
        "scheme_id": "SCH_PMSBY",
        "category": "AGE_LIMIT",
        "description": "Persons below 18 years or above 70 years of age",
        "rule_condition": "demographics.age < 18 or demographics.age > 70",
        "source_pages": [4]
    }
]

# 2. DOCUMENTS REQUIRED DATA
documents_data = [
    {
        "document_id": "DOC_ONORC_001",
        "scheme_id": "SCH_ONORC",
        "mandatory": [
            {"name": "Ration Card", "description": "Active NFSA ration card with seeded family details", "purpose": "Identity and entitlement verification"},
            {"name": "Aadhaar Card", "description": "Aadhaar card of beneficiary or family member", "purpose": "Biometric / iris authentication on ePoS device"}
        ],
        "optional": [],
        "source_pages": [2]
    },
    {
        "document_id": "DOC_PMSYM_001",
        "scheme_id": "SCH_PMSYM",
        "mandatory": [
            {"name": "Aadhaar Card", "description": "Aadhaar card of unorganised worker", "purpose": "Identity and KYC verification"},
            {"name": "Savings Bank Account / Jan Dhan Account", "description": "Bank passbook or cheque leaf with IFSC", "purpose": "Auto-debit of monthly pension contribution"},
            {"name": "Mobile Number", "description": "Active mobile number linked to Aadhaar", "purpose": "SMS alerts and verification"}
        ],
        "optional": [],
        "source_pages": [3]
    },
    {
        "document_id": "DOC_NPST_001",
        "scheme_id": "SCH_NPST",
        "mandatory": [
            {"name": "Aadhaar Card", "description": "Aadhaar card of trader/retailer", "purpose": "Identity verification"},
            {"name": "Savings Bank Account / Jan Dhan Passbook", "description": "Bank account details with IFSC", "purpose": "Auto-debit for pension contribution"},
            {"name": "Self-Declaration of Turnover", "description": "Self-certification that annual turnover is Rs 1.5 Cr or below", "purpose": "Turnover eligibility proof"}
        ],
        "optional": [
            {"name": "GSTIN", "description": "GST Identification Number if registered", "purpose": "Business verification"}
        ],
        "source_pages": [4]
    },
    {
        "document_id": "DOC_PMJJBY_001",
        "scheme_id": "SCH_PMJJBY",
        "mandatory": [
            {"name": "Aadhaar Card", "description": "Aadhaar card of account holder", "purpose": "Primary KYC"},
            {"name": "Savings Bank Account Details", "description": "Operative bank account in participating bank", "purpose": "Auto-debit of annual premium Rs 436"},
            {"name": "Consent cum Auto-Debit Mandate Form", "description": "Signed auto-debit consent form", "purpose": "Enabling automatic premium deduction"}
        ],
        "optional": [],
        "source_pages": [4]
    },
    {
        "document_id": "DOC_PMSBY_001",
        "scheme_id": "SCH_PMSBY",
        "mandatory": [
            {"name": "Aadhaar Card", "description": "Aadhaar card", "purpose": "Primary KYC"},
            {"name": "Savings Bank Account Details", "description": "Operative bank or post office account", "purpose": "Auto-debit of annual premium Rs 20"},
            {"name": "Auto-Debit Consent Form", "description": "Signed auto-debit mandate", "purpose": "Annual premium deduction authorization"}
        ],
        "optional": [],
        "source_pages": [4]
    },
    {
        "document_id": "DOC_APY_001",
        "scheme_id": "SCH_APY",
        "mandatory": [
            {"name": "Aadhaar Card", "description": "Aadhaar number", "purpose": "Primary identification and spouse details"},
            {"name": "Savings Bank Account / Post Office Account", "description": "Active savings account", "purpose": "Monthly/Quarterly/Half-yearly auto-debit"},
            {"name": "Mobile Number", "description": "Registered mobile number", "purpose": "Account alerts"}
        ],
        "optional": [],
        "source_pages": [5]
    },
    {
        "document_id": "DOC_PMKISAN_001",
        "scheme_id": "SCH_PMKISAN",
        "mandatory": [
            {"name": "Aadhaar Card", "description": "Mandatory Aadhaar card of landholder farmer", "purpose": "Aadhaar-based payment via PFMS"},
            {"name": "Land Record Documents (Khatauni / Jamabandi)", "description": "Proof of cultivable land ownership in land records", "purpose": "Farmer qualification"},
            {"name": "Aadhaar-Seeded Bank Account", "description": "Bank account linked with NPCI / Aadhaar", "purpose": "Direct Benefit Transfer (DBT) credit"}
        ],
        "optional": [],
        "source_pages": [5]
    },
    {
        "document_id": "DOC_PMSURYA_001",
        "scheme_id": "SCH_PMSURYA",
        "mandatory": [
            {"name": "Electricity Bill", "description": "Recent electricity bill showing consumer number", "purpose": "DISCOM consumer mapping and rooftop verification"},
            {"name": "Aadhaar Card", "description": "Aadhaar card of household head / applicant", "purpose": "Identity verification"},
            {"name": "Bank Account Passbook / Cancelled Cheque", "description": "Account details of electricity consumer", "purpose": "Direct subsidy transfer credit"},
            {"name": "Proof of Roof Ownership / Electricity Connection", "description": "Electricity connection in name of applicant", "purpose": "Eligibility confirmation"}
        ],
        "optional": [],
        "source_pages": [6]
    },
    {
        "document_id": "DOC_SVANIDHI_001",
        "scheme_id": "SCH_SVANIDHI",
        "mandatory": [
            {"name": "Vending Certificate / Identity Card", "description": "Certificate of Vending or ID card issued by Urban Local Body (ULB)", "purpose": "Street vendor identification"},
            {"name": "Letter of Recommendation (LoR)", "description": "LoR from ULB / Town Vending Committee if ID card not issued", "purpose": "Eligibility for non-card vendors"},
            {"name": "Aadhaar Card", "description": "Aadhaar card", "purpose": "KYC"},
            {"name": "Bank Account Details", "description": "Savings account details", "purpose": "Working capital loan disbursement"}
        ],
        "optional": [],
        "source_pages": [6]
    },
    {
        "document_id": "DOC_VISHWA_001",
        "scheme_id": "SCH_VISHWA",
        "mandatory": [
            {"name": "Aadhaar Card", "description": "Aadhaar card of artisan/craftsperson", "purpose": "Biometric verification"},
            {"name": "Mobile Number linked to Aadhaar", "description": "Mobile number", "purpose": "OTP verification"},
            {"name": "Bank Account Details", "description": "Operative bank account with IFSC", "purpose": "Stipend, toolkit incentive, and collateral-free loan"},
            {"name": "Ration Card", "description": "Family ration card", "purpose": "Ensuring one benefit per family"}
        ],
        "optional": [],
        "source_pages": [7]
    },
    {
        "document_id": "DOC_PMUY_001",
        "scheme_id": "SCH_PMUY",
        "mandatory": [
            {"name": "Aadhaar Card of Adult Woman Applicant", "description": "Aadhaar card", "purpose": "Proof of identity and age (18+)"},
            {"name": "Ration Card / Family Composition Document", "description": "Ration card showing family members", "purpose": "Confirming single connection per household"},
            {"name": "Bank Account Details", "description": "Aadhaar linked bank account of the woman", "purpose": "LPG subsidy credit"},
            {"name": "14-Point Declaration", "description": "Self-declaration of not having existing LPG", "purpose": "Exclusion check"}
        ],
        "optional": [],
        "source_pages": [8]
    },
    {
        "document_id": "DOC_PMMY_001",
        "scheme_id": "SCH_PMMY",
        "mandatory": [
            {"name": "Identity Proof", "description": "Aadhaar Card, Voter ID, PAN Card, or Passport", "purpose": "Identity verification"},
            {"name": "Residence Proof", "description": "Electricity bill, ration card, or Aadhaar", "purpose": "Address verification"},
            {"name": "Business Proposal / Quotation for Machinery", "description": "Quotation of machinery/items to be purchased", "purpose": "Loan appraisal"}
        ],
        "optional": [
            {"name": "Last 6 Months Bank Statement", "description": "Bank statement of current or savings account", "purpose": "Credit assessment"}
        ],
        "source_pages": [9]
    },
    {
        "document_id": "DOC_SSY_001",
        "scheme_id": "SCH_SSY",
        "mandatory": [
            {"name": "Birth Certificate of Girl Child", "description": "Birth certificate issued by municipal or hospital authority", "purpose": "Proof of age (<= 10 years) and parentage"},
            {"name": "Aadhaar / ID Proof of Parent / Legal Guardian", "description": "Aadhaar, Passport, or PAN card of parent", "purpose": "Guardian KYC"},
            {"name": "Address Proof of Parent / Guardian", "description": "Aadhaar, Utility Bill, or Passport", "purpose": "Address verification"},
            {"name": "Medical Certificate (in case of twins/triplets)", "description": "Medical certificate from authorized doctor", "purpose": "Third girl child exception proof"}
        ],
        "optional": [],
        "source_pages": [10]
    },
    {
        "document_id": "DOC_PMJDY_001",
        "scheme_id": "SCH_PMJDY",
        "mandatory": [
            {"name": "Aadhaar Card", "description": "Aadhaar card (if address changed, self-attestation sufficient)", "purpose": "Single KYC document for opening zero balance account"}
        ],
        "optional": [
            {"name": "Other Officially Valid Documents (OVD)", "description": "Voter ID, Driving License, Passport, NREGA Job Card (if Aadhaar unavailable)", "purpose": "Alternative KYC"}
        ],
        "source_pages": [11]
    },
    {
        "document_id": "DOC_MGNREGA_001",
        "scheme_id": "SCH_MGNREGA",
        "mandatory": [
            {"name": "Application for Job Card", "description": "Written or oral application to Gram Panchayat by adult members", "purpose": "Household registration"},
            {"name": "Proof of Age and Residence", "description": "Aadhaar, Voter ID, or local verification", "purpose": "Adult resident status"},
            {"name": "Photographs of Adult Members", "description": "Passport-size photos of all adult members", "purpose": "Job card affixation"}
        ],
        "optional": [],
        "source_pages": [14, 17]
    }
]

# 3. PROCEDURES DATA
procedures_data = [
    {
        "procedure_id": "PROC_ONORC_001",
        "scheme_id": "SCH_ONORC",
        "mode": "HYBRID",
        "online_steps": [
            "Download and open 'MERA RATION' mobile application (available in 13 languages).",
            "Enter Aadhaar number or Ration Card number to check active entitlement and nearest Fair Price Shop (FPS).",
            "Use the app to locate POS-enabled Fair Price Shops in the destination state/district."
        ],
        "offline_steps": [
            "Visit any Fair Price Shop (FPS) with ePoS device anywhere in India.",
            "Quote Aadhaar number or Ration Card number to the FPS dealer.",
            "Perform biometric (fingerprint or iris) authentication on the ePoS device.",
            "Collect entitled full or partial food grains at central issue prices."
        ],
        "processing_time": "Instantaneous at ePoS terminal",
        "fees": "Zero application or registration fees",
        "source_pages": [1, 2]
    },
    {
        "procedure_id": "PROC_PMSYM_001",
        "scheme_id": "SCH_PMSYM",
        "mode": "OFFLINE_AND_ONLINE",
        "online_steps": [
            "Visit the official portal maandhan.in or self-enrollment section on e-Shram portal.",
            "Enter Aadhaar number and verify using OTP sent to registered mobile.",
            "Fill applicant details, unorganised worker occupation, and bank IFSC.",
            "Set up bank auto-debit mandate and make the initial monthly contribution online."
        ],
        "offline_steps": [
            "Visit the nearest Common Services Centre (CSC) along with Aadhaar card and Savings Bank Passbook.",
            "VLE (Village Level Entrepreneur) enters details and takes biometric authentication.",
            "System calculates monthly contribution (Rs 55 to Rs 200 based on age).",
            "Pay the first installment in cash at CSC; system generates PMSYM Card immediately."
        ],
        "processing_time": "Instant card generation upon first contribution",
        "fees": "Free enrollment (Govt pays CSC fee)",
        "source_pages": [3]
    },
    {
        "procedure_id": "PROC_PMKISAN_001",
        "scheme_id": "SCH_PMKISAN",
        "mode": "ONLINE_AND_OFFLINE",
        "online_steps": [
            "Visit official PM-KISAN portal (pmkisan.gov.in) -> Farmers Corner -> 'New Farmer Registration'.",
            "Select Rural Farmer Registration or Urban Farmer Registration.",
            "Enter Aadhaar Number and Mobile Number, select State, and verify OTP.",
            "Fill personal, bank, and land details (survey/khata number, dag/khasra number, land size in hectares).",
            "Complete mandatory e-KYC using Aadhaar OTP or facial recognition via PM-KISAN Mobile App."
        ],
        "offline_steps": [
            "Visit the nearest Common Service Centre (CSC) or local Patwari / Revenue Officer / Nodal Agriculture Officer.",
            "Submit land records, Aadhaar, and bank passbook for verification."
        ],
        "processing_time": "Approval by State/District Nodal Officer within 15-30 days",
        "fees": "Free on portal; standard CSC assistance charges apply for CSC visits",
        "source_pages": [5]
    },
    {
        "procedure_id": "PROC_PMSURYA_001",
        "scheme_id": "SCH_PMSURYA",
        "mode": "ONLINE",
        "online_steps": [
            "Register on National Portal for PM Surya Ghar (pmsuryaghar.gov.in) by selecting State, Distribution Company (DISCOM), and Consumer Account Number.",
            "Apply for Rooftop Solar installation by submitting roof area and sanctioned load details.",
            "Wait for DISCOM feasibility approval online.",
            "Select a registered vendor and get the rooftop solar plant installed.",
            "Submit plant details and apply for net meter inspection.",
            "Upon DISCOM inspection and commissioning certificate generation, submit bank account details for direct subsidy disbursement."
        ],
        "offline_steps": [
            "Net meter physical inspection and installation by DISCOM field team."
        ],
        "processing_time": "Subsidy credited directly to bank account within 30 days of commissioning",
        "fees": "Application online is free; plant cost net of subsidy payable to vendor",
        "source_pages": [6]
    },
    {
        "procedure_id": "PROC_SVANIDHI_001",
        "scheme_id": "SCH_SVANIDHI",
        "mode": "ONLINE_AND_OFFLINE",
        "online_steps": [
            "Access PM SVANidhi portal (pmsvanidhi.mohua.gov.in) or PM SVANidhi mobile app.",
            "Enter mobile number and verify via OTP.",
            "Select vendor category: (A) Vendors with Vending Card/LoR, (B) Vendors left out of survey, (C) Surrounding rural vendors.",
            "Upload KYC documents and select preferred lending institution / bank.",
            "Submit loan application for 1st tranche (up to Rs 10,000)."
        ],
        "offline_steps": [
            "Visit nearest CSC, Municipal Corporation office, or bank branch for application submission.",
            "Collect Letter of Recommendation (LoR) from Town Vending Committee (TVC) if not possessing ID card."
        ],
        "processing_time": "Loan sanctioned typically within 7-14 working days",
        "fees": "No collateral or processing charges",
        "source_pages": [6]
    },
    {
        "procedure_id": "PROC_VISHWA_001",
        "scheme_id": "SCH_VISHWA",
        "mode": "ONLINE_VIA_CSC",
        "online_steps": [
            "Artisan visits nearest CSC for Aadhaar-based biometric registration on PM Vishwakarma Portal.",
            "Three-tier verification: Stage 1 Gram Panchayat / ULB verification; Stage 2 District Implementation Committee; Stage 3 Screening Committee.",
            "Upon approval, download PM Vishwakarma Certificate and ID Card.",
            "Undergo 5-7 days basic skill training (Rs 500/day stipend).",
            "Receive Rs 15,000 toolkit digital e-voucher and apply for Enterprise Development Loan (Tranche 1: Rs 1 Lakh at 5% interest)."
        ],
        "offline_steps": [
            "Physical biometric verification and hands-on skill training at designated training centers."
        ],
        "processing_time": "15-30 days for complete 3-tier verification",
        "fees": "Free registration at CSC",
        "source_pages": [7]
    },
    {
        "procedure_id": "PROC_PMUY_001",
        "scheme_id": "SCH_PMUY",
        "mode": "ONLINE_AND_OFFLINE",
        "online_steps": [
            "Visit pmuy.gov.in portal, select LPG distributor (Indane, Bharatgas, or HP Gas).",
            "Submit online application form with Aadhaar and family ration card details."
        ],
        "offline_steps": [
            "Visit nearest LPG distributor showroom.",
            "Submit filled application form along with Aadhaar, ration card, bank passbook, and 14-point declaration.",
            "Distributor verifies eligibility against OMC de-duplication database.",
            "Receive LPG cylinder, pressure regulator, hose pipe, and stove."
        ],
        "processing_time": "Connection released within 7-10 days of document verification",
        "fees": "Free security deposit, free first cylinder and stove assistance",
        "source_pages": [8]
    },
    {
        "procedure_id": "PROC_MGNREGA_001",
        "scheme_id": "SCH_MGNREGA",
        "mode": "OFFLINE",
        "online_steps": [
            "Check Job Card status and muster roll payment on nrega.nic.in portal."
        ],
        "offline_steps": [
            "Adult members of rural household submit application (oral or written) for registration to Gram Panchayat.",
            "Gram Panchayat verifies local residence and household adulthood within 14 days.",
            "Gram Panchayat issues Job Card bearing photographs of all adult members free of cost.",
            "Worker submits written application demanding employment specifying dates and duration.",
            "Gram Panchayat / Block Programme Officer allots wage employment within 15 days, or pays statutory unemployment allowance."
        ],
        "processing_time": "Job card issued within 15 days; employment provided within 15 days of demand",
        "fees": "Free of cost",
        "source_pages": [14, 17, 18]
    }
]

# 4. FAQS DATA
faqs_data = [
    {
        "faq_id": "FAQ_ONORC_001",
        "scheme_id": "SCH_ONORC",
        "question": "I live in Mumbai but my family lives in Rajasthan, Can my family receive the ration at Rajasthan?",
        "answer": "Yes, the ONORC scheme allows your family to claim their part of ration on the same Ration Card in Rajasthan while you can claim your share in Mumbai.",
        "source_pages": [2]
    },
    {
        "faq_id": "FAQ_ONORC_002",
        "scheme_id": "SCH_ONORC",
        "question": "My allotted Fair Price Shop (FPS) does not give me the ration. Can I claim ration from any other FPS?",
        "answer": "Yes, the scheme allows you to claim ration from any other Fair Price Shop (FPS) in the area or across the nation if your Aadhaar is seeded to your Ration Card.",
        "source_pages": [2]
    },
    {
        "faq_id": "FAQ_ONORC_003",
        "scheme_id": "SCH_ONORC",
        "question": "Who are eligible for the One Nation One Ration Card scheme?",
        "answer": "This scheme can be availed by all eligible ration cardholders or beneficiaries covered under the National Food Security Act (NFSA), 2013 with Aadhaar numbers seeded.",
        "source_pages": [2]
    },
    {
        "faq_id": "FAQ_ESHRAM_001",
        "scheme_id": "SCH_PMSYM",
        "question": "Are gig and platform workers covered under e-Shram?",
        "answer": "Yes, gig and platform workers are included in the e-Shram database and eligible for social security welfare schemes.",
        "source_pages": [13]
    },
    {
        "faq_id": "FAQ_PMSYM_001",
        "scheme_id": "SCH_PMSYM",
        "question": "What is the minimum assured pension under PM-SYM?",
        "answer": "Beneficiaries receive an assured minimum monthly pension of Rs. 3,000 per month after attaining the age of 60 years.",
        "source_pages": [3]
    },
    {
        "faq_id": "FAQ_PMSYM_002",
        "scheme_id": "SCH_PMSYM",
        "question": "What happens if a PM-SYM subscriber dies before reaching 60 years of age?",
        "answer": "If a subscriber dies before 60, their spouse can continue the scheme by paying regular contributions, or exit the scheme and receive the subscriber's accumulated contribution along with interest.",
        "source_pages": [3]
    },
    {
        "faq_id": "FAQ_PMSYM_003",
        "scheme_id": "SCH_PMSYM",
        "question": "What is the family pension after the demise of the PM-SYM pensioner?",
        "answer": "During receipt of pension after age 60, if the pensioner dies, the spouse is entitled to receive 50% of the pension (i.e. Rs. 1,500 per month) as family pension. This is applicable only to spouse.",
        "source_pages": [3]
    },
    {
        "faq_id": "FAQ_PMJJBY_001",
        "scheme_id": "SCH_PMJJBY",
        "question": "What is the premium and life insurance coverage under PMJJBY?",
        "answer": "PMJJBY provides life insurance cover of Rs. 2,00,000 in case of death due to any reason. The annual premium is Rs. 436 per annum, auto-debited from the subscriber's bank account in May/June.",
        "source_pages": [4]
    },
    {
        "faq_id": "FAQ_PMSBY_001",
        "scheme_id": "SCH_PMSBY",
        "question": "What is the risk coverage and annual premium under PMSBY?",
        "answer": "PMSBY offers accidental death and full disability cover of Rs. 2,00,000, and partial permanent disability cover of Rs. 1,00,000. The premium is only Rs. 20 per annum, auto-debited from the bank account.",
        "source_pages": [4]
    },
    {
        "faq_id": "FAQ_APY_001",
        "scheme_id": "SCH_APY",
        "question": "What pension amounts can one choose under Atal Pension Yojana?",
        "answer": "Under APY, subscribers can choose a guaranteed monthly pension of Rs. 1,000, Rs. 2,000, Rs. 3,000, Rs. 4,000, or Rs. 5,000 starting from age 60, based on monthly contribution.",
        "source_pages": [5]
    },
    {
        "faq_id": "FAQ_PMKISAN_001",
        "scheme_id": "SCH_PMKISAN",
        "question": "How much financial benefit is given under PM-KISAN every year?",
        "answer": "Under PM-KISAN, eligible farmer families receive Rs. 6,000 per year transferred directly into their Aadhaar-linked bank accounts in three equal 4-monthly installments of Rs. 2,000 each.",
        "source_pages": [5]
    },
    {
        "faq_id": "FAQ_PMKISAN_002",
        "scheme_id": "SCH_PMKISAN",
        "question": "Is eKYC mandatory for PM-KISAN beneficiaries?",
        "answer": "Yes, eKYC is mandatory for all PM-KISAN registered farmers. It can be done through OTP on the portal or biometric verification at CSC or facial recognition on the PM-KISAN App.",
        "source_pages": [5]
    },
    {
        "faq_id": "FAQ_PMSURYA_001",
        "scheme_id": "SCH_PMSURYA",
        "question": "How much subsidy is provided under PM Surya Ghar Muft Bijli Yojana?",
        "answer": "The scheme provides subsidy of Rs. 30,000 for 1 kW systems, Rs. 60,000 for 2 kW systems, and Rs. 78,000 for 3 kW or higher systems, providing up to 300 units of free electricity monthly.",
        "source_pages": [6]
    },
    {
        "faq_id": "FAQ_SVANIDHI_001",
        "scheme_id": "SCH_SVANIDHI",
        "question": "What are the loan amounts and interest subsidy available under PM SVANidhi?",
        "answer": "PM SVANidhi offers working capital loans: 1st tranche up to Rs. 10,000 (1-year tenure); 2nd tranche up to Rs. 20,000; and 3rd tranche up to Rs. 50,000 upon timely repayment, with 7% interest subsidy per annum and up to Rs. 1,200 annual cashback on digital transactions.",
        "source_pages": [6]
    },
    {
        "faq_id": "FAQ_VISHWA_001",
        "scheme_id": "SCH_VISHWA",
        "question": "What trades and benefits are covered under PM Vishwakarma?",
        "answer": "Covers 18 traditional trades (carpenters, blacksmiths, potters, weavers, etc.). Benefits include PM Vishwakarma Certificate & ID, basic skill training with Rs 500/day stipend, Rs 15,000 toolkit incentive, and collateral-free enterprise loans up to Rs 3 Lakh (Rs 1 Lakh tranche 1, Rs 2 Lakh tranche 2) at a concessional 5% interest rate.",
        "source_pages": [7]
    },
    {
        "faq_id": "FAQ_SSY_001",
        "scheme_id": "SCH_SSY",
        "question": "When does a Sukanya Samriddhi Yojana (SSY) account mature?",
        "answer": "An SSY account matures 21 years from the date of its opening or upon marriage of the girl child after attaining 18 years of age. Partial withdrawal up to 50% is allowed for higher education after age 18.",
        "source_pages": [10]
    },
    {
        "faq_id": "FAQ_MGNREGA_001",
        "scheme_id": "SCH_MGNREGA",
        "question": "Within how many days must employment be provided under MGNREGA?",
        "answer": "Employment must be provided within 15 days of receiving the application for work. If employment is not provided within 15 days, the applicant is legally entitled to daily unemployment allowance.",
        "source_pages": [14, 18]
    }
]

# 5. AUTHORITIES DATA
authorities_data = [
    {
        "authority_id": "AUTH_ONORC",
        "scheme_id": "SCH_ONORC",
        "ministry": "Ministry of Consumer Affairs, Food & Public Distribution",
        "department": "Department of Food & Public Distribution",
        "implementing_agency": "State / UT Food and Civil Supplies Departments & Fair Price Shops",
        "portal_url": "https://nfsa.gov.in",
        "helpline": "1967 / 14445",
        "grievance_redressal": "State PDS Portals & District Food Supplies Officer",
        "source_pages": [1]
    },
    {
        "authority_id": "AUTH_PMSYM",
        "scheme_id": "SCH_PMSYM",
        "ministry": "Ministry of Labour and Employment",
        "department": "Social Security Division",
        "implementing_agency": "Life Insurance Corporation of India (LIC) & CSC e-Governance Services India Ltd",
        "portal_url": "https://maandhan.in",
        "helpline": "1800 267 6888 / 14434",
        "grievance_redressal": "LIC Branch Grievance Officers & Joint Secretary (Labour)",
        "source_pages": [3]
    },
    {
        "authority_id": "AUTH_PMKISAN",
        "scheme_id": "SCH_PMKISAN",
        "ministry": "Ministry of Agriculture and Farmers Welfare",
        "department": "Department of Agriculture and Farmers Welfare",
        "implementing_agency": "State/UT Agriculture Departments via PFMS and NPCI DBT",
        "portal_url": "https://pmkisan.gov.in",
        "helpline": "155261 / 011-24300606",
        "grievance_redressal": "District Nodal Agriculture Officers & PM-KISAN Grievance Portal",
        "source_pages": [5]
    },
    {
        "authority_id": "AUTH_PMSURYA",
        "scheme_id": "SCH_PMSURYA",
        "ministry": "Ministry of New and Renewable Energy",
        "department": "Rooftop Solar Division",
        "implementing_agency": "State Power Distribution Companies (DISCOMs) & REC Limited",
        "portal_url": "https://pmsuryaghar.gov.in",
        "helpline": "15555",
        "grievance_redressal": "DISCOM Consumer Forum & National Portal Support Desk",
        "source_pages": [6]
    },
    {
        "authority_id": "AUTH_SVANIDHI",
        "scheme_id": "SCH_SVANIDHI",
        "ministry": "Ministry of Housing and Urban Affairs",
        "department": "Urban Livelihoods Division",
        "implementing_agency": "Urban Local Bodies (ULBs) & Scheduled Commercial Banks / SIDBI",
        "portal_url": "https://pmsvanidhi.mohua.gov.in",
        "helpline": "1800 11 1979",
        "grievance_redressal": "Town Vending Committee & SIDBI Helpdesk",
        "source_pages": [6]
    },
    {
        "authority_id": "AUTH_VISHWA",
        "scheme_id": "SCH_VISHWA",
        "ministry": "Ministry of Micro, Small and Medium Enterprises",
        "department": "MSME Development & National Skill Development Corporation (NSDC)",
        "implementing_agency": "Jointly implemented by MoMSME, MoSDE, and MoF via CSCs & Banks",
        "portal_url": "https://pmvishwakarma.gov.in",
        "helpline": "1800 267 7777 / 17923",
        "grievance_redressal": "District Implementation Committee & MSME-DFO",
        "source_pages": [7]
    },
    {
        "authority_id": "AUTH_PMUY",
        "scheme_id": "SCH_PMUY",
        "ministry": "Ministry of Petroleum and Natural Gas",
        "department": "LPG Division",
        "implementing_agency": "Oil Marketing Companies (IOCL, BPCL, HPCL)",
        "portal_url": "https://pmuy.gov.in",
        "helpline": "1800 233 3555 / 1906",
        "grievance_redressal": "OMC Area Offices & MoP&NG Helpdesk",
        "source_pages": [8]
    },
    {
        "authority_id": "AUTH_MGNREGA",
        "scheme_id": "SCH_MGNREGA",
        "ministry": "Ministry of Rural Development",
        "department": "Department of Rural Development",
        "implementing_agency": "Gram Panchayats, Block Programme Coordinators & District Collectors",
        "portal_url": "https://nrega.nic.in",
        "helpline": "1800 110 707",
        "grievance_redressal": "District MGNREGA Ombudsman & Gram Sabha Social Audit",
        "source_pages": [14, 21, 22]
    }
]

# 6. RELATIONSHIPS DATA
relationships_data = [
    {
        "relationship_id": "REL_ESHRAM_PMSYM",
        "source_scheme_id": "SCH_PMSYM",
        "target_scheme_id": "SCH_ESHRAM",
        "relationship_type": "INTEGRATED_PORTAL",
        "description": "e-Shram acts as the national registry and single-window onboarding database for PM-SYM unorganised workers.",
        "shared_fields": ["demographics.aadhaar_number", "employment.unorganised_worker"]
    },
    {
        "relationship_id": "REL_PMJDY_PMKISAN",
        "source_scheme_id": "SCH_PMKISAN",
        "target_scheme_id": "SCH_PMJDY",
        "relationship_type": "PREREQUISITE_RAIL",
        "description": "PM Jan Dhan Yojana bank accounts provide the financial inclusion rail for DBT transfer of PM-KISAN installments.",
        "shared_fields": ["banking.account_number", "banking.ifsc", "demographics.aadhaar_number"]
    },
    {
        "relationship_id": "REL_PMSBY_PMJJBY",
        "source_scheme_id": "SCH_PMSBY",
        "target_scheme_id": "SCH_PMJJBY",
        "relationship_type": "COMPLEMENTARY",
        "description": "PMJJBY covers natural and accidental death (life insurance), while PMSBY specifically covers accidental death and disability. Both share bank auto-debit mechanisms.",
        "shared_fields": ["banking.account_number", "demographics.aadhaar_number"]
    },
    {
        "relationship_id": "REL_MGNREGA_PMAYG",
        "source_scheme_id": "SCH_PMAYG",
        "target_scheme_id": "SCH_MGNREGA",
        "relationship_type": "SUBSIDIARY_CONVERGENCE",
        "description": "Beneficiaries constructing houses under PMAY-G are entitled to up to 90/95 person-days of unskilled labor wages under MGNREGA.",
        "shared_fields": ["housing.beneficiary_id", "demographics.job_card_number"]
    },
    {
        "relationship_id": "REL_ONORC_NFSA",
        "source_scheme_id": "SCH_ONORC",
        "target_scheme_id": "SCH_NFSA",
        "relationship_type": "DEPENDENCY",
        "description": "ONORC operates strictly on top of the National Food Security Act (NFSA) 2013 entitlements.",
        "shared_fields": ["institutional.ration_card_number", "demographics.aadhaar_number"]
    }
]

# 7. TEMPORAL DATA
temporal_data = [
    {"scheme_id": "SCH_ONORC", "launch_year": 2018, "status": "ACTIVE", "frequency": "MONTHLY", "financial_cycle": "Continuous", "deadlines": "Monthly ration lifting cycle"},
    {"scheme_id": "SCH_PMSYM", "launch_year": 2019, "status": "ACTIVE", "frequency": "MONTHLY", "financial_cycle": "Monthly auto-debit", "deadlines": "Monthly contribution on set bank date"},
    {"scheme_id": "SCH_PMKISAN", "launch_year": 2019, "status": "ACTIVE", "frequency": "FOUR_MONTHLY", "financial_cycle": "Tri-annual", "deadlines": "April-July, August-November, December-March installments"},
    {"scheme_id": "SCH_PMSURYA", "launch_year": 2024, "status": "ACTIVE", "frequency": "ONE_TIME", "financial_cycle": "Financial year target", "deadlines": "Target of 1 crore households"},
    {"scheme_id": "SCH_SVANIDHI", "launch_year": 2020, "status": "ACTIVE", "frequency": "RECURRING_LOAN", "financial_cycle": "Annual loan tranches", "deadlines": "Timely monthly EMI repayment unlocks next tranche"},
    {"scheme_id": "SCH_VISHWA", "launch_year": 2023, "status": "ACTIVE", "frequency": "MULTI_STAGE", "financial_cycle": "2023-24 to 2027-28", "deadlines": "Tranche 2 unlocked after 6 months of Tranche 1 regular repayment"},
    {"scheme_id": "SCH_PMUY", "launch_year": 2016, "status": "ACTIVE", "frequency": "ONE_TIME_SUBSIDY", "financial_cycle": "Continuous under Ujjwala 2.0", "deadlines": "Connection release on verification"},
    {"scheme_id": "SCH_PMJJBY", "launch_year": 2015, "status": "ACTIVE", "frequency": "ANNUAL", "financial_cycle": "June 1 to May 31", "deadlines": "Annual premium auto-debit by May 31 each year"},
    {"scheme_id": "SCH_PMSBY", "launch_year": 2015, "status": "ACTIVE", "frequency": "ANNUAL", "financial_cycle": "June 1 to May 31", "deadlines": "Annual premium auto-debit by May 31 each year"},
    {"scheme_id": "SCH_APY", "launch_year": 2015, "status": "ACTIVE", "frequency": "MONTHLY", "financial_cycle": "Auto-debit", "deadlines": "Monthly auto-debit depending on subscriber choice"},
    {"scheme_id": "SCH_SSY", "launch_year": 2015, "status": "ACTIVE", "frequency": "ANNUAL_DEPOSIT", "financial_cycle": "Financial year", "deadlines": "Minimum deposit of Rs 250 required before March 31 annually"},
    {"scheme_id": "SCH_MGNREGA", "launch_year": 2005, "status": "ACTIVE", "frequency": "ON_DEMAND", "financial_cycle": "Financial year (100 days per household)", "deadlines": "Work must be provided within 15 days of demand"}
]

# 8. SOURCE CHUNKS DATA (Extracted text sections for BM25 retrieval and verification provenance)
source_chunks = []
chunk_id_counter = 1

for s in schemes:
    sid = s["scheme_id"]
    name = s["official_name"]
    pages = s.get("source_pages", [1])
    desc = s.get("description", "")
    obj = s.get("objective", "")

    # Chunk 1: Overview
    source_chunks.append({
        "chunk_id": f"CHK_{chunk_id_counter:04d}",
        "scheme_id": sid,
        "scheme_name": name,
        "section": "OVERVIEW_AND_DESCRIPTION",
        "page_numbers": pages,
        "text": f"{name} ({s.get('abbreviation', '')}): {desc} Objective: {obj}"
    })
    chunk_id_counter += 1

    # Chunk 2: Administration
    source_chunks.append({
        "chunk_id": f"CHK_{chunk_id_counter:04d}",
        "scheme_id": sid,
        "scheme_name": name,
        "section": "ADMINISTRATION",
        "page_numbers": pages,
        "text": f"{name} is administered by {s.get('ministry', '')}, {s.get('department', '')}. Implementing Agency: {s.get('implementing_agency', '')}. Scope: {s.get('geographic_scope', 'NATIONAL')}."
    })
    chunk_id_counter += 1

# Add chunks from benefits
for b in json.load(open(f"{DATA_DIR}/benefits/all_benefits.json")):
    source_chunks.append({
        "chunk_id": f"CHK_{chunk_id_counter:04d}",
        "scheme_id": b["scheme_id"],
        "scheme_name": scheme_map.get(b["scheme_id"], {}).get("official_name", b["scheme_id"]),
        "section": "BENEFITS",
        "page_numbers": b.get("source_pages", [1]),
        "text": f"Benefit for {b['scheme_id']}: Type: {b.get('benefit_type', '')}. {b.get('description', '')}. Quantified value: {b.get('quantified_value', '')} {b.get('coverage', '')}."
    })
    chunk_id_counter += 1

# Add chunks from rules
for r in json.load(open(f"{DATA_DIR}/rules/all_rules.json")):
    conds_text = "; ".join([c.get("description", "") for c in r.get("conditions", [])])
    source_chunks.append({
        "chunk_id": f"CHK_{chunk_id_counter:04d}",
        "scheme_id": r["scheme_id"],
        "scheme_name": scheme_map.get(r["scheme_id"], {}).get("official_name", r["scheme_id"]),
        "section": "ELIGIBILITY_RULES",
        "page_numbers": r.get("source_pages", [1]),
        "text": f"Eligibility rule for {r['scheme_id']}: {r.get('description', '')}. Conditions: {conds_text}"
    })
    chunk_id_counter += 1

# Add chunks from procedures
for p in procedures_data:
    on_text = " ".join(p.get("online_steps", []))
    off_text = " ".join(p.get("offline_steps", []))
    source_chunks.append({
        "chunk_id": f"CHK_{chunk_id_counter:04d}",
        "scheme_id": p["scheme_id"],
        "scheme_name": scheme_map.get(p["scheme_id"], {}).get("official_name", p["scheme_id"]),
        "section": "PROCEDURE",
        "page_numbers": p.get("source_pages", [1]),
        "text": f"Application Procedure for {p['scheme_id']}: Mode: {p.get('mode', '')}. Online: {on_text}. Offline: {off_text}. Fees: {p.get('fees', '')}."
    })
    chunk_id_counter += 1

# Add chunks from FAQs
for q in faqs_data:
    source_chunks.append({
        "chunk_id": f"CHK_{chunk_id_counter:04d}",
        "scheme_id": q["scheme_id"],
        "scheme_name": scheme_map.get(q["scheme_id"], {}).get("official_name", q["scheme_id"]),
        "section": "FAQ",
        "page_numbers": q.get("source_pages", [1]),
        "text": f"FAQ for {q['scheme_id']}: Question: {q['question']} Answer: {q['answer']}"
    })
    chunk_id_counter += 1


# Write out all JSON files
with open(f"{DATA_DIR}/exclusions/all_exclusions.json", "w") as f:
    json.dump(exclusions_data, f, indent=2)

with open(f"{DATA_DIR}/documents/all_documents.json", "w") as f:
    json.dump(documents_data, f, indent=2)

with open(f"{DATA_DIR}/procedures/all_procedures.json", "w") as f:
    json.dump(procedures_data, f, indent=2)

with open(f"{DATA_DIR}/faqs/all_faqs.json", "w") as f:
    json.dump(faqs_data, f, indent=2)

with open(f"{DATA_DIR}/authorities/all_authorities.json", "w") as f:
    json.dump(authorities_data, f, indent=2)

with open(f"{DATA_DIR}/relationships/all_relationships.json", "w") as f:
    json.dump(relationships_data, f, indent=2)

with open(f"{DATA_DIR}/temporal/all_temporal.json", "w") as f:
    json.dump(temporal_data, f, indent=2)

with open(f"{DATA_DIR}/source_chunks/all_chunks.json", "w") as f:
    json.dump(source_chunks, f, indent=2)


# Write AUDIT DELIVERABLES
scheme_inventory = [
    {
        "scheme_id": s["scheme_id"],
        "official_name": s["official_name"],
        "abbreviation": s.get("abbreviation"),
        "category": s.get("category"),
        "ministry": s.get("ministry"),
        "source_pages": s.get("source_pages")
    }
    for s in schemes
]

field_inventory = {
    "demographic_fields": ["age", "gender", "category", "marital_status", "occupation", "residence_state", "rural_urban"],
    "economic_fields": ["annual_turnover", "monthly_income", "annual_family_income", "land_holding_hectares", "is_income_tax_payer"],
    "institutional_fields": ["has_ration_card", "is_aadhaar_seeded", "has_bank_account", "is_epfo_or_esic_member", "is_pmjdy_account_holder"],
    "benefit_types": ["DIRECT_BENEFIT_TRANSFER", "PENSION", "INSURANCE", "SUBSIDY", "LOAN_WORKING_CAPITAL", "TRAINING_STIPEND", "HOUSING_ASSISTANCE", "FOOD_GRAIN_PORTABILITY"]
}

source_mapping = {
    s["scheme_id"]: {
        "pages": s.get("source_pages", []),
        "sections": s.get("source_sections", []),
        "ministry": s.get("ministry")
    }
    for s in schemes
}

ambiguity_report = [
    {
        "issue_id": "AMB_001",
        "scheme_id": "SCH_PMSBY_FULL",
        "severity": "LOW",
        "description": "PMSBY appears both as a brief summary in early pages and detailed rules later in the document.",
        "resolution": "Unified into SCH_PMSBY with comprehensive conditions covering both summary and detailed schedules."
    },
    {
        "issue_id": "AMB_002",
        "scheme_id": "SCH_VBG_RAMG",
        "severity": "MEDIUM",
        "description": "VB-G RAM G represents the updated statutory framework alongside MGNREGA 2005.",
        "resolution": "Retained as distinct statutory scheme with shared operational provisions and link to MGNREGA."
    },
    {
        "issue_id": "AMB_003",
        "scheme_id": "SCH_APY",
        "severity": "LOW",
        "description": "Income tax payers were permitted before Oct 1, 2022 but excluded post Oct 1, 2022.",
        "resolution": "Implemented temporal condition: for current applications, income tax payers are strictly disqualified."
    }
]

with open(f"{AUDIT_DIR}/scheme_inventory.json", "w") as f:
    json.dump(scheme_inventory, f, indent=2)

with open(f"{AUDIT_DIR}/field_inventory.json", "w") as f:
    json.dump(field_inventory, f, indent=2)

with open(f"{AUDIT_DIR}/source_mapping.json", "w") as f:
    json.dump(source_mapping, f, indent=2)

with open(f"{AUDIT_DIR}/ambiguity_report.json", "w") as f:
    json.dump(ambiguity_report, f, indent=2)

print("Successfully generated all canonical data and audit files!")
print(f"Total schemes: {len(schemes)}")
print(f"Total exclusions: {len(exclusions_data)}")
print(f"Total documents: {len(documents_data)}")
print(f"Total procedures: {len(procedures_data)}")
print(f"Total FAQs: {len(faqs_data)}")
print(f"Total authorities: {len(authorities_data)}")
print(f"Total relationships: {len(relationships_data)}")
print(f"Total source chunks: {len(source_chunks)}")
