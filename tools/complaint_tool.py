# tools/complaint_tool.py
# Feature 4 — Complaint / Ticket Logging
# Uses LLM with chat_history to collect complaint details conversationally

import os
import sys
import random
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from observability.logger import log_info, log_warning, log_error
from data.mock_tickets    import MOCK_TICKETS, MOCK_TICKETS_LIST
import json
TICKETS_FILE = "data/session_tickets_store.json"

SESSION_TICKETS = {}

PRIORITY_RULES = {
    "unauthorized_transaction" : {"priority": "Urgent", "sla_hours": 4},
    "card_cloned"              : {"priority": "Urgent", "sla_hours": 4},
    "failed_transaction"       : {"priority": "High",   "sla_hours": 24},
    "card_swallowed"           : {"priority": "High",   "sla_hours": 24},
    "wrong_charges"            : {"priority": "Medium", "sla_hours": 48},
    "net_banking_issue"        : {"priority": "Medium", "sla_hours": 48},
    "staff_misbehavior"        : {"priority": "Medium", "sla_hours": 72},
    "account_opening_delay"    : {"priority": "Low",    "sla_hours": 120},
    "general"                  : {"priority": "Low",    "sla_hours": 120}
}

CATEGORY_KEYWORDS = {
    "unauthorized_transaction" : ["unauthorized", "fraud", "unknown transaction"],
    "card_cloned"              : ["cloned", "skimmed", "stolen card"],
    "failed_transaction"       : ["failed", "deducted", "reversed", "not credited"],
    "card_swallowed"           : ["swallowed", "ate my card", "card stuck"],
    "wrong_charges"            : ["wrong charge", "extra charge", "duplicate"],
    "net_banking_issue"        : ["net banking", "login", "password", "upi"],
    "staff_misbehavior"        : ["staff", "rude", "misbehave"],
    "account_opening_delay"    : ["account opening", "delay", "pending"],
}

def _save_ticket_to_store(ticket):
    """Persists ticket to disk — survives session restart"""
    os.makedirs("data", exist_ok=True)
    store = _load_ticket_store()
    store[ticket["ticket_id"]] = ticket
    with open(TICKETS_FILE, "w") as f:
        json.dump(store, f, indent=2)

def _load_ticket_store():
    """Loads all persisted tickets from disk"""
    if not os.path.exists(TICKETS_FILE):
        return {}
    try:
        with open(TICKETS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}
    
def detect_category(text):
    text_lower = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return category
    return "general"


def generate_ticket_id():
    year   = datetime.now().strftime("%Y")
    number = random.randint(10000, 99999)
    return f"TKT-{year}-{number:05d}"


def calculate_eta(sla_hours):
    eta = datetime.now() + timedelta(hours=sla_hours)
    return eta.strftime("%d-%b-%Y by %I:%M %p")


def mask_email(email):
    if not email or "@" not in email:
        return email or "Not provided"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return email
    masked = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked}@{domain}"

