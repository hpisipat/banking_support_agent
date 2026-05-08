# tools/eligibility_tool.py
# Feature 2 — Loan / Credit Card Eligibility Checker
# LLM handles full conversation — rules provided as context
# No regex, no hardcoded extraction — LLM understands natural language

import os
import sys
import warnings
os.environ["LANGCHAIN_OPENAI_TCP_KEEPALIVE"] = "0"
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from observability.logger import log_info, log_warning

# ── Eligibility Rules ─────────────────────────────────────────────────────────
# These are provided to LLM as context — not used programmatically
# LLM applies them to whatever the customer says

ELIGIBILITY_RULES = {
    "personal_loan": {
        "title"       : "Personal Loan",
        "min_age"     : 21,   "max_age"   : 58,
        "min_salary"  : 25000, "min_cibil" : 700,
        "emi_cap_pct" : 50,   "tenure_max": "5 years"
    },
    "home_loan": {
        "title"       : "Home Loan",
        "min_age"     : 23,   "max_age"   : 60,
        "min_salary"  : 40000, "min_cibil" : 720,
        "emi_cap_pct" : 40,   "tenure_max": "30 years"
    },
    "car_loan": {
        "title"       : "Car Loan",
        "min_age"     : 21,   "max_age"   : 65,
        "min_salary"  : 20000, "min_cibil" : 680,
        "emi_cap_pct" : 50,   "tenure_max": "7 years"
    },
    "education_loan": {
        "title"            : "Education Loan",
        "min_age"          : 16,    "max_age"          : 35,
        "co_applicant_min" : 20000, "min_cibil"        : 650,
        "collateral_above" : 750000,"tenure_max"       : "15 years"
    },
    "credit_card": {
        "title"             : "Credit Card",
        "min_age"           : 18,   "max_age"          : 65,
        "min_salary"        : 15000, "min_cibil"        : 700,
        "max_existing_cards": 3,    "tenure_max"       : "N/A"
    }
}


# ── Main function — LLM handles full eligibility conversation ─────────────────

