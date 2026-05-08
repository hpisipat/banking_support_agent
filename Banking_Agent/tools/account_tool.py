# tools/account_tool.py
# Feature 6 — Account Inquiry (Mock Data)
# Uses LLM with chat_history to extract customer ID and mobile naturally

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from observability.logger import log_info, log_warning, log_error
from data.mock_accounts   import MOCK_CUSTOMERS, MOCK_STAFF

AUTH_FAILURES = {}
MAX_AUTH_RETRIES = 3


def mask_account_number(n):
    return f"XXXX XXXX {n[-4:]}" if len(n) >= 4 else "XXXX"

def mask_mobile(m):
    return f"XXXXXX{m[-4:]}" if len(m) >= 4 else "XXXXXX"

def mask_email(e):
    if "@" not in e: return e
    local, domain = e.split("@", 1)
    if len(local) <= 2: return f"{local[0]}*@{domain}"
    return f"{local[0]}{'*'*(len(local)-2)}{local[-1]}@{domain}"


def extract_credentials_from_conversation(user_message, chat_history):
    """
    LLM extracts customer ID and mobile from full conversation.
    Handles any phrasing — no regex needed.
    """
    from core.llm_agent import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage
    import json

    llm    = get_llm()
    prompt = f"""
    Extract authentication details from this banking conversation.

    Reply ONLY with valid JSON:
    {{
        "customer_id"  : "CUST-XXXXX or null",
        "mobile"       : "10 digit mobile number or null",
        "employee_id"  : "EMP-XXXX or null"
    }}

    Return null for anything not clearly mentioned.
    """

    messages = [SystemMessage(content=prompt)]
    for msg in chat_history[-6:]:
        messages.append(msg)
    messages.append(HumanMessage(content=user_message))

    try:
        response = llm.invoke(messages)
        text     = response.content.strip()
        text     = text.replace("```json","").replace("```","").strip()
        data     = json.loads(text)
        return (data.get("customer_id"),
                data.get("mobile"),
                data.get("employee_id"))
    except Exception:
        return None, None, None


def verify_customer(customer_id, mobile, session_id="SYSTEM"):
    failures = AUTH_FAILURES.get(session_id, 0)
    if failures >= MAX_AUTH_RETRIES:
        log_error(session_id, "existing_customer", "auth_session_locked",
                  f"attempts={failures}")
        return False, ("🔒 Session locked due to multiple failed attempts.\n"
                       "   Please visit your nearest branch with Aadhaar.")

    customer = MOCK_CUSTOMERS.get(customer_id)
    if not customer:
        AUTH_FAILURES[session_id] = failures + 1
        remaining = MAX_AUTH_RETRIES - AUTH_FAILURES[session_id]
        log_warning(session_id, "existing_customer", "auth_not_found",
                    "customer_id=[REDACTED]")
        return False, (f"❌ No account found with that Customer ID.\n"
                       f"   ({remaining} attempt(s) remaining)")

    if customer["mobile"] != mobile:
        AUTH_FAILURES[session_id] = failures + 1
        remaining = MAX_AUTH_RETRIES - AUTH_FAILURES[session_id]
        log_warning(session_id, "existing_customer", "auth_mobile_mismatch",
                    f"attempts={AUTH_FAILURES[session_id]}")
        if AUTH_FAILURES[session_id] >= MAX_AUTH_RETRIES:
            return False, ("🔒 Too many failed attempts. Session locked.\n"
                           "   Please visit your nearest branch.")
        return False, (f"❌ Details don't match our records.\n"
                       f"   ({remaining} attempt(s) remaining)")

    AUTH_FAILURES[session_id] = 0
    log_info(session_id, "existing_customer", "auth_success", "verified")
    return True, customer


def verify_banker(employee_id, session_id="SYSTEM"):
    staff = MOCK_STAFF.get(employee_id)
    if not staff:
        log_warning(session_id, "banker", "banker_auth_failed",
                    "employee_id=[REDACTED]")
        return False, "❌ Invalid Employee ID. Please verify and try again."
    log_info(session_id, "banker", "banker_auth_success",
             f"role={staff['role']}")
    return True, staff


# ── Main function ─────────────────────────────────────────────────────────────

def get_account_details(user_message, persona="existing_customer",
                        customer_id=None, mobile=None,
                        employee_id=None, session_id="SYSTEM",
                        chat_history=[]):
    """
    Returns account details based on persona.
    LLM extracts credentials from full conversation context.
    """

    log_info(session_id, persona, "account_tool_called", user_message)

    # New customer — no account
    if persona == "new_customer":
        log_info(session_id, persona, "account_new_customer_redirect", "")
        return ("As a new customer you don't have an account yet.\n\n"
                "   Would you like to open one? I can help with:\n"
                "   • Documents needed\n"
                "   • Types of accounts available\n"
                "   • Nearest branch to visit\n\n"
                "   Just say 'I want to open an account'!")

    # LLM extracts credentials if not already passed
    if not customer_id or (persona == "existing_customer" and not mobile):
        llm_cust, llm_mobile, llm_emp = extract_credentials_from_conversation(
            user_message, chat_history
        )
        customer_id  = customer_id  or llm_cust
        mobile       = mobile       or llm_mobile
        employee_id  = employee_id  or llm_emp

    # Existing customer flow
    if persona == "existing_customer":
        if not customer_id:
            return ("To view account details, I'll need to verify your identity.\n\n"
                    "   Please share:\n"
                    "   • Customer ID (found on passbook or welcome letter)\n"
                    "   • Registered mobile number")

        if not mobile:
            return ("Please also share your registered mobile number "
                    "along with your Customer ID for verification.")

        success, result = verify_customer(customer_id, mobile, session_id)
        if not success:
            return result
        return format_customer_view(result, session_id)

    # Banker flow
    if persona == "banker":
        if not employee_id:
            return "Please provide your Employee ID to proceed."

        success, staff = verify_banker(employee_id, session_id)
        if not success:
            return staff

        if not customer_id:
            return "Please provide the Customer ID to look up."

        customer = MOCK_CUSTOMERS.get(customer_id)
        if not customer:
            return (f"No customer found with ID: {customer_id}. "
                    f"Please verify and try again.")

        return format_banker_view(customer, staff, session_id)

    return "Unable to process. Please try again."


