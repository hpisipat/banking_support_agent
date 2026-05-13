# Phase 6 - Long-term Memory
# Saves and loads user memory across sessions
# Non-sensitive data persisted - sensitive data cleared after session

from datetime import datetime

from core.sqlite_store import clear_memory_records, load_memory_record, save_memory_record
from observability.logger import log_info, log_warning

# Sensitive - NEVER persisted, cleared after every session
SENSITIVE_KEYS = [
    "customer_id",
    "mobile",
    "email",
    "employee_id",
    "account_number"
]

# Non-sensitive - persisted across sessions
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


def load_memory(session_id, persona, user_id=None):
    """
    Loads memory for this user/persona pair.
    Returns dict of remembered non-sensitive data.
    Returns empty dict for first-time users.
    """
    memory = load_memory_record(user_id, persona)

    if memory:
        log_info(session_id, persona, "memory_loaded",
                 f"session_count={memory.get('session_count', 0)} "
                 f"last_seen={memory.get('last_seen', 'never')}")
    else:
        log_info(session_id, persona, "memory_new_user",
                 "no previous memory found")

    return memory


def update_memory(session_id, persona, key, value, user_id=None):
    """
    Updates a single memory key during the session.
    Sensitive keys are silently ignored - never persisted.
    """
    if key in SENSITIVE_KEYS:
        log_info(session_id, persona, "memory_sensitive_skipped",
                 f"key={key} not persisted")
        return

    if key not in PERSISTENT_KEYS:
        log_warning(session_id, persona, "memory_unknown_key",
                    f"key={key} not in allowed keys")
        return

    memory = load_memory_record(user_id, persona)
    memory[key] = value
    save_memory_record(user_id, persona, memory)

    log_info(session_id, persona, "memory_updated", f"key={key}")


def save_session_memory(session_id, persona, chat_history,
                        session_data=None, user_id=None,
                        increment_session_count=True):
    """
    Called at end of every session or during periodic autosave.
    Extracts useful non-sensitive info from conversation.
    Persists to SQLite.
    Sensitive data is NEVER saved.
    """
    log_info(session_id, persona, "memory_save_started", "")

    session_data = session_data or {}
    memory = load_memory_record(user_id, persona)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if "first_seen" not in memory:
        memory["first_seen"] = now
    memory["last_seen"] = now
    memory["persona"] = persona
    if increment_session_count:
        memory["session_count"] = memory.get("session_count", 0) + 1
    else:
        memory["session_count"] = memory.get("session_count", 0)

    for key, value in session_data.items():
        if key in SENSITIVE_KEYS:
            continue
        if key in PERSISTENT_KEYS:
            if isinstance(value, list):
                existing = memory.get(key, [])
                memory[key] = list(set(existing + value))
            else:
                memory[key] = value

    memory = _extract_from_history(memory, chat_history)

    for key in SENSITIVE_KEYS:
        memory.pop(key, None)

    save_memory_record(user_id, persona, memory)

    log_info(session_id, persona, "memory_saved",
             f"session_count={memory.get('session_count', 0)} "
             f"keys={list(memory.keys())}")

    return memory


def _extract_from_history(memory, chat_history):
    """
    Scans conversation to extract memorable non-sensitive info.
    Products enquired and preferred area extracted automatically.
    """
    from langchain_core.messages import HumanMessage

    products_mentioned = []
    areas_mentioned = []

    product_keywords = {
        "personal_loan": ["personal loan", "pl"],
        "home_loan": ["home loan", "housing loan"],
        "car_loan": ["car loan", "vehicle loan", "bike loan"],
        "credit_card": ["credit card"],
        "education_loan": ["education loan", "student loan"],
        "savings_account": ["savings account", "saving account"],
        "fixed_deposit": ["fixed deposit", "fd"],
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
        existing = memory.get("products_enquired", [])
        memory["products_enquired"] = list(set(existing + products_mentioned))

    if areas_mentioned:
        memory["preferred_area"] = areas_mentioned[-1]

    return memory


def build_memory_context(memory, persona):
    """
    Converts memory into natural language string.
    Injected into system prompt so LLM greets returning users warmly
    and references their history naturally.
    """
    if not memory:
        return ""

    lines = []

    if memory.get("session_count", 0) > 1:
        lines.append(
            f"Returning customer - visited {memory['session_count']} times. "
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

    context = "\n    RETURNING CUSTOMER CONTEXT (use naturally in conversation):\n    "
    context += "\n    ".join(lines)
    return context


def clear_memory(persona=None, user_id=None):
    """Clears memory - used for testing only."""
    clear_memory_records(user_id=user_id, persona=persona)
    if user_id and persona:
        print(f"Memory cleared for user={user_id}, persona={persona}")
    elif persona:
        print(f"Memory cleared for persona={persona}")
    else:
        print("All memory cleared")
