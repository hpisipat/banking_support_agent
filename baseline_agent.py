# baseline_agent.py

from core.router          import detect_intent
from core.guardrails      import check_guardrails
from observability.logger_bkp import (generate_session_id,
                                  log_info,
                                  log_warning,
                                  log_error)

# ── Persona Selection ─────────────────────────────────────────────────────────

def select_persona():
    """Ask user who they are — determines tool access later"""
    print("\nPlease select your profile:")
    print("  1. New Customer")
    print("  2. Existing Customer")
    print("  3. Banker / Staff")

    personas = {
        "1": "new_customer",
        "2": "existing_customer",
        "3": "banker"
    }

    while True:
        choice = input("Enter choice (1/2/3): ").strip()
        if choice in personas:
            return personas[choice]
        print("Invalid choice. Please enter 1, 2, or 3.")


# ── Tool Stub ─────────────────────────────────────────────────────────────────

def call_tool(intent, persona, session_id):
    """
    Phase 2 — stub responses only.
    Real tool logic comes in Phase 5.
    """
    tool_responses = {
        "document_checklist" : "I can help with document requirements. "
                               "[Full checklist tool coming in Phase 5]",
        "eligibility"        : "I can check your eligibility. "
                               "[Eligibility tool coming in Phase 5]",
        "faq"                : "Let me look that up for you. "
                               "[FAQ / RAG tool coming in Phase 4]",
        "complaint"          : "I can log your complaint. "
                               "[Complaint tool coming in Phase 5]",
        "locator"            : "Let me find the nearest branch or ATM. "
                               "[Locator tool coming in Phase 5]",
        "account_inquiry"    : "Let me pull up your account details. "
                               "[Account tool coming in Phase 5]",
    }

    response = tool_responses.get(intent, "I'm not sure how to help with that.")

    # Log the tool call
    log_info(session_id, persona, "tool_called",   intent)
    log_info(session_id, persona, "tool_response", response)

    return response


# ── Main Agent Loop ───────────────────────────────────────────────────────────

def run_agent():

    # Session setup
    session_id = generate_session_id()
    persona    = select_persona()

    log_info(session_id, persona, "session_started", f"persona={persona}")

    print()
    print("=" * 45)
    print("  Banking Support Agent — Baseline Version")
    print("=" * 45)
    print(f"  Session : {session_id}")
    print(f"  Profile : {persona.replace('_', ' ').title()}")
    print("=" * 45)
    print("Agent: Hi! Welcome to Banking Support.")
    print("       Type 'exit' to end the session.\n")

    while True:

        user_message = input("You: ").strip()

        # Handle empty input
        if not user_message:
            continue

        # Handle exit
        if user_message.lower() == "exit":
            log_info(session_id, persona, "session_ended")
            print("Agent: Thank you for contacting us. Goodbye!\n")
            break

        # Log incoming message
        log_info(session_id, persona, "user_message", user_message)

        # ── Step 1: Guardrails ────────────────────────────────────────────────
        is_blocked, block_message = check_guardrails(user_message)

        if is_blocked:
            log_warning(session_id, persona,
                        "guardrail_triggered", user_message)
            print(f"Agent: {block_message}\n")
            continue

        # ── Step 2: Intent Detection ──────────────────────────────────────────
        intent = detect_intent(user_message)

        if intent == "unknown":
            log_warning(session_id, persona,
                        "intent_unknown", user_message)
            print("Agent: I'm sorry, I didn't understand that.")
            print("       I can help with:")
            print("       • Account details & KYC")
            print("       • Loan / credit card eligibility")
            print("       • Document checklists")
            print("       • Complaints & ticket status")
            print("       • Branch & ATM locations")
            print("       • Banking FAQs & policies\n")
            continue

        # ── Step 3: Call Tool ─────────────────────────────────────────────────
        log_info(session_id, persona, "intent_detected", intent)
        response = call_tool(intent, persona, session_id)
        print(f"Agent: {response}\n")


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_agent()
