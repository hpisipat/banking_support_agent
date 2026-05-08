# memory/memory_manager.py
# Phase 6 — Long-term Memory
# Saves and loads user memory across sessions
# Non-sensitive data persisted — sensitive data cleared after session

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from observability.logger import log_info, log_warning

# ── Configuration ─────────────────────────────────────────────────────────────
MEMORY_DIR  = "memory"
MEMORY_FILE = os.path.join(MEMORY_DIR, "user_memory.json")

# ── What to remember vs forget ────────────────────────────────────────────────
# Sensitive — NEVER persisted, cleared after every session
SENSITIVE_KEYS = [
    "customer_id",
    "mobile",
    "email",
    "employee_id",
    "account_number"
]

# Non-sensitive — persisted across sessions
PERSISTENT_KEYS = [
    "persona",
    "preferred_area",
    "preferred_language",
    "products_enquired",
    "last_intent",
    "last_ticket_id",
    "session_count",
    "first_seen",
    "last_seen",
    "name",
    "ticket_ids"
]


# ── Helper — load all memory ──────────────────────────────────────────────────

def _load_all_memory():
    """Loads full memory store from disk"""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


# ── Helper — save all memory ──────────────────────────────────────────────────

def _save_all_memory(memory_store):
    """Saves full memory store to disk"""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(memory_store, f, indent=2)
    except Exception as e:
        log_warning("SYSTEM", "system", "memory_save_failed", str(e))


# ── Function 1 — Load user memory ────────────────────────────────────────────

def load_memory(session_id, persona):
    """
    Loads memory for this persona.
    Returns dict of remembered non-sensitive data.
    Returns empty dict for first-time users.
    """
    memory_store = _load_all_memory()
    memory       = memory_store.get(persona, {})

    if memory:
        log_info(session_id, persona, "memory_loaded",
                 f"session_count={memory.get('session_count', 0)} "
                 f"last_seen={memory.get('last_seen', 'never')}")
    else:
        log_info(session_id, persona, "memory_new_user",
                 "no previous memory found")

    return memory


# ── Function 2 — Update memory during session ─────────────────────────────────

def update_memory(session_id, persona, key, value):
    """
    Updates a single memory key during the session.
    Sensitive keys are silently ignored — never persisted.
    """
    if key in SENSITIVE_KEYS:
        log_info(session_id, persona, "memory_sensitive_skipped",
                 f"key={key} not persisted")
        return

    if key not in PERSISTENT_KEYS:
        log_warning(session_id, persona, "memory_unknown_key",
                    f"key={key} not in allowed keys")
        return

    memory_store          = _load_all_memory()
    memory                = memory_store.get(persona, {})
    memory[key]           = value
    memory_store[persona] = memory
    _save_all_memory(memory_store)

    log_info(session_id, persona, "memory_updated", f"key={key}")


# ── Function 3 — Save session memory on exit ──────────────────────────────────

def save_session_memory(session_id, persona, chat_history,
                        session_data={}):
    """
    Called at end of every session.
    Extracts useful non-sensitive info from conversation.
    Persists to memory file.
    Sensitive data is NEVER saved.

    Parameters:
        session_id   : current session ID
        persona      : user persona
        chat_history : full conversation history
        session_data : data collected during session
                       e.g. {"last_intent": "faq",
                             "products_enquired": ["personal_loan"]}
    """
    log_info(session_id, persona, "memory_save_started", "")

    memory_store = _load_all_memory()
    memory       = memory_store.get(persona, {})

    # Update session metadata
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if "first_seen" not in memory:
        memory["first_seen"] = now
    memory["last_seen"]     = now
    memory["persona"]       = persona
    memory["session_count"] = memory.get("session_count", 0) + 1

    # Persist non-sensitive session data
    for key, value in session_data.items():
        if key in SENSITIVE_KEYS:
            continue
        if key in PERSISTENT_KEYS:
            if isinstance(value, list):
                existing    = memory.get(key, [])
                memory[key] = list(set(existing + value))
            else:
                memory[key] = value

    # Extract info from chat history
    memory = _extract_from_history(memory, chat_history)

    # Final safety — ensure sensitive keys are NOT saved
    for key in SENSITIVE_KEYS:
        memory.pop(key, None)

    # Save
    memory_store[persona] = memory
    _save_all_memory(memory_store)

    log_info(session_id, persona, "memory_saved",
             f"session_count={memory['session_count']} "
             f"keys={list(memory.keys())}")

    return memory


# ── Helper — extract useful info from chat history ────────────────────────────