def update_ticket_priority(user_message, ticket_id=None,
                            persona="existing_customer",
                            session_id="SYSTEM",
                            chat_history=[]):
    """
    Updates priority of an existing ticket.
    Only authorised bank staff (bankers) can update priority.
    If ticket_id not known — lists available tickets and asks which one.
    """
    log_info(session_id, persona, "ticket_priority_update_called",
             f"ticket_id={ticket_id}")

    # Only bankers can update ticket priority
    if persona != "banker":
        log_warning(session_id, persona, "ticket_priority_access_denied",
                    f"persona={persona} attempted priority update")
        return (
            "Priority updates can only be made by authorised bank staff.\n\n"
            "   Please visit your nearest branch and speak to our staff\n"
            "   to request a priority change on your ticket."
        )

    priority_map = {
        "urgent"  : "Urgent",
        "high"    : "High",
        "medium"  : "Medium",
        "low"     : "Low"
    }

    # Detect requested priority from message
    msg_lower = user_message.lower()
    new_priority = "High"   # default if user says "high priority"
    for key, val in priority_map.items():
        if key in msg_lower:
            new_priority = val
            break

    priority_icons = {
        "Urgent": "🔴", "High": "🟠",
        "Medium": "🟡", "Low" : "🟢"
    }
    priority_icon = priority_icons.get(new_priority, "🟠")

    # If ticket_id known — update directly
    if ticket_id:
        ticket = SESSION_TICKETS.get(ticket_id) or MOCK_TICKETS.get(ticket_id)

        if not ticket:
            return (f"❌ No ticket found with ID: {ticket_id}\n"
                    f"   Please verify the Ticket ID.")

        # Update priority
        old_priority      = ticket.get("priority", "Low")
        ticket["priority"] = new_priority
        ticket["remark"]   = (f"Priority updated from {old_priority} "
                               f"to {new_priority} by customer request.")
        ticket["last_updated"] = datetime.now().strftime("%d-%b-%Y %I:%M %p")
        ticket["updated_by"]   = "Customer"

        log_info(session_id, persona, "ticket_priority_updated",
                 f"ticket={ticket_id} old={old_priority} new={new_priority}")

        return (f"✅ Ticket Priority Updated!\n\n"
                f"   Ticket ID  : {ticket_id}\n"
                f"   Old Priority: {ticket.get('priority', old_priority)}\n"
                f"   New Priority: {priority_icon} {new_priority}\n"
                f"   Updated On : {ticket['last_updated']}\n\n"
                f"   Our team will prioritize your request accordingly.\n"
                f"   For urgent help call: 1800-XXX-XXXX (24/7)")

    # No ticket_id — check session tickets first
    if SESSION_TICKETS:
        ticket_list = "\n".join([
            f"   • {tid} — {t['category']} ({t['priority']})"
            for tid, t in SESSION_TICKETS.items()
        ])
        return (f"I can update the priority of your ticket.\n\n"
                f"   Your recent tickets:\n{ticket_list}\n\n"
                f"   Which ticket would you like to update to "
                f"{priority_icon} {new_priority}?\n"
                f"   Please share the Ticket ID.")

    # No tickets at all
    return (f"To update ticket priority, please share your Ticket ID.\n"
            f"   (e.g. TKT-2026-42308 — shown in your email confirmation)\n\n"
            f"   Which ticket would you like to update to "
            f"{priority_icon} {new_priority}?")

# ── Main function — LLM collects details conversationally ─────────────────────

