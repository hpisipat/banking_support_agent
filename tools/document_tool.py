# tools/document_tool.py
# Feature 1 — Document Checklist & Process Guide
# Uses LLM with full chat_history for context-aware responses
# Falls back to hardcoded data for accurate structured output

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from observability.logger import log_info, log_warning

# ── Document Checklists ───────────────────────────────────────────────────────

DOCUMENT_CHECKLISTS = {

    "savings_account": {
        "title"    : "Savings Account Opening",
        "category" : "Account Opening",
        "documents": [
            "Aadhaar card — original and photocopy",
            "PAN card — mandatory for all accounts",
            "Recent passport size photograph — 2 copies",
            "Address proof if different from Aadhaar (utility bill, rent agreement)",
            "Initial deposit amount — minimum Rs.1,000 for urban branches"
        ]
    },
    "current_account": {
        "title"    : "Current Account Opening",
        "category" : "Account Opening",
        "documents": [
            "Aadhaar card — original and photocopy",
            "PAN card — mandatory",
            "Business registration certificate",
            "GST registration certificate (if applicable)",
            "Address proof of business premises",
            "Partnership deed / MOA / AOA (for firms and companies)",
            "Recent passport size photograph — 2 copies",
            "Initial deposit — minimum Rs.10,000"
        ]
    },
    "joint_account": {
        "title"    : "Joint Account Opening",
        "category" : "Account Opening",
        "documents": [
            "Aadhaar card of ALL account holders — original and photocopy",
            "PAN card of ALL account holders — mandatory",
            "Recent passport size photograph — 2 copies per holder",
            "Address proof of primary account holder",
            "Joint account mandate form — Either or Survivor / Jointly",
            "Initial deposit — minimum Rs.1,000"
        ]
    },
    "nri_account": {
        "title"    : "NRI Account Opening",
        "category" : "Account Opening",
        "documents": [
            "Valid Indian passport — original and photocopy",
            "Valid visa / OCI card / PIO card",
            "Overseas address proof (bank statement / utility bill)",
            "PAN card or Form 60 (if no PAN)",
            "Recent passport size photograph — 2 copies",
            "FEMA declaration form",
            "Initial deposit — minimum Rs.10,000 (NRE/NRO)"
        ]
    },
    "ppf_account": {
        "title"    : "PPF Account Opening",
        "category" : "Account Opening",
        "documents": [
            "Aadhaar card — original and photocopy",
            "PAN card — mandatory",
            "Recent passport size photograph — 2 copies",
            "PPF account opening form (Form A)",
            "Nomination form",
            "Initial deposit — minimum Rs.500"
        ]
    },
    "fixed_deposit": {
        "title"    : "Fixed Deposit",
        "category" : "Account Opening",
        "documents": [
            "Aadhaar card — original and photocopy",
            "PAN card — mandatory for deposits above Rs.50,000",
            "Existing savings account (linked for FD)",
            "Nomination form",
            "FD application form"
        ]
    },
    "demat_account": {
        "title"    : "Demat Account Opening",
        "category" : "Investments & Trading",
        "documents": [
            "Aadhaar card — original and photocopy",
            "PAN card — mandatory",
            "Bank account proof (cancelled cheque with name printed)",
            "Recent passport size photograph — 2 copies",
            "Income proof for F&O trading (salary slip / ITR)",
            "In-person verification (IPV) required"
        ]
    },
    "personal_loan": {
        "title"    : "Personal Loan",
        "category" : "Loans",
        "documents": {
            "salaried": [
                "Aadhaar card + PAN card",
                "Last 3 months salary slips",
                "Last 6 months bank statements",
                "Form 16 or latest ITR",
                "Employment letter / offer letter",
                "Passport size photograph — 2 copies"
            ],
            "self_employed": [
                "Aadhaar card + PAN card",
                "Last 2 years ITR with computation",
                "Last 6 months bank statements",
                "Business registration proof",
                "GST returns (last 6 months)",
                "Passport size photograph — 2 copies"
            ]
        }
    },
    "home_loan": {
        "title"    : "Home Loan",
        "category" : "Loans",
        "documents": {
            "salaried": [
                "Aadhaar card + PAN card",
                "Last 3 months salary slips",
                "Last 12 months bank statements",
                "Form 16 for last 2 years",
                "Property documents — sale deed / agreement to sell",
                "Property valuation report",
                "NOC from builder / society",
                "Passport size photograph — 2 copies"
            ],
            "self_employed": [
                "Aadhaar card + PAN card",
                "Last 3 years ITR with CA certification",
                "Last 12 months bank statements",
                "Business registration + GST certificate",
                "Property documents — sale deed / agreement to sell",
                "Property valuation report",
                "Passport size photograph — 2 copies"
            ]
        }
    },
    "car_loan": {
        "title"    : "Car Loan",
        "category" : "Loans",
        "documents": {
            "salaried": [
                "Aadhaar card + PAN card",
                "Last 3 months salary slips",
                "Last 6 months bank statements",
                "Car proforma invoice from dealer",
                "Passport size photograph — 2 copies"
            ],
            "self_employed": [
                "Aadhaar card + PAN card",
                "Last 2 years ITR",
                "Last 6 months bank statements",
                "Business registration proof",
                "Car proforma invoice from dealer",
                "Passport size photograph — 2 copies"
            ]
        }
    },
    "education_loan": {
        "title"    : "Education Loan",
        "category" : "Loans",
        "documents": [
            "Student Aadhaar card + PAN card",
            "Co-applicant Aadhaar card + PAN card",
            "Admission letter from institution",
            "Fee structure from institution",
            "Mark sheets — 10th, 12th, graduation (if applicable)",
            "Co-applicant last 3 months salary slips / ITR",
            "Co-applicant last 6 months bank statements",
            "Passport size photograph — 2 copies each"
        ]
    },
    "credit_card": {
        "title"    : "Credit Card",
        "category" : "Cards",
        "documents": {
            "salaried": [
                "Aadhaar card + PAN card",
                "Last 3 months salary slips",
                "Last 3 months bank statements",
                "Passport size photograph — 1 copy"
            ],
            "self_employed": [
                "Aadhaar card + PAN card",
                "Last year ITR",
                "Last 3 months bank statements",
                "Business registration proof",
                "Passport size photograph — 1 copy"
            ]
        }
    }
}

