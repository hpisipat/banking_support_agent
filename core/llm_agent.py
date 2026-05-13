# core/llm_agent.py
# LLM brain — system prompt, intent detection, response generation
# Phase 6: memory_context injected into system prompt

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


# ── Function 1 — LLM initializer ─────────────────────────────────────────────

def get_llm():
    return ChatOpenAI(
        model             = "gpt-4o",
        temperature       = 0,
        http_client       = http_client,
        http_async_client = http_async_client
    )


# ── Function 2 — System prompt builder ───────────────────────────────────────

def build_system_prompt(persona, memory_context="",
                        feedback_style="default", intent="",
                        user_id=None):
    """
    Builds persona-aware system prompt.
    Phase 6: memory_context injected to greet returning users
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
    """

    if persona == "new_customer":
        base_prompt += """
    PERSONA: NEW CUSTOMER — Critical Rules:
    - This person does NOT have a bank account yet
    - They have NO customer ID, account number, or existing products
    - NEVER ask for customer ID or account number from this person
    - If they ask about account details — guide them to account opening
    - Focus on: account opening, product information, eligibility
    - Use simple, welcoming, encouraging language
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
    """

    elif persona == "banker":
        base_prompt += """
    PERSONA: BANK EMPLOYEE / MANAGER — Important Rules:
    - This is internal bank staff assisting customers
    - They may look up any customer account using customer ID
    - Use formal, precise, and complete language
    - Provide full technical details and policy references
    - They may be entering data on behalf of a walk-in customer
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


    # ── Phase 7: Adaptive behaviour — ADDITIVE only ───────────────────────────
    # Only activates after 3+ feedbacks — never replaces existing behaviour
    if feedback_style not in ("default", ""):
        from tools.feedback_tool import get_style_guidance
        style_block = get_style_guidance(
            feedback_style,
            persona,
            user_id=user_id
        )
        if style_block:
            base_prompt += style_block

    return base_prompt.strip()


# ── Function 3 — LLM response generator ──────────────────────────────────────

def get_llm_response(user_message, persona, chat_history=[],
                     memory_context="", feedback_style="default",
                     intent="", user_id=None):
    """
    Generates response using GPT-4o with full context.
    Phase 6: memory_context added to system prompt.
    """
    llm      = get_llm()
    messages = []

    messages.append(
        SystemMessage(content=build_system_prompt(persona, memory_context,
                                              feedback_style, intent,
                                              user_id=user_id))
    )

    for msg in chat_history:
        messages.append(msg)

    messages.append(HumanMessage(content=user_message))

    response = llm.invoke(messages)
    return response.content


# ── Function 4 — LLM intent detector ─────────────────────────────────────────

def detect_intent_llm(user_message):
    """
    Uses GPT-4o to classify user message into one of 7 intents.
    """
    llm = get_llm()

    intent_prompt = f"""
    You are an intent classifier for a banking support chatbot.

    Classify the customer message into EXACTLY ONE of these intents:

    - document_checklist : customer wants to OPEN or APPLY for something NEW,
                           or asking what documents are needed
                           Examples: "I want to open a new account",
                           "how do I apply for home loan",
                           "what documents do I need"

    - eligibility        : customer asking if they QUALIFY for a loan
                           or credit card
                           Examples: "can I get a loan with 30k salary",
                           "am I eligible for credit card"

    - faq                : general banking questions, interest rates,
                           charges, fees, policies
                           Examples: "what is minimum balance",
                           "what are NEFT charges"

    - complaint          : customer reporting a PROBLEM or issue
                           Examples: "my ATM transaction failed",
                           "wrong charges on my account"

    - locator            : customer looking for branch or ATM location
                           Examples: "nearest ATM to Ameerpet",
                           "where is your branch"

    - account_inquiry    : EXISTING customer asking about THEIR account
                           Examples: "show my account details",
                           "what is my KYC status"

    - unknown            : unclear or unrelated to banking

    IMPORTANT:
    - "open account" = document_checklist NOT account_inquiry
    - account_inquiry is ONLY for existing customers checking their account

    Customer message: "{user_message}"

    Reply with ONLY the intent name. Nothing else.
    """

    response = llm.invoke([HumanMessage(content=intent_prompt)])
    intent   = response.content.strip().lower().strip(".,!? \n")

    if intent not in VALID_INTENTS:
        return "unknown"

    return intent
