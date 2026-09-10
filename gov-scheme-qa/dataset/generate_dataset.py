"""
Generates synthetic & pattern-expanded training dataset for intent classification.
All data is grounded in the scheme inventory and domain intents.
"""

import json
import random

DATA_FILE = "/home/sivaguru/Documents/slm/gov-scheme-qa/dataset/intent_dataset.json"

SCHEME_NAMES = [
    "ONORC", "One Nation One Ration Card", "PM-SYM", "Pradhan Mantri Shram Yogi Maan-Dhan",
    "NPS-Traders", "PMJJBY", "Jeevan Jyoti Bima", "PMSBY", "Suraksha Bima", "Atal Pension Yojana", "APY",
    "PM-KISAN", "Kisan Samman Nidhi", "PM Surya Ghar", "Muft Bijli", "PM SVANidhi", "Street Vendor Scheme",
    "PM Vishwakarma", "Ujjwala Yojana", "PMUY", "Mudra Yojana", "PMMY", "Fasal Bima Yojana", "PMFBY",
    "Sukanya Samriddhi", "SSY", "PMAY-G", "Gramin Awaas", "PM Jan Dhan", "PMJDY", "MGNREGA",
    "VB-G RAM G", "Kisan Mandhan", "PM-KMY", "DDU-GKY", "Garib Kalyan Rozgar", "GKRY", "DAY-NRLM",
    "PM Kaushal Vikas", "PMKVY", "NSAP", "Ayushman Bharat", "AB PM-JAY", "Weavers Health Insurance", "SRMS"
]

