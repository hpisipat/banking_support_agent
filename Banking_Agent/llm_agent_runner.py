# llm_agent_runner.py
# Phase 6 — Long-term Memory
# Saves session memory on exit, loads on start
# Injects memory context into system prompt for returning users

import os
import warnings
import json
os.environ["LANGCHAIN_OPENAI_TCP_KEEPALIVE"] = "0"
warnings.filterwarnings("ignore")

import re
from core.guardrails       import check_guardrails
from core.router           import detect_intent
from core.tool_access      import is_tool_allowed, get_access_denied_message
from core.llm_agent        import get_llm_response, detect_intent_llm
from memory.memory_manager import (load_memory, save_session_memory,
                                   build_memory_context)
from langchain_core.messages import HumanMessage, AIMessage
from observability.logger  import (generate_session_id,
                                   log_info, log_warning, log_error)

MAX_RETRIES = 3


# ── Persona Selection ─────────────────────────────────────────────────────────

def select_persona():
    print("\nPlease select your profile:")
    print("  1. New Customer")
    print("  2. Existing Customer")
    print("  3. Banker / Staff")
    personas = {"1": "new_customer", "2": "existing_customer", "3": "banker"}
    while True:
        choice = input("Enter choice (1/2/3): ").strip()
        if choice in personas:
            return personas[choice]
        print("  Invalid choice. Please enter 1, 2, or 3.")


# ── Structured extractors ─────────────────────────────────────────────────────

def extract_customer_id(text):
    match = re.search(r'CUST-\d+', text, re.IGNORECASE)
    return match.group(0).upper() if match else None

def extract_mobile(text):
    match = re.search(r'\b\d{10}\b', text)
    return match.group(0) if match else None