def check_eligibility_with_llm(user_message, persona,
                                session_id, chat_history=[]):
    """
    LLM handles the complete eligibility conversation.
    - Collects missing details conversationally
    - Never asks for info already in chat_history
    - Calculates max loan amount when eligible
    - Answers follow-up questions naturally
    - No regex, no hardcoded extraction needed

    Parameters:
        user_message : current user message
        persona      : new_customer / existing_customer / banker
        session_id   : for logging
        chat_history : full conversation — LLM sees all context
    """
    from core.llm_agent import get_llm
    from langchain_core.messages import HumanMessage, SystemMessage

    log_info(session_id, persona, "eligibility_tool_called", user_message)

    # Rules as readable text for LLM
    rules_context = """
    ELIGIBILITY RULES:

    Personal Loan:
    - Age: 21 to 58 years
    - Min salary: Rs.25,000/month (salaried)
    - Min CIBIL score: 700
    - EMI cap: 50% of monthly salary
    - Max tenure: 5 years
    - Approx max amount = salary x 50% x 48 months

    Home Loan:
    - Age: 23 to 60 years
    - Min salary: Rs.40,000/month (salaried)
    - Min CIBIL score: 720
    - EMI cap: 40% of monthly salary
    - Max tenure: 30 years
    - Approx max amount = salary x 40% x 120 months

    Car Loan / Vehicle Loan (includes bike, car, scooter):
    - Age: 21 to 65 years
    - Min salary: Rs.20,000/month
    - Min CIBIL score: 680
    - EMI cap: 50% of monthly salary
    - Max tenure: 7 years

    Education Loan:
    - Student age: 16 to 35 years
    - Co-applicant income min: Rs.20,000/month
    - Co-applicant CIBIL min: 650
    - Collateral required above Rs.7.5 lakhs
    - Max tenure: 15 years

    Credit Card:
    - Age: 18 to 65 years
    - Min salary: Rs.15,000/month
    - Min CIBIL score: 700
    - Max existing cards: 3
    """

    
    system_prompt = f"""
        You are a banking eligibility assistant for a leading Indian bank.

        PERSONA: {persona.replace('_', ' ').title()}
        {"Use simple friendly language." if persona == "new_customer" else ""}
        {"Be formal and precise." if persona == "banker" else ""}

        YOUR JOB:
        - Check if customer is eligible for banking products
        - Collect ALL necessary details conversationally
        - NEVER ask for info already given in conversation
        - Use chat history — customer should not repeat themselves

        MANDATORY DETAILS TO COLLECT:
        You MUST collect ALL of these before giving eligibility result:
        1. Product type (personal loan / home loan / credit card etc.)
        2. Age
        3. Monthly income / salary
        4. CIBIL / credit score
        5. ✅ Existing monthly EMIs — ALWAYS ask this
        "Do you have any existing loan EMIs per month?"
        Even if customer says "no EMIs" — confirm and proceed
        This affects maximum loan amount significantly

        WHEN ALL DETAILS COLLECTED:
        - Check eligibility against rules
        - Calculate max loan amount considering:
        * EMI cap % of salary
        * MINUS existing EMIs already being paid
        * Net available EMI = (salary × EMI cap%) - existing EMIs
        * Max amount = Net available EMI × tenure months
        - Show clearly:
        ✅ Eligible criteria
        ❌ Failed criteria
        💰 Max loan amount you can get
        📋 Recommend document checklist

        EXAMPLE CALCULATION:
        Salary = Rs.2,00,000 | EMI cap = 50% | Existing EMI = Rs.30,000
        Net available EMI = Rs.1,00,000 - Rs.30,000 = Rs.70,000
        Max amount = Rs.70,000 × 48 months = Rs.33,60,000

        ELIGIBILITY RULES:
        {rules_context}

        IMPORTANT:
        - Scan full conversation before asking any question
        - If salary, age, CIBIL, EMI were mentioned earlier — use them
        - Only ask for what is genuinely missing
        - Always ask about existing EMIs — never skip this

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
             "eligibility_llm_response",
             f"length={len(response.content)}")

    return response.content


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 55)
    print("  Phase 5 — Eligibility Tool Test")
    print("=" * 55)

    TEST_SESSION = "TEST-PHASE5-ELIG-001"

    # Test 1 — Single turn with all details
    print("\n── Test 1: Single turn ────────────────────────────────")
    queries = [
        ("personal loan salary 35000 age 28 cibil 720 no emis", "new_customer"),
        ("home loan salary 45000 age 32 cibil 750",             "existing_customer"),
        ("credit card salary 15000 age 25",                     "new_customer"),
        ("vehicle loan salary 20000 age 30",                    "existing_customer"),
        ("can I get a loan",                                    "new_customer"),
    ]

    for query, persona in queries:
        print(f"\nQ [{persona}]: {query}")
        result = check_eligibility_with_llm(
            query, persona, TEST_SESSION, []
        )
        print(f"A: {result}")
        print("-" * 55)

    # Test 2 — Multi-turn conversation
    print("\n── Test 2: Multi-turn conversation ────────────────────")
    from langchain_core.messages import HumanMessage, AIMessage

    history = []

    turns = [
        "I want to check personal loan eligibility",
        "my salary is 30000 and age is 26",
        "my cibil score is 710",
        "I have no existing EMIs",
        "what is the maximum loan I can get?",
        "what if my cibil was 680?"
    ]

    for turn in turns:
        print(f"\nYou: {turn}")
        response = check_eligibility_with_llm(
            turn, "existing_customer", TEST_SESSION, history
        )
        print(f"Agent: {response}")
        history.append(HumanMessage(content=turn))
        history.append(AIMessage(content=response))
        print("-" * 55)
