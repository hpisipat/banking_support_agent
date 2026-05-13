# tests/prompt_comparison.py

import sys
import os

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai        import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from core.llm_agent          import build_system_prompt
from dotenv import load_dotenv


load_dotenv()

# ── Test question — same for all 3 strategies ─────────────────────────────────
TEST_QUESTION = "can I get a home loan with 40000 salary?"
PERSONA       = "existing_customer"

llm = ChatOpenAI(model="gpt-4o", temperature=0)


# ── Strategy 1 — Zero Shot ────────────────────────────────────────────────────
def test_zero_shot():
    """
    No system prompt, no examples.
    Just the raw question sent to GPT-4o.
    """
    response = llm.invoke([
        HumanMessage(content=TEST_QUESTION)
    ])
    return response.content


# ── Strategy 2 — System Prompt ────────────────────────────────────────────────
def test_system_prompt():
    """
    With banking system prompt — persona aware, rules enforced.
    This is what we built in Phase 3.
    """
    response = llm.invoke([
        SystemMessage(content=build_system_prompt(PERSONA)),
        HumanMessage(content=TEST_QUESTION)
    ])
    return response.content


# ── Strategy 3 — Few Shot ─────────────────────────────────────────────────────
def test_few_shot():
    """
    System prompt + example conversation before the real question.
    Shows LLM what a good answer looks like.
    """
    response = llm.invoke([
        SystemMessage(content=build_system_prompt(PERSONA)),

        # Example 1 — show LLM what a good answer looks like
        HumanMessage(content="can I get a personal loan with 25000 salary?"),
        AIMessage(content="""Based on your salary of Rs.25,000 per month,
here is the eligibility summary for a Personal Loan:

✅ Minimum salary requirement   : Rs.25,000 — You meet this
📊 CIBIL score required         : Minimum 700
📋 Employment type              : Salaried or self-employed
💰 EMI cap                      : Your total EMIs should not 
                                   exceed 50% of salary (Rs.12,500)

Next steps:
1. Check your CIBIL score at www.cibil.com
2. Visit your nearest branch with salary slips
3. Our team will assess your full application"""),

        # Example 2
        HumanMessage(content="what about credit card eligibility?"),
        AIMessage(content="""For a Credit Card with your salary of Rs.25,000:

✅ Minimum salary requirement   : Rs.15,000 — You meet this
📊 CIBIL score required         : Minimum 700
📋 Age requirement              : 18 to 65 years
💳 Existing cards allowed       : Maximum 3 active cards

You appear eligible! Next steps:
1. Visit nearest branch or apply online
2. Carry salary slips and KYC documents"""),

        # Now the actual question
        HumanMessage(content=TEST_QUESTION)
    ])
    return response.content


# ── Run all 3 and compare ─────────────────────────────────────────────────────

if __name__ == "__main__":

    print("=" * 60)
    print("  Phase 3 — Prompt Strategy Comparison")
    print(f"  Test Question: '{TEST_QUESTION}'")
    print("=" * 60)

    print("\n── Strategy 1: Zero Shot ──────────────────────────────")
    r1 = test_zero_shot()
    print(r1)

    print("\n── Strategy 2: System Prompt ──────────────────────────")
    r2 = test_system_prompt()
    print(r2)

    print("\n── Strategy 3: Few Shot ───────────────────────────────")
    r3 = test_few_shot()
    print(r3)

    print("\n── Summary ────────────────────────────────────────────")
    print("""
    Strategy         | Banking Focus | Persona Aware | Structured
    ─────────────────|───────────────|───────────────|───────────
    Zero Shot        | ❌ Generic    | ❌ No         | ❌ No
    System Prompt    | ✅ Yes        | ✅ Yes        | ✅ Yes
    Few Shot         | ✅ Yes        | ✅ Yes        | ✅ Best

    Selected Strategy: Few Shot + System Prompt
    Reason: Most structured, banking-specific, persona-aware responses
    """)