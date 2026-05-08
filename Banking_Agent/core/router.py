# core/router.py

INTENT_KEYWORDS = {
    "faq"                : ["what is", "what are", "how much", "policy",
                            "interest rate", "charges", "fee",
                            "minimum balance", "rules", "min", "bal"],
    "document_checklist" : ["document", "checklist", "how to", "process",
                            "steps", "enable", "apply", "open account"],
    "eligibility"        : ["eligible", "eligibility", "qualify",
                            "salary", "cibil", "income", "can i get"],
    "complaint"          : ["complaint", "complain", "failed", "issue",
                            "problem", "wrong", "deducted", "raise", "ticket"],
    "locator"            : ["branch", "atm", "near", "nearest", "around",
                            "where", "address", "timing", "locate"],
    "account_inquiry"    : ["account", "acct", "kyc", "my account",
                            "statement", "details", "deposit", "card", "emi"]
}


def detect_intent(user_message):
    """
    Scans user message for keywords and returns matched intent.
    Returns 'unknown' if no intent is detected.
    """
    message = user_message.lower()

    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in message:
                return intent

    return "unknown"