def log_complaint(user_message, customer_id=None, email=None,
                  persona="existing_customer", session_id="SYSTEM",
                  chat_history=[], feedback_style="default"):
    """
    Uses LLM with full chat_history to collect complaint details
    conversationally. LLM extracts all needed info from conversation.
    Then logs structured ticket.
    """
    from core.llm_agent import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage
    from tools.feedback_tool import get_style_guidance
    import json

    log_info(session_id, persona, "complaint_tool_called", user_message)

    style_guidance = get_style_guidance(feedback_style, persona)

    llm = get_llm()

    # Step 1 — LLM extracts complaint details from conversation
    extract_prompt = f"""
Extract complaint details from this banking support conversation.

Reply ONLY with valid JSON:
{{
    "complaint_description": "description of the issue",
    "category": "category or general",
    "amount": number_or_null,
    "date_of_incident": "date or today",
    "email": "email if mentioned or null",
    "customer_id": "CUST-XXXXX if mentioned or null",
    "has_enough_info": true or false
}}

has_enough_info = true if customer has described WHAT the issue is.
It does NOT need to be detailed — even a simple clear statement qualifies.

Examples that ARE enough:
"My account has been frozen. Please unfreeze it"  → true
"Request to unfreeze my account"                  → true
"My ATM transaction failed"                       → true
"Wrong charges on my account"                     → true
"My card is not working"                          → true

Examples that are NOT enough:
"I want to raise a complaint"                     → false
"I have an issue"                                 → false
"file a ticket"                                   → false
"""

    messages = [SystemMessage(content=extract_prompt)]
    for msg in chat_history[-6:]:
        messages.append(msg)
    messages.append(HumanMessage(content=user_message))

    try:
        response = llm.invoke(messages)
        text     = response.content.strip()
        text     = text.replace("```json","").replace("```","").strip()
        details  = json.loads(text)
    except Exception:
        details  = {
            "complaint_description": user_message,
            "category"             : detect_category(user_message),
            "amount"               : None,
            "date_of_incident"     : datetime.now().strftime("%d-%b-%Y"),
            "email"                : email,
            "customer_id"          : customer_id,
            "has_enough_info"      : False
        }
    # ✅ If not enough info — ask for details instead of logging
    if not details.get("has_enough_info"):
        log_info(session_id, persona,
                 "complaint_details_needed", user_message)
        return ("I'd be happy to help raise a complaint. "
                "Could you please describe the issue?\n\n"
                "       For example:\n"
                "       • What happened?\n"
                "       • When did it occur?\n"
                "       • Any amount involved?\n\n"
                "       The more details you share, the faster "
                "we can resolve it!")
    
    # Use extracted or passed values
    cust_id     = details.get("customer_id") or customer_id
    email_addr  = details.get("email") or email
    description = details.get("complaint_description", user_message)
    category    = details.get("category", "general")
    amount      = details.get("amount")
    incident_dt = details.get("date_of_incident",
                               datetime.now().strftime("%d-%b-%Y"))

    # Step 2 — Log the ticket
    rules     = PRIORITY_RULES.get(category, PRIORITY_RULES["general"])
    priority  = rules["priority"]
    eta       = calculate_eta(rules["sla_hours"])
    ticket_id = generate_ticket_id()
    logged_on = datetime.now().strftime("%d-%b-%Y %I:%M %p")

    category_labels = {
        "unauthorized_transaction" : "Unauthorized Transaction",
        "card_cloned"              : "Card Cloned / Fraud",
        "failed_transaction"       : "Failed Transaction — Amount Debited",
        "card_swallowed"           : "Card Swallowed by ATM",
        "wrong_charges"            : "Wrong Charges Applied",
        "net_banking_issue"        : "Digital Banking Issue",
        "staff_misbehavior"        : "Service Quality — Staff Behaviour",
        "account_opening_delay"    : "Account Opening Delay",
        "general"                  : "General Complaint"
    }
    category_label = category_labels.get(category, "General Complaint")

    priority_icons = {"Urgent": "🔴", "High": "🟠",
                      "Medium": "🟡", "Low": "🟢"}
    priority_icon  = priority_icons.get(priority, "🟢")

    ticket = {
        "ticket_id"        : ticket_id,
        "customer_id"      : cust_id or "NOT_PROVIDED",
        "category"         : category_label,
        "description"      : description,
        "date_of_incident" : incident_dt,
        "amount"           : amount,
        "priority"         : priority,
        "status"           : "Logged",
        "logged_on"        : logged_on,
        "last_updated"     : logged_on,
        "updated_by"       : "System",
        "remark"           : "Complaint received and being reviewed.",
        "email_sent_to"    : mask_email(email_addr),
        "resolution_eta"   : eta,
        "session_id"       : session_id
    }

    SESSION_TICKETS[ticket_id] = ticket
    
    # After SESSION_TICKETS[ticket_id] = ticket
    SESSION_TICKETS[ticket_id] = ticket
    _save_ticket_to_store(ticket)   # ← persist to disk!
    

    # Build response
    if persona == "banker":
        response_text = (
            f"COMPLAINT REGISTRATION — STAFF ASSISTED\n"
            f"{'='*45}\n"
            f"Customer ID        : {cust_id or 'NOT_PROVIDED'}\n"
            f"Ticket ID          : {ticket_id}\n"
            f"Category           : {category_label}\n"
            f"Priority           : {priority_icon} {priority}\n"
            f"Description        : {description}\n"
            f"Logged On          : {logged_on}\n"
            f"Resolution SLA     : {eta}\n"
            f"Email Notification : {mask_email(email_addr)}\n"
            f"{'='*45}"
        )
    else:
        response_text = (
            f"✅ Complaint Logged Successfully\n\n"
            f"   Ticket ID      : {ticket_id}\n"
            f"   Category       : {category_label}\n"
            f"   Priority       : {priority_icon} {priority}\n"
            f"   Logged On      : {logged_on}\n"
            f"   Resolution ETA : {eta}\n"
        )
        if email_addr:
            response_text += (f"\n   📧 Confirmation sent to: "
                              f"{mask_email(email_addr)}")
        else:
            response_text += ("\n   📧 Share your email for confirmation")

        response_text += (f"\n\n   Reference: {ticket_id}\n"
                          f"   For urgent help: 1800-XXX-XXXX (24/7)")

        if priority == "Urgent":
            response_text += ("\n\n   ⚠️  URGENT: Please also block your "
                              "card via net banking or call 1800-XXX-XXXX now!")

        if feedback_style == "detailed":
            response_text += ("\n\n   📋 What happens next?\n"
                              "   • Our team reviews your complaint within 24 hours\n"
                              "   • You will receive an email update at each stage\n"
                              "   • You can track status anytime using your Ticket ID\n"
                              "   Would you like to know anything else?")

    log_info(session_id, persona, "complaint_logged",
             f"ticket_id={ticket_id} priority={priority}")
    
    return response_text