PROCESS_GUIDES = {
    "net_banking": {
        "title"   : "Enable Net Banking / Online Banking",
        "channel" : "Branch + Online",
        "steps"   : [
            "Visit your home branch with Aadhaar card and PAN card",
            "Fill the Net Banking Registration form at the branch",
            "Collect your temporary User ID and Password",
            "Visit www.bank.com and click on 'First Time Login'",
            "Enter temporary User ID and Password",
            "Set a new strong password",
            "Set 3 security questions for account recovery",
            "Net banking is now active"
        ]
    },
    "third_party_transfer": {
        "title"   : "Enable Third Party Transfer (TPT)",
        "channel" : "Net Banking",
        "steps"   : [
            "Login to net banking at www.bank.com",
            "Go to 'Settings' → 'Transfer Settings'",
            "Click on 'Enable Third Party Transfer'",
            "Enter your net banking transaction password",
            "Enter the OTP sent to your registered mobile",
            "Third party transfer is now enabled",
            "Daily limit is Rs.2,00,000 by default"
        ]
    },
    "reset_password": {
        "title"   : "Reset Net Banking Password",
        "channel" : "Online / Branch",
        "steps"   : [
            "Go to www.bank.com and click 'Forgot Password'",
            "Enter your User ID and registered mobile number",
            "Enter the OTP sent to your mobile within 5 minutes",
            "Set a new strong password",
            "Login with your new password"
        ]
    },
    "reset_upi_pin": {
        "title"   : "Reset UPI PIN",
        "channel" : "Mobile Banking App",
        "steps"   : [
            "Open your UPI app (BHIM / PhonePe / GPay etc.)",
            "Go to 'Profile' or 'Settings'",
            "Select your bank account",
            "Tap 'Forgot UPI PIN' or 'Reset PIN'",
            "Enter your debit card last 6 digits and expiry date",
            "Enter the OTP sent to your registered mobile",
            "Set a new 4 or 6 digit UPI PIN"
        ]
    },
    "international_transactions": {
        "title"   : "Enable / Disable International Transactions",
        "channel" : "Net Banking / Mobile App / Branch",
        "steps"   : [
            "Login to net banking or mobile banking app",
            "Go to 'Cards' → select your Debit or Credit Card",
            "Click on 'Card Settings' or 'Manage Card'",
            "Toggle 'International Transactions' ON or OFF",
            "Confirm with OTP sent to registered mobile",
            "Change takes effect immediately"
        ]
    },
    "block_card": {
        "title"   : "Block / Unblock Debit Card",
        "channel" : "Net Banking / Mobile App / Helpline",
        "steps"   : [
            "IMMEDIATE BLOCK: Call 1800-XXX-XXXX (24/7 available)",
            "Or login to net banking → Cards → Block Card",
            "Or open mobile app → Cards → Block/Unblock",
            "Select card and confirm block with OTP",
            "Card is blocked immediately",
            "To unblock: Net banking → Cards → Unblock Card"
        ]
    },
    "link_aadhaar": {
        "title"   : "Link Aadhaar to Bank Account",
        "channel" : "Net Banking / ATM / Branch / Mobile App",
        "steps"   : [
            "Method 1 — Net Banking: Login → My Account → Link Aadhaar → OTP",
            "Method 2 — Mobile App: Profile → Link Aadhaar → OTP",
            "Method 3 — ATM: More Options → Aadhaar Seeding",
            "Method 4 — Branch: Submit Aadhaar photocopy with account number",
            "Linking completed within 24 hours"
        ]
    }
}