def _extract_from_history(memory, chat_history):
    """
    Scans conversation to extract memorable non-sensitive info.
    Products enquired and preferred area extracted automatically.
    """
    from langchain_core.messages import HumanMessage

    products_mentioned = []
    areas_mentioned    = []

    product_keywords = {
        "personal_loan"  : ["personal loan", "pl"],
        "home_loan"      : ["home loan", "housing loan"],
        "car_loan"       : ["car loan", "vehicle loan", "bike loan"],
        "credit_card"    : ["credit card"],
        "education_loan" : ["education loan", "student loan"],
        "savings_account": ["savings account", "saving account"],
        "fixed_deposit"  : ["fixed deposit", "fd"],
    }

    area_keywords = [
        "ameerpet", "kukatpally", "madhapur", "begumpet",
        "secunderabad", "banjara hills", "gachibowli",
        "mehdipatnam", "miyapur", "uppal", "dilsukhnagar"
    ]

    for msg in chat_history:
        if not isinstance(msg, HumanMessage):
            continue
        text = msg.content.lower()

        for product, keywords in product_keywords.items():
            if any(kw in text for kw in keywords):
                if product not in products_mentioned:
                    products_mentioned.append(product)

        for area in area_keywords:
            if area in text and area not in areas_mentioned:
                areas_mentioned.append(area)

    if products_mentioned:
        existing              = memory.get("products_enquired", [])
        memory["products_enquired"] = list(set(existing + products_mentioned))

    if areas_mentioned:
        memory["preferred_area"] = areas_mentioned[-1]

    return memory


# ── Function 4 — Build memory context for system prompt ──────────────────────

def build_memory_context(memory, persona):
    """
    Converts memory into natural language string.
    Injected into system prompt so LLM greets returning users warmly
    and references their history naturally.

    Returns empty string for new users.
    """
    if not memory:
        return ""

    lines = []

    if memory.get("session_count", 0) > 1:
        lines.append(
            f"Returning customer — visited {memory['session_count']} times. "
            f"Last seen: {memory.get('last_seen', 'unknown')}."
        )

    if memory.get("products_enquired"):
        products = ", ".join(memory["products_enquired"])
        lines.append(f"Previously enquired about: {products}.")

    if memory.get("preferred_area"):
        lines.append(
            f"Preferred area: {memory['preferred_area'].title()}."
        )

    if memory.get("last_ticket_id"):
        lines.append(
            f"Last complaint ticket: {memory['last_ticket_id']}."
        )

    if memory.get("last_intent"):
        lines.append(
            f"Last query type: {memory['last_intent'].replace('_', ' ')}."
        )

    if not lines:
        return ""

    context  = "\n    RETURNING CUSTOMER CONTEXT (use naturally in conversation):\n    "
    context += "\n    ".join(lines)
    return context


# ── Function 5 — Clear memory (for testing) ──────────────────────────────────

def clear_memory(persona=None):
    """Clears memory — used for testing only"""
    memory_store = _load_all_memory()
    if persona:
        memory_store.pop(persona, None)
        print(f"Memory cleared for: {persona}")
    else:
        memory_store = {}
        print("All memory cleared")
    _save_all_memory(memory_store)


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    from langchain_core.messages import HumanMessage, AIMessage

    print("=" * 55)
    print("  Phase 6 — Memory Manager Test")
    print("=" * 55)

    TEST_SESSION = "TEST-PHASE6-001"
    TEST_PERSONA = "existing_customer"

    clear_memory(TEST_PERSONA)

    # Test 1 — New user
    print("\n── Test 1: New User ───────────────────────────────────")
    memory = load_memory(TEST_SESSION, TEST_PERSONA)
    print(f"Memory: {memory}")
    print("Expected: empty dict")

    # Test 2 — Save session
    print("\n── Test 2: Save Session Memory ────────────────────────")
    mock_history = [
        HumanMessage(content="I want to check personal loan eligibility"),
        AIMessage(content="Sure, I can help..."),
        HumanMessage(content="salary 35000 age 28"),
        AIMessage(content="You appear eligible..."),
        HumanMessage(content="nearest branch to Ameerpet"),
        AIMessage(content="Ameerpet branch details..."),
    ]

    session_data = {
        "last_intent"      : "locator",
        "products_enquired": ["personal_loan"],
        "customer_id"      : "CUST-10234",  # sensitive — NOT saved
        "mobile"           : "9876543210",   # sensitive — NOT saved
    }

    saved = save_session_memory(
        TEST_SESSION, TEST_PERSONA,
        mock_history, session_data
    )
    print(f"Saved:\n{json.dumps(saved, indent=2)}")
    print("\n✅ customer_id and mobile should NOT appear above")

    # Test 3 — Load next session
    print("\n── Test 3: Load Memory Next Session ───────────────────")
    memory = load_memory("TEST-PHASE6-002", TEST_PERSONA)
    print(f"Loaded:\n{json.dumps(memory, indent=2)}")

    # Test 4 — Memory context for system prompt
    print("\n── Test 4: Memory Context ─────────────────────────────")
    context = build_memory_context(memory, TEST_PERSONA)
    print(f"Context injected into system prompt:\n{context}")

    # Test 5 — Session count increases
    print("\n── Test 5: Second Session Count ───────────────────────")
    save_session_memory("TEST-PHASE6-002", TEST_PERSONA, [], {})
    memory = load_memory("TEST-PHASE6-003", TEST_PERSONA)
    print(f"Session count: {memory.get('session_count')} (expected: 2)")

    print("\n✅ Check memory/user_memory.json for persisted data!")