TEMPLATES_BY_INTENT = {
    "CHECK_ELIGIBILITY": [
        "Am I eligible for {scheme}?",
        "Can I apply for {scheme} if my age is 25 and income is 12000?",
        "Check my eligibility for {scheme}",
        "I am a {occupation}, do I qualify for {scheme}?",
        "I am 30 years old earning 10000 per month, am I eligible for {scheme}?",
        "Can a {occupation} get benefits under {scheme}?",
        "Do I qualify for {scheme} with 1.5 hectare land?",
        "Can women apply for {scheme}?",
        "I am 65 years old, can I join {scheme}?",
        "Check if I am eligible for {scheme} as an unorganised worker"
    ],
    "ELIGIBILITY": [
        "What is the eligibility criteria for {scheme}?",
        "Who is eligible for {scheme}?",
        "What are the age limits for {scheme}?",
        "Eligibility conditions for {scheme}",
        "What are the income criteria for {scheme}?",
        "Who can join {scheme}?",
        "What qualifications are needed for {scheme}?",
        "Tell me the eligibility rules for {scheme}",
        "Who is entitled to receive benefits under {scheme}?",
        "What are the terms and conditions to get {scheme}?"
    ],
    "BENEFITS": [
        "What are the benefits of {scheme}?",
        "How much money do I get under {scheme}?",
        "What financial assistance is provided by {scheme}?",
        "Benefits and coverage under {scheme}",
        "What is the pension amount in {scheme}?",
        "How much subsidy is given under {scheme}?",
        "Tell me about the coverage and benefits of {scheme}",
        "What do beneficiaries receive under {scheme}?",
        "What is the sum assured or insurance under {scheme}?",
        "What are the key advantages of {scheme}?"
    ],
    "DOCUMENTS": [
        "What documents are required for {scheme}?",
        "Documents needed to apply for {scheme}",
        "List of documents for {scheme}",
        "Do I need an Aadhaar card for {scheme}?",
        "What papers should I submit for {scheme}?",
        "Required documents checklist for {scheme}",
        "Which certificates are mandatory for {scheme}?",
        "Can I apply for {scheme} without ration card?",
        "What KYC documents are needed for {scheme}?",
        "Paperwork required for {scheme} application"
    ],
    "PROCEDURE": [
        "How to apply for {scheme}?",
        "What is the application process for {scheme}?",
        "Where can I apply for {scheme}?",
        "Can I apply online for {scheme}?",
        "Step by step registration process for {scheme}",
        "How do I enroll in {scheme}?",
        "What is the official portal to register for {scheme}?",
        "Offline application procedure for {scheme}",
        "How to register at CSC for {scheme}?",
        "Where do I submit the application form for {scheme}?"
    ],
    "EXCLUSIONS": [
        "Who is excluded from {scheme}?",
        "Who cannot apply for {scheme}?",
        "What are the disqualifications for {scheme}?",
        "Are income tax payers excluded from {scheme}?",
        "Can government employees get {scheme}?",
        "Who is not eligible for {scheme}?",
        "Exclusion list for {scheme}",
        "Disqualifying conditions for {scheme}",
        "Can EPFO members join {scheme}?",
        "Under what conditions is an applicant rejected for {scheme}?"
    ],
    "FAQ": [
        "Frequently asked questions about {scheme}",
        "Can my family claim benefits in another state under {scheme}?",
        "What happens if subscriber dies in {scheme}?",
        "Is eKYC mandatory for {scheme}?",
        "Common questions about {scheme}",
        "Can I change my nominee in {scheme}?",
        "What is the penalty for delayed payment in {scheme}?",
        "How to check status of my application in {scheme}?",
        "Can I exit {scheme} early?",
        "Queries and answers on {scheme}"
    ],
    "AUTHORITY": [
        "Which ministry runs {scheme}?",
        "Who is the implementing agency for {scheme}?",
        "Helpline number for {scheme}",
        "Toll free contact number for {scheme}",
        "Official website and portal for {scheme}",
        "Grievance redressal officer for {scheme}",
        "Department in charge of {scheme}",
        "Customer care phone number for {scheme}",
        "Where to file complaint about {scheme}?",
        "Who administers {scheme}?"
    ],
    "LIST_SCHEMES": [
        "List all government schemes",
        "What schemes are available?",
        "Show me all welfare schemes",
        "List schemes for farmers",
        "List pension schemes",
        "Which social security schemes are in the system?",
        "Show available schemes catalog",
        "Can you give me a list of all schemes?",
        "What government programmes can I view?",
        "Display all available central sector schemes"
    ],
    "OVERVIEW": [
        "What is {scheme}?",
        "Tell me about {scheme}",
        "Explain {scheme}",
        "Overview of {scheme}",
        "Give me information on {scheme}",
        "What is the objective of {scheme}?",
        "Background details of {scheme}",
        "When was {scheme} launched?",
        "Summary of {scheme}",
        "Introduction to {scheme}"
    ],
    "OUT_OF_SCOPE": [
        "What is the capital of France?",
        "Write a poem about the sunrise",
        "Who won the cricket world cup?",
        "What is quantum computing?",
        "Solve x^2 + 5x + 6 = 0",
        "Tell me a joke",
        "How do I book flight tickets to London?",
        "What is the weather in Delhi today?",
        "Recommend a good restaurant nearby",
        "How to write python code for bubble sort?"
    ]
}

OCCUPATIONS = ["farmer", "street vendor", "carpenter", "tailor", "weaver", "construction worker", "unorganised worker", "artisan", "small retailer"]

def generate_dataset():
    data = []
    for intent, templates in TEMPLATES_BY_INTENT.items():
        if intent == "LIST_SCHEMES" or intent == "OUT_OF_SCOPE":
            for t in templates:
                data.append({"query": t, "intent": intent})
                # Add slight variations
                data.append({"query": t.lower(), "intent": intent})
                data.append({"query": f"Please {t.lower()}", "intent": intent})
        else:
            for scheme in SCHEME_NAMES:
                for t in templates:
                    occ = random.choice(OCCUPATIONS)
                    q = t.format(scheme=scheme, occupation=occ)
                    data.append({"query": q, "intent": intent})

    random.seed(42)
    random.shuffle(data)

    print(f"Generated {len(data)} total labeled query samples across {len(TEMPLATES_BY_INTENT)} intents.")

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

    return data

if __name__ == "__main__":
    generate_dataset()