def format_customer_view(customer, session_id):
    account  = customer["account"]
    products = customer["linked_products"]
    status   = account["status"]

    status_icons = {
        "Active": "✅ Active", "Dormant": "😴 Dormant",
        "Frozen": "🔒 Frozen", "Closed": "❌ Closed"
    }

    kyc_display = ("✅ Verified" if customer["kyc_status"] == "Verified"
                   else "⚠️ Expired")
    kyc_alert   = ""
    if customer["kyc_status"] == "Expired":
        kyc_alert = ("\n\n   ⚠️  URGENT: KYC expired! "
                     "Please visit nearest branch to renew.")

    loans_s = "".join([f"\n       • {l['type']} — Rs.{l['amount']:,} ({l['status']})"
                       for l in products.get("loans", [])])
    cards_s = "".join([f"\n       • {c['type']} — {c['status']}"
                       for c in products.get("cards", [])])
    deps_s  = "".join([f"\n       • {d['type']} — Rs.{d['amount']:,} (Matures: {d['maturity']})"
                       for d in products.get("deposits", [])])

    response = (f"👤 Account Details\n{'='*45}\n"
                f"Name              : {customer['name']}\n"
                f"Customer ID       : {customer['customer_id']}\n"
                f"Account Number    : {mask_account_number(account['account_number'])}\n"
                f"Account Type      : {account['account_type']}\n"
                f"Account Status    : {status_icons.get(status, status)}\n"
                f"Opening Date      : {account['opening_date']}\n"
                f"Branch            : {account['branch']}\n"
                f"IFSC Code         : {account['ifsc']}\n\n"
                f"KYC Status        : {kyc_display}\n"
                f"KYC Expiry        : {customer['kyc_expiry']}\n\n"
                f"Nominee           : {account['nominee']}\n\n"
                f"Registered Mobile : {mask_mobile(customer['mobile'])}\n"
                f"Registered Email  : {mask_email(customer['email'])}\n")

    if loans_s or cards_s or deps_s:
        response += "\n📦 Linked Products"
        if loans_s:    response += f"\n   Loans    :{loans_s}"
        if cards_s:    response += f"\n   Cards    :{cards_s}"
        if deps_s:     response += f"\n   Deposits :{deps_s}"

    if status == "Dormant":
        response += ("\n\n   😴 Account is dormant. Visit branch with "
                     "KYC documents to reactivate.")
    elif status == "Frozen":
        response += ("\n\n   🔒 Account is frozen. Contact branch immediately.")

    response += kyc_alert
    response += ("\n\n   ⚠️  For balance enquiry use:\n"
                 "   Net banking | Mobile app | ATM")

    log_info(session_id, "existing_customer", "account_details_returned",
             f"status={status}")
    return response


def format_banker_view(customer, staff, session_id):
    account  = customer["account"]
    products = customer["linked_products"]

    loans_s = "".join([f"\n   • {l['type']} — Rs.{l['amount']:,} | EMI: Rs.{l['emi']:,} | {l['status']}"
                       for l in products.get("loans", [])])
    cards_s = "".join([f"\n   • {c['type']} ({c['network']}) — {c['status']} | Exp: {c['expiry']}"
                       for c in products.get("cards", [])])
    deps_s  = "".join([f"\n   • {d['type']} — Rs.{d['amount']:,} @ {d['rate']}% | Matures: {d['maturity']}"
                       for d in products.get("deposits", [])])

    response = (f"CUSTOMER PROFILE — STAFF VIEW\n"
                f"Accessed by: {staff['name']} | {staff['branch']} Branch\n"
                f"{'='*50}\n"
                f"Customer ID    : {customer['customer_id']}\n"
                f"Full Name      : {customer['name']}\n"
                f"Date of Birth  : {customer['dob']}\n"
                f"Mobile         : {customer['mobile']}\n"
                f"Email          : {customer['email']}\n\n"
                f"Account Number : {account['account_number']}\n"
                f"Account Type   : {account['account_type']}\n"
                f"Status         : {account['status']}\n"
                f"Opening Date   : {account['opening_date']}\n"
                f"Branch         : {account['branch']}\n"
                f"IFSC           : {account['ifsc']}\n"
                f"Nominee        : {account['nominee']}\n\n"
                f"KYC Status     : {customer['kyc_status']}\n"
                f"KYC Expiry     : {customer['kyc_expiry']}\n"
                f"Segment        : {customer.get('segment','Regular')}\n"
                f"RM Assigned    : {customer.get('relationship_manager','N/A')}\n")

    if loans_s or cards_s or deps_s:
        response += "\nLinked Products"
        if loans_s: response += f"\nLoans    :{loans_s}"
        if cards_s: response += f"\nCards    :{cards_s}"
        if deps_s:  response += f"\nDeposits :{deps_s}"

    response += f"\n{'='*50}"

    log_info(session_id, "banker", "account_banker_view_returned",
             f"customer={customer['customer_id']}")
    return response