def extract_email(text):
    match = re.search(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    return match.group(0) if match else None

def extract_employee_id(text):
    match = re.search(r'EMP-\d+', text, re.IGNORECASE)
    return match.group(0).upper() if match else None

def extract_ticket_id(text):
    match = re.search(r'TKT-\d{4}-\d+', text, re.IGNORECASE)
    return match.group(0).upper() if match else None


def get_context_from_history(chat_history):
    """Scans history for structured IDs"""
    context = {
        "customer_id": None, "mobile": None, "email": None,
        "employee_id": None, "ticket_id": None
    }
    for msg in chat_history:
        text = msg.content if hasattr(msg, 'content') else str(msg)
        if not context["customer_id"]: context["customer_id"] = extract_customer_id(text)
        if not context["mobile"]:      context["mobile"]      = extract_mobile(text)
        if not context["email"]:       context["email"]       = extract_email(text)
        if not context["employee_id"]: context["employee_id"] = extract_employee_id(text)
        if not context["ticket_id"]:   context["ticket_id"]   = extract_ticket_id(text)
    return context


# ── Small Talk Detection ──────────────────────────────────────────────────────

def is_small_talk(user_message):
    """LLM detects pure appreciation — responds warmly"""
    from core.llm_agent import get_llm
    from langchain_core.messages import HumanMessage as HM

    if len(user_message.split()) > 10 or "?" in user_message:
        return False

    llm    = get_llm()
    prompt = f"""
Customer said: "{user_message}"

Is this ONLY a thank you or positive acknowledgement with NO question?

"thanks" → yes  |  "thank you" → yes  |  "great" → yes
"ok" → yes      |  "got it" → yes     |  "helpful" → yes

"no thanks" → no  |  "bye" → no  |  "thanks what about X?" → no

Reply ONLY "yes" or "no".
"""
    try:
        response = llm.invoke([HM(content=prompt)])
        return response.content.strip().lower().startswith("yes")
    except:
        return False


# ── Conversation End Detection ────────────────────────────────────────────────

def is_conversation_ending(user_message, chat_history):
    """LLM detects if user is leaving or declining help"""
    from core.llm_agent import get_llm
    from langchain_core.messages import HumanMessage as HM

    if len(user_message.split()) > 10 or "?" in user_message:
        return False

    llm    = get_llm()
    prompt = f"""
Customer said: "{user_message}"

Is the customer LEAVING or DECLINING further help?

"bye" → yes  |  "exit" → yes  |  "no thanks" → yes
"nothing" → yes  |  "I'm good" → yes  |  "no" → yes
"done" → yes  |  "that's all" → yes

"thanks" → no  |  "thank you" → no  |  "ok" → no

Reply ONLY "yes" or "no".
"""
    try:
        response = llm.invoke([HM(content=prompt)])
        result   = response.content.strip().lower()
        log_info("SYSTEM", "system", "exit_check",
                 f"message='{user_message}' result='{result}'")
        return result.startswith("yes")
    except Exception as e:
        log_info("SYSTEM", "system", "exit_check_failed", str(e))
        return False


# ── Product Tracker ───────────────────────────────────────────────────────────

def track_products(user_message, response, session_data,
                   session_id, persona):
    """LLM extracts products discussed. Silent fail — non-critical."""
    try:
        from core.llm_agent import get_llm
        from langchain_core.messages import HumanMessage as HM

        llm    = get_llm()
        prompt = f"""
From this banking conversation, extract what banking products
or services the customer enquired about.

Customer said: "{user_message}"
Agent replied: "{response[:300]}"

Return ONLY a JSON list using standard names:
personal_loan, home_loan, car_loan, education_loan,
credit_card, savings_account, current_account,
fixed_deposit, demat_account, net_banking,
branch_locator, complaint, account_inquiry

Example: ["personal_loan", "credit_card"]
Return [] if nothing specific was discussed.
Return ONLY the JSON list, nothing else.
"""
        result   = llm.invoke([HM(content=prompt)])
        text     = result.content.strip()
        text     = text.replace("```json","").replace("```","").strip()
        products = json.loads(text)

        if isinstance(products, list) and products:
            existing = session_data.get("products_enquired", [])
            session_data["products_enquired"] = list(
                set(existing + products)
            )
            log_info(session_id, persona,
                     "memory_products_tracked",
                     f"products={products}")
    except Exception:
        pass


# ── Ticket ID Tracker ─────────────────────────────────────────────────────────

def track_ticket_id(response, session_data, session_id, persona):
    """
    Extracts ticket ID from agent response when complaint is logged.
    Saves to session_data so it persists to memory across sessions.
    """
    match = re.search(r'TKT-\d{4}-\d+', response)
    if match:
        ticket_id = match.group(0)
        if "ticket_ids" not in session_data:
            session_data["ticket_ids"] = []
        if ticket_id not in session_data["ticket_ids"]:
            session_data["ticket_ids"].append(ticket_id)
            log_info(session_id, persona,
                     "memory_ticket_id_tracked",
                     f"ticket_id={ticket_id}")


# ── Tool Router ───────────────────────────────────────────────────────────────

def route_to_tool(intent, user_message, persona, session_id,
                  chat_history, memory_context="",
                  session_data={}, memory={}):
    """Routes intent to real tool. All context passed."""

    context = get_context_from_history(chat_history)
    context["customer_id"] = context["customer_id"] or extract_customer_id(user_message)
    context["mobile"]      = context["mobile"]      or extract_mobile(user_message)
    context["email"]       = context["email"]        or extract_email(user_message)
    context["employee_id"] = context["employee_id"] or extract_employee_id(user_message)
    context["ticket_id"]   = context["ticket_id"]   or extract_ticket_id(user_message)

    if intent == "faq":
        try:
            from tools.faq_tool import get_faq_answer
            log_info(session_id, persona, "tool_called", "faq_tool")
            answer, _ = get_faq_answer(user_message, persona, session_id)
            return answer
        except Exception as e:
            log_error(session_id, persona, "faq_tool_failed", str(e))
            return "I'm having trouble searching our FAQ. Please call 1800-XXX-XXXX."

    if intent == "document_checklist":
        try:
            from tools.document_tool import get_document_checklist
            log_info(session_id, persona, "tool_called", "document_tool")
            return get_document_checklist(
                user_message, persona, session_id, chat_history)
        except Exception as e:
            log_error(session_id, persona, "document_tool_failed", str(e))
            return "Please visit your nearest branch for document details."

    if intent == "eligibility":
        try:
            from tools.eligibility_tool import check_eligibility_with_llm
            log_info(session_id, persona, "tool_called", "eligibility_tool")
            return check_eligibility_with_llm(
                user_message, persona, session_id, chat_history)
        except Exception as e:
            log_error(session_id, persona, "eligibility_tool_failed", str(e))
            return "Please visit your nearest branch for eligibility assessment."

    if intent == "locator":
        if persona == "banker" and any(
            w in user_message.lower()
            for w in ["zone", "all branches", "directory"]
        ):
            try:
                from tools.locator_tool import get_zone_directory
                log_info(session_id, persona, "tool_called", "zone_directory")
                return get_zone_directory(session_id=session_id)
            except Exception as e:
                log_error(session_id, persona, "zone_directory_failed", str(e))
        try:
            from tools.locator_tool import find_nearest
            log_info(session_id, persona, "tool_called", "locator_tool")
            return find_nearest(user_message, persona, session_id, chat_history)
        except Exception as e:
            log_error(session_id, persona, "locator_tool_failed", str(e))
            return "Please call 1800-XXX-XXXX for branch information."

    if intent == "complaint":
        try:
            from tools.complaint_tool import (log_complaint,
                                              check_ticket_status,
                                              update_ticket_priority,
                                              SESSION_TICKETS)
            from data.mock_tickets import MOCK_TICKETS

            log_info(session_id, persona, "tool_called", "complaint_tool")

            ticket_id        = context.get("ticket_id")
            msg_lower        = user_message.lower()
            pending_action   = session_data.get("pending_action", "")
            pending_priority = session_data.get("pending_priority", "High")

            wants_status = any(w in msg_lower for w in
                               ["status", "check ticket", "track",
                                "list", "show", "display",
                                "my ticket", "ticket details",
                                "details", "full details", "view ticket",
                                "view my"]) or bool(ticket_id)

            wants_priority_update = any(w in msg_lower for w in
                                        ["high priority", "urgent",
                                         "priority", "escalate",
                                         "make it high", "update priority",
                                         "change priority"])

            # ── Waiting for ticket ID to update priority ──────────────────────
            if pending_action == "priority_update" and ticket_id:
                session_data.pop("pending_action", None)
                session_data.pop("pending_priority", None)
                log_info(session_id, persona,
                         "ticket_priority_update_resumed",
                         f"ticket={ticket_id}")
                return update_ticket_priority(
                    f"update to {pending_priority} priority",
                    ticket_id    = ticket_id,
                    persona      = persona,
                    session_id   = session_id,
                    chat_history = chat_history
                )

            # ── Priority update request ───────────────────────────────────────
            if wants_priority_update:
                new_priority = "High"
                for p in ["urgent", "high", "medium", "low"]:
                    if p in msg_lower:
                        new_priority = p.title()
                        break
                session_data["pending_action"]   = "priority_update"
                session_data["pending_priority"] = new_priority

                return update_ticket_priority(
                    user_message,
                    ticket_id    = ticket_id,
                    persona      = persona,
                    session_id   = session_id,
                    chat_history = chat_history
                )

            # ── Status / list tickets ─────────────────────────────────────────
            if wants_status:
                if ticket_id:
                    return check_ticket_status(
                        ticket_id,
                        customer_id = context.get("customer_id"),
                        persona     = persona,
                        session_id  = session_id
                    )
                else:

                    from tools.complaint_tool import (SESSION_TICKETS,
                                          _load_ticket_store)
                    from data.mock_tickets import MOCK_TICKETS

                    tickets_to_show = dict(SESSION_TICKETS)

                    # Build full ticket list across all sources
                    tickets_to_show = dict(SESSION_TICKETS)

                    # ✅ Load from persistent store (survives session restart)
                    persisted = _load_ticket_store()

                    # Add tickets from memory (previous sessions)
                    saved_ids = memory.get("ticket_ids", [])
                    for tid in saved_ids:
                        if tid in persisted:
                            tickets_to_show[tid] = persisted[tid]   # ← fix!
                        elif tid in MOCK_TICKETS:
                            tickets_to_show[tid] = MOCK_TICKETS[tid]

                    # Add tickets from mock data for this customer
                    customer_id = context.get("customer_id")
                    if customer_id:
                        for tid, t in {**MOCK_TICKETS, **persisted}.items():
                            if t.get("customer_id") == customer_id:
                                tickets_to_show[tid] = t

                    if tickets_to_show:
                        def _ticket_summary(t):
                            desc = t.get("description", "")
                            summary = (desc[:60] + "...") if len(desc) > 60 else desc
                            return (f"{t['ticket_id']} — {summary}\n"
                                    f"     {t['category']} | "
                                    f"{t.get('priority','Low')} | {t['status']}")
                        ticket_list = "\n".join([
                            f"   • {_ticket_summary(t)}"
                            for t in tickets_to_show.values()
                        ])
                        return (f"📋 Your tickets:\n\n"
                                f"{ticket_list}\n\n"
                                f"   Share a Ticket ID for full details "
                                f"or to update priority.")

                    return ("No tickets found.\n"
                            "       Would you like to raise a complaint?\n"
                            "       I can help log a new ticket for you.")

            # ── Log new complaint ─────────────────────────────────────────────
            return log_complaint(
                user_message,
                customer_id  = context.get("customer_id"),
                email        = context.get("email"),
                persona      = persona,
                session_id   = session_id,
                chat_history = chat_history
            )

        except Exception as e:
            log_error(session_id, persona, "complaint_tool_failed", str(e))
            return "Please call 1800-XXX-XXXX for complaint assistance."

    if intent == "account_inquiry":
        try:
            from tools.account_tool import get_account_details
            log_info(session_id, persona, "tool_called", "account_tool")
            return get_account_details(
                user_message = user_message,
                persona      = persona,
                customer_id  = context.get("customer_id"),
                mobile       = context.get("mobile"),
                employee_id  = context.get("employee_id"),
                session_id   = session_id,
                chat_history = chat_history
            )
        except Exception as e:
            log_error(session_id, persona, "account_tool_failed", str(e))
            return "Please visit your nearest branch for account details."

    log_info(session_id, persona, "tool_called", f"llm_fallback:{intent}")
    return get_llm_response(user_message, persona, chat_history, memory_context)


# ── Main Agent Loop ───────────────────────────────────────────────────────────

def run_llm_agent():

    session_id   = generate_session_id()
    persona      = select_persona()
    chat_history = []
    retry_count  = 0
    last_intent  = "unknown"
    session_data = {
        "products_enquired": [],
        "last_intent"      : "unknown",
        "ticket_ids"       : []
    }

    # Phase 6: Load memory
    memory         = load_memory(session_id, persona)
    memory_context = build_memory_context(memory, persona)
    is_returning   = memory.get("session_count", 0) > 0

    log_info(session_id, persona, "session_started",
             f"persona={persona} returning={is_returning}")

    print()
    print("=" * 50)
    print("  Banking Support Agent — Phase 6")
    print("=" * 50)
    print(f"  Session : {session_id}")
    print(f"  Profile : {persona.replace('_', ' ').title()}")
    if is_returning:
        print(f"  Visits  : {memory.get('session_count', 0) + 1}")
    print("=" * 50)

    if is_returning:
        print("Agent: Welcome back! Great to have you again.")
        if memory.get("products_enquired"):
            products = ", ".join(memory["products_enquired"])
            print(f"       Last time you enquired about: {products}.")
        print("       How can I help you today?\n")
    else:
        print("Agent: Hi! Welcome to Banking Support.")
        print("       I can help you with:\n")
        print("       • Document checklists & process guides")
        print("       • Loan & credit card eligibility")
        print("       • Banking FAQs & policies")
        print("       • Complaint logging & tracking")
        print("       • Branch & ATM locations")
        print("       • Account details")
        print("\n       Type 'exit' to end the session.\n")

    while True:

        user_message = input("You: ").strip()

        if not user_message:
            continue

        log_info(session_id, persona, "user_message", user_message)

        # Small talk
        if is_small_talk(user_message):
            log_info(session_id, persona, "small_talk", user_message)
            print("Agent: You're welcome! Is there anything else "
                  "I can help you with?\n")
            continue

        # Step 1 — Guardrails
        is_blocked, block_message = check_guardrails(user_message)
        if is_blocked:
            log_warning(session_id, persona, "guardrail_triggered", user_message)
            print(f"Agent: {block_message}\n")
            continue

        # Step 2 — Intent Detection
        intent = "unknown"
        try:
            intent = detect_intent_llm(user_message)
            log_info(session_id, persona, "intent_detected_llm", intent)
            retry_count = 0
        except Exception as e:
            retry_count += 1
            log_error(session_id, persona, "intent_llm_failed",
                      f"attempt={retry_count} error={str(e)}")
            intent = detect_intent(user_message)
            log_info(session_id, persona, "intent_detected_fallback", intent)

        # Smart exit — AFTER intent, BEFORE last_intent
        if intent == "unknown":
            if is_conversation_ending(user_message, chat_history):
                session_data["last_intent"] = last_intent
                save_session_memory(
                    session_id, persona,
                    chat_history, session_data
                )
                log_info(session_id, persona, "session_ended",
                         f"total_turns={len(chat_history)//2} "
                         f"reason=natural_ending")
                print("Agent: Thank you for contacting us.")
                print("       Have a great day! Goodbye! 👋\n")
                break

        # Continue last intent for follow-ups
        if intent == "unknown" and last_intent != "unknown":
            if len(user_message.split()) <= 15:
                eligibility_signals = [
                    "eligible", "eligibility", "qualify",
                    "can i get", "will i get", "am i"
                ]
                msg_lower = user_message.lower()

                if any(signal in msg_lower for signal in eligibility_signals):
                    intent = "eligibility"
                    log_info(session_id, persona,
                             "intent_override_eligibility",
                             f"from={last_intent} message='{user_message}'")
                else:
                    intent = last_intent
                    log_info(session_id, persona, "intent_continued",
                             f"last_intent={last_intent} reply='{user_message}'")

        # Step 3 — Access Control
        if intent != "unknown" and not is_tool_allowed(intent, persona):
            log_warning(session_id, persona, "access_denied",
                        f"intent={intent} persona={persona}")
            print(f"Agent: {get_access_denied_message(intent, persona)}\n")
            continue

        # Step 4 — Handle unknown
        if intent == "unknown":
            log_warning(session_id, persona, "intent_unknown", user_message)

            if len(chat_history) > 0:
                try:
                    response = get_llm_response(
                        user_message, persona,
                        chat_history, memory_context
                    )
                    print(f"Agent: {response}\n")
                    log_info(session_id, persona, "agent_response",
                             f"intent=llm_contextual length={len(response)}")
                    chat_history.append(HumanMessage(content=user_message))
                    chat_history.append(AIMessage(content=response))
                except Exception as e:
                    log_error(session_id, persona,
                              "llm_contextual_failed", str(e))
                    print("Agent: Could you please rephrase that?\n")
                continue

            print("Agent: I'd be happy to help! I can assist with:\n")
            print("       • Opening accounts or applying for loans")
            print("       • Loan / credit card eligibility")
            print("       • Banking FAQs and policies")
            print("       • Raising or tracking complaints")
            print("       • Nearest branch or ATM")
            print("       • Account details\n")
            print("       Could you tell me more about what you need?\n")
            continue

        # Step 5 — Route to Tool
        log_info(session_id, persona, "intent_confirmed", intent)
        try:
            response = route_to_tool(
                intent         = intent,
                user_message   = user_message,
                persona        = persona,
                session_id     = session_id,
                chat_history   = chat_history,
                memory_context = memory_context,
                session_data   = session_data,
                memory         = memory
            )
            print(f"Agent: {response}\n")
            log_info(session_id, persona, "agent_response",
                     f"intent={intent} length={len(response)}")
            last_intent = intent
            retry_count = 0

            # Track products discussed
            track_products(user_message, response,
                           session_data, session_id, persona)

            # Track ticket IDs from complaint responses
            if intent == "complaint":
                track_ticket_id(response, session_data, session_id, persona)

        except Exception as e:
            retry_count += 1
            log_error(session_id, persona, "tool_failed",
                      f"intent={intent} attempt={retry_count} error={str(e)}")
            if retry_count >= MAX_RETRIES:
                log_error(session_id, persona, "max_retries_exceeded",
                          f"intent={intent}")
                print("Agent: I'm unable to process your request right now.")
                print("       Please visit your nearest branch or")
                print("       call us at 1800-XXX-XXXX\n")
                retry_count = 0
                last_intent = "unknown"
            else:
                print("Agent: I encountered an issue. Please try again.\n")
            continue

        # Step 6 — Update history
        chat_history.append(HumanMessage(content=user_message))
        chat_history.append(AIMessage(content=response))
        if len(chat_history) > 20:
            chat_history = chat_history[-20:]
            log_info(session_id, persona, "history_trimmed",
                     "kept last 10 turns")


if __name__ == "__main__":
    run_llm_agent()