# core/llm_agent.py
# LLM brain for the banking support agent
# Handles: system prompt, intent detection, LLM response generation

import os
import httpx
from dotenv import load_dotenv
from langchain_openai        import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

load_dotenv()

# ── Proxy bypass ──────────────────────────────────────────────────────────────
http_client       = httpx.Client(proxy=None, timeout=60.0)
http_async_client = httpx.AsyncClient(proxy=None, timeout=60.0)

# ── Valid intents ─────────────────────────────────────────────────────────────
VALID_INTENTS = [
    "document_checklist",
    "eligibility",
    "faq",
    "complaint",
    "locator",
    "account_inquiry",
    "unknown"
]


# ── Function 1 — LLM Initializer ─────────────────────────────────────────────

def get_llm():
    """
    Returns ChatOpenAI instance with proxy bypass.
    Created fresh each call to avoid connection issues.
    """
    return ChatOpenAI(
        model             = "gpt-4o",
        temperature       = 0,
        http_client       = http_client,
        http_async_client = http_async_client
    )


# ── Function 2 — System Prompt Builder ───────────────────────────────────────

def build_system_prompt(persona, memory_context=""):
    """
    Builds persona-aware system prompt.
    System prompt teaches LLM the rules — no hardcoding needed!
    LLM handles all conversation scenarios automatically.
    memory_context injected to greet returning users
    and reference their history naturally.

    Parameters:
        persona        : new_customer / existing_customer / banker
        memory_context : string from memory_manager.build_memory_context()
                         empty string for new users
    """

    base_prompt = """
    You are a banking support assistant for a leading Indian bank.

    You help customers with:
    - Document checklists for banking services
    - Loan and credit card eligibility checks
    - Banking FAQs and policy questions
    - Complaint logging and status tracking
    - Branch and ATM locations in Hyderabad
    - Account information queries

    STRICT RULES — ALWAYS FOLLOW:
    - You NEVER process transactions, transfers, or payments
    - You NEVER ask for or accept passwords, PINs, or OTPs
    - You NEVER answer non-banking questions
    - You NEVER make up information — if unsure say
      "I don't have that information, please contact your nearest branch"
    - Always be professional, empathetic, and concise
    - Always ask clarifying questions if user intent is unclear
    - Guide users to the right service based on their need
    - Keep responses clear and structured
    """

    if persona == "new_customer":
        base_prompt += """
    PERSONA: NEW CUSTOMER — Critical Rules:
    - This person does NOT have a bank account yet
    - They have NO customer ID, account number, or existing products
    - NEVER ask for customer ID or account number from this person
    - If they ask about account details — they need to open an
      account first, guide them towards account opening warmly
    - If they ask about loans — help them understand eligibility
      and documents needed to apply
    - Focus on: account opening, product information, eligibility
    - Use simple, welcoming, encouraging language
    - Always offer to help them get started with the bank
    - Be patient — they may not know banking terminology
    """

    elif persona == "existing_customer":
        base_prompt += """
    PERSONA: EXISTING CUSTOMER — Important Rules:
    - This person already has an account with the bank
    - They may have loans, cards, or fixed deposits linked
    - Ask for customer ID only when needed for account inquiry
    - Acknowledge their concern empathetically before asking details
    - Be supportive — they may be frustrated if facing issues
    - Offer clear next steps for every query
    - Remind them of self-service options (net banking, mobile app)
      where appropriate
    """

    elif persona == "banker":
        base_prompt += """
    PERSONA: BANK EMPLOYEE / MANAGER — Important Rules:
    - This is internal bank staff assisting customers
    - They may look up any customer account using customer ID
    - Use formal, precise, and complete language
    - Provide full technical details and policy references
    - They may be entering data on behalf of a walk-in customer
    - Include process steps and escalation paths where relevant
    """
     
     # ── Phase 6: Inject memory context ───────────────────────────────────────
    # If returning user — LLM knows their history and greets accordingly
    if memory_context:
        base_prompt += f"""
    {memory_context}
 
    MEMORY USAGE RULES:
    - Greet returning customers warmly — mention it's good to see them again
    - Reference their previous enquiries naturally if relevant
    - If they enquired about a product before — offer to continue from there
    - Do NOT robotically list all memory facts — use naturally in conversation
    """
 
    return base_prompt.strip()
    



# ── Function 3 — LLM Response Generator ──────────────────────────────────────

