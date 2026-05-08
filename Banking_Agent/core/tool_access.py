# core/tool_access.py
# Role-based tool access control
# Each persona gets access only to permitted tools
# Agent is architecturally incapable of calling unauthorised tools

# ── Tool Access Matrix ────────────────────────────────────────────────────────
TOOL_ACCESS = {
    "new_customer"      : [
        "faq",
        "document_checklist",
        "eligibility",
        "locator"
    ],
    "existing_customer" : [
        "faq",
        "document_checklist",
        "eligibility",
        "locator",
        "complaint",
        "account_inquiry"
    ],
    "banker"            : [
        "faq",
        "document_checklist",
        "eligibility",
        "locator",
        "complaint",
        "account_inquiry",
        "zone_directory"
    ]
}


def is_tool_allowed(intent, persona):
    """
    Returns True if persona is allowed to use this tool.
    Called before every tool invocation.

    Parameters:
        intent  : detected intent / tool name
        persona : new_customer / existing_customer / banker

    Returns:
        True if allowed, False if not
    """
    allowed = TOOL_ACCESS.get(persona, [])
    return intent in allowed


def get_allowed_tools(persona):
    """
    Returns list of tools allowed for this persona.
    Used to inform user what help is available.
    """
    return TOOL_ACCESS.get(persona, [])


def get_access_denied_message(intent, persona):
    """
    Returns appropriate message when access is denied.
    Persona-aware — explains why access is restricted.
    """
    if persona == "new_customer":
        if intent == "account_inquiry":
            return ("As a new customer you don't have an account yet. "
                    "Would you like help opening one? I can guide you "
                    "through the process and documents needed.")
        if intent == "complaint":
            return ("Complaint logging is available for existing customers. "
                    "If you faced an issue during account opening, "
                    "please visit your nearest branch or call 1800-XXX-XXXX.")
        return ("This feature is available for existing customers only. "
                "Would you like help with account opening or "
                "product information?")

    return ("You don't have access to this feature. "
            "Please contact your branch for assistance.")
