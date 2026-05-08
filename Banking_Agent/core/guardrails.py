# core/guardrails.py

BLOCKED_KEYWORDS = [
    "transfer", "send money", "pay bill", "pay",
    "reset pin", "change password", "close account",
    "buy", "disburse", "otp"
]

OUT_OF_SCOPE_KEYWORDS = [
    "weather", "cricket", "recipe", "movie",
    "vacation", "trip", "news", "joke"
]

ABUSIVE_KEYWORDS = [
    "idiot", "stupid", "useless", "worst bank",
    "pathetic", "rubbish", "hate"
]


def is_transaction_request(message):
    """Returns True if message contains transactional intent"""
    for keyword in BLOCKED_KEYWORDS:
        if keyword in message:
            return True
    return False


def is_out_of_scope(message):
    """Returns True if message is clearly not banking related"""
    for keyword in OUT_OF_SCOPE_KEYWORDS:
        if keyword in message:
            return True
    return False


def is_abusive(message):
    """Returns True if message contains abusive language"""
    for keyword in ABUSIVE_KEYWORDS:
        if keyword in message:
            return True
    return False


def check_guardrails(message):
    """
    Master function — runs all 3 checks in order.
    Returns tuple: (is_blocked, response_message)
    """
    message = message.lower()

    if is_transaction_request(message):
        return (True,
                "I'm sorry, I cannot process transactions. "
                "Please use net banking, mobile app, or visit "
                "your nearest branch for this request.")

    if is_out_of_scope(message):
        return (True,
                "I'm a banking support assistant. I can help "
                "with accounts, loans, complaints, branch "
                "locations, documents, and FAQs.")

    if is_abusive(message):
        return (True,
                "I understand you may be frustrated. "
                "I'm here to help — please share your "
                "banking query and I'll do my best.")

    return (False, None)