def get_llm_response(user_message, persona, chat_history=[]):
    """
    Sends full conversation context to GPT-4o and returns response.
    System prompt + history + current message = smart contextual reply.

    Parameters:
        user_message : current message from user
        persona      : new_customer / existing_customer / banker
        chat_history : list of previous HumanMessage and AIMessage objects

    Returns:
        response string from GPT-4o
    """

    llm      = get_llm()
    messages = []

    # 1. System prompt — always first
    messages.append(
        SystemMessage(content=build_system_prompt(persona))
    )

    # 2. Conversation history — gives LLM memory
    for msg in chat_history:
        messages.append(msg)

    # 3. Current user message — always last
    messages.append(
        HumanMessage(content=user_message)
    )

    response = llm.invoke(messages)
    return response.content


# ── Function 4 — LLM Intent Detector ─────────────────────────────────────────

def detect_intent_llm(user_message):
    """
    Uses GPT-4o to classify user message into one of 7 intents.
    Much smarter than keyword matching — understands meaning,
    synonyms, informal language, and context.

    Parameters:
        user_message : raw message from user

    Returns:
        intent string — one of VALID_INTENTS
    """

    llm = get_llm()

    intent_prompt = f"""
    You are an intent classifier for a banking support chatbot.

    Classify the customer message into EXACTLY ONE of these intents:

    - document_checklist : customer wants to OPEN or APPLY for
                           something NEW, or asking what documents
                           are needed for any banking service
                           Examples:
                           "I want to open a new account"
                           "I want to open a savings account"
                           "how do I apply for home loan"
                           "what documents do I need"
                           "steps to enable net banking"
                           "how to get a credit card"

    - eligibility        : customer asking if they QUALIFY for a
                           loan or credit card based on salary,
                           age, or CIBIL score
                           Examples:
                           "can I get a loan with 30k salary"
                           "am I eligible for credit card"
                           "what is minimum salary for home loan"

    - faq                : customer asking general banking questions,
                           interest rates, charges, fees, policies,
                           rules, or how something works
                           Examples:
                           "what is minimum balance"
                           "what are NEFT charges"
                           "what is the interest rate on FD"
                           "how does KYC work"

    - complaint          : customer reporting a PROBLEM, failed
                           transaction, wrong charges, card issue,
                           or wanting to raise or check a ticket
                           Examples:
                           "my ATM transaction failed"
                           "wrong charges on my account"
                           "my card is not working"
                           "I want to raise a complaint"
                           "check status of my complaint"

    - locator            : customer looking for branch or ATM
                           LOCATION, address, or timings
                           Examples:
                           "nearest ATM to Ameerpet"
                           "where is your branch"
                           "ATM near me"
                           "branch timings"

    - account_inquiry    : EXISTING customer asking about THEIR
                           CURRENT account details, KYC status,
                           linked products, or account status
                           NOTE: "open account" = document_checklist
                           NOT account_inquiry
                           Examples:
                           "show my account details"
                           "what is my KYC status"
                           "check my account"
                           "what loans do I have"

    - unknown            : message is unclear, too vague, or
                           completely unrelated to banking

    IMPORTANT CLASSIFICATION RULES:
    - "open account" or "new account" = document_checklist
    - "my account" or "check account" = account_inquiry
    - account_inquiry is ONLY for existing customers
      checking their existing account details
    - When in doubt between two intents — pick the more specific one

    Customer message: "{user_message}"

    Reply with ONLY the intent name. Nothing else.
    No explanation. No punctuation. Just the intent word.
    """

    response = llm.invoke([HumanMessage(content=intent_prompt)])
    intent   = response.content.strip().lower()

    # Clean up — remove any punctuation LLM might add
    intent = intent.strip(".,!? \n")

    if intent not in VALID_INTENTS:
        return "unknown"

    return intent


# ── Quick test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("Testing LLM Agent...\n")

    # Test intent detection
    print("── Intent Detection Test ──")
    test_messages = [
        "I want to open a new account",
        "my txn got reversed",
        "what papers should I bring for home loan",
        "show me my passbook",
        "nearest ATM la bhai",
        "I earn 35k can I get a loan",
        "what is interest rate on FD",
        "I want to book a flight"
    ]

    for msg in test_messages:
        intent = detect_intent_llm(msg)
        print(f"  '{msg}'")
        print(f"   → {intent}\n")

    # Test full response
    print("\n── Full Response Test ──")
    response = get_llm_response(
        user_message = "I want to open a savings account",
        persona      = "new_customer",
        chat_history = []
    )
    print(f"New Customer asks: 'I want to open a savings account'")
    print(f"Agent: {response}")