# ── Check ticket status ───────────────────────────────────────────────────────

def check_ticket_status(ticket_id, customer_id=None,
                        persona="existing_customer",
                        session_id="SYSTEM"):

    log_info(session_id, persona, "ticket_status_called",
             f"ticket_id={ticket_id}")

    ticket = SESSION_TICKETS.get(ticket_id) or MOCK_TICKETS.get(ticket_id)

    if not ticket:
        log_warning(session_id, persona, "ticket_not_found", ticket_id)
        return (f"❌ No ticket found with ID: {ticket_id}\n\n"
                f"   Please check the Ticket ID and try again.")

    if (persona == "existing_customer" and customer_id and
            ticket.get("customer_id") not in [customer_id, "NOT_PROVIDED"]):
        log_warning(session_id, persona, "ticket_access_denied",
                    f"ticket_id={ticket_id}")
        return "❌ This ticket does not belong to your account."

    status_icons = {
        "Logged": "🟡", "In Progress": "🔵",
        "Awaiting Info": "🟠", "Resolved": "🟢", "Closed": "⚫"
    }
    status_icon = status_icons.get(ticket.get("status",""), "🟡")

    if persona == "banker":
        return (f"COMPLAINT STATUS — STAFF VIEW\n{'='*45}\n"
                f"Ticket ID     : {ticket['ticket_id']}\n"
                f"Customer ID   : {ticket.get('customer_id','N/A')}\n"
                f"Status        : {status_icon} {ticket['status']}\n"
                f"Category      : {ticket['category']}\n"
                f"Priority      : {ticket.get('priority','N/A')}\n"
                f"Description   : {ticket['description']}\n"
                f"Logged On     : {ticket['logged_on']}\n"
                f"Last Updated  : {ticket['last_updated']}\n"
                f"Remark        : {ticket['remark']}\n"
                f"Resolution ETA: {ticket['resolution_eta']}\n"
                f"{'='*45}")

    priority      = ticket.get("priority", "Low")
    priority_icons = {"Urgent": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}
    priority_icon  = priority_icons.get(priority, "🟢")

    return (f"📋 Complaint Status\n\n"
            f"   Ticket ID      : {ticket['ticket_id']}\n"
            f"   Status         : {status_icon} {ticket['status']}\n"
            f"   Priority       : {priority_icon} {priority}\n"
            f"   Category       : {ticket['category']}\n"
            f"   Description    : {ticket.get('description', 'N/A')}\n"
            f"   Logged On      : {ticket['logged_on']}\n"
            f"   Last Updated   : {ticket['last_updated']}\n"
            f"   Remark         : {ticket['remark']}\n"
            f"   Resolution ETA : {ticket['resolution_eta']}\n\n"
            f"   For urgent help: 1800-XXX-XXXX")