# ── Main function — LLM with chat_history ─────────────────────────────────────

def get_document_checklist(user_message, persona="existing_customer",
                           session_id="SYSTEM", chat_history=[],
                           feedback_style="default", user_id=None):
    """
    Uses LLM with full chat_history for context-aware responses.
    LangChain handles context automatically — no manual string joining.
    Provides document checklists and process guides from hardcoded data.
    """
    from core.llm_agent import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage
    from tools.feedback_tool import get_style_guidance

    log_info(session_id, persona, "document_tool_called", user_message)

    style_guidance = get_style_guidance(
        feedback_style,
        persona,
        user_id=user_id
    )

    # Build data context string for LLM
    services_list = "\n".join([
        f"  - {v['title']}"
        for k, v in DOCUMENT_CHECKLISTS.items()
    ])

    processes_list = "\n".join([
        f"  - {v['title']}"
        for k, v in PROCESS_GUIDES.items()
    ])

    # Full document data as string for LLM reference
    import json
    checklists_data = {}
    for k, v in DOCUMENT_CHECKLISTS.items():
        docs = v["documents"]
        if isinstance(docs, dict):
            checklists_data[v["title"]] = {
                "salaried"     : docs.get("salaried", []),
                "self_employed": docs.get("self_employed", [])
            }
        else:
            checklists_data[v["title"]] = docs

    processes_data = {
        v["title"]: v["steps"]
        for k, v in PROCESS_GUIDES.items()
    }

    system_prompt = f"""
    You are a banking document assistant for a leading Indian bank.
    {style_guidance}
    PERSONA: {persona.replace('_', ' ').title()}
    {"Use simple friendly language." if persona == "new_customer" else ""}
    {"Be formal and precise." if persona == "banker" else ""}

    YOUR JOB:
    - Help customers find what documents they need
    - Help customers with step-by-step process guides
    - Use ONLY the data provided below — do not make up documents
    - If service is unclear — ask which service they need
    - If loan/card — ask if salaried or self-employed
    - For follow-up questions — use conversation context

    IMPORTANT — PRODUCT ENQUIRY HANDLING:
    When a customer says they want a loan or credit card
    (e.g. "I want a credit card", "I want a home loan"):
    → FIRST ask: "Would you like to:
    1. Check if you are eligible?
    2. Get the list of documents needed?
    
    Please let me know and I'll help you right away!"

    Only proceed with documents AFTER customer confirms they want docs.
    If they say "eligibility" or "check eligibility" — 
    tell them: "Let me check your eligibility!" and ask for their details.


    AVAILABLE SERVICES:
{services_list}

    AVAILABLE PROCESS GUIDES:
{processes_list}

    DOCUMENT DATA (use exactly as provided):
    {json.dumps(checklists_data, indent=2)}

    PROCESS DATA (use exactly as provided):
    {json.dumps(processes_data, indent=2)}

    FORMAT RULES:
    - Number all documents clearly
    - Add tip about carrying originals and photocopies
    - For loans/cards — show correct list based on employment type
    - For processes — show numbered steps clearly
    """

    llm      = get_llm()
    messages = [SystemMessage(content=system_prompt)]

    # Add full chat history — LangChain manages context automatically
    for msg in chat_history:
        messages.append(msg)

    # Add current message
    messages.append(HumanMessage(content=user_message))

    response = llm.invoke(messages)

    log_info(session_id, persona,
             "document_tool_response",
             f"length={len(response.content)}")

    return response.content
