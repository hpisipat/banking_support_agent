# observability/logger.py

import json
import os
import re
import random
from datetime import datetime

# Global flag — set to False to silence console logs
VERBOSE = False   # set to True when debugging


# ── PII Scrubber ──────────────────────────────────────────────────────────────

def scrub_pii(text):
    """
    Scans text and replaces any PII with redacted placeholders.
    Always call this before logging any user input.
    """
    text = str(text)

    # Mobile numbers — 10 digits
    text = re.sub(r'\b\d{10}\b',
                  '[MOBILE_REDACTED]', text)

    # Email addresses
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                  '[EMAIL_REDACTED]', text)

    # Account numbers — 12 digits
    text = re.sub(r'\b\d{12}\b',
                  '[ACCOUNT_REDACTED]', text)

    # Aadhaar — 12 digits with spaces (1234 5678 9012)
    text = re.sub(r'\b\d{4}\s\d{4}\s\d{4}\b',
                  '[AADHAAR_REDACTED]', text)

    # PAN card — format ABCDE1234F
    text = re.sub(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b',
                  '[PAN_REDACTED]', text)

    # Customer IDs — CUST-XXXXX
    text = re.sub(r'\bCUST-\d+\b',
                  '[CUSTOMER_ID_REDACTED]', text)

    return text


# ── Session ID Generator ──────────────────────────────────────────────────────

def generate_session_id():
    """
    Generates a unique session ID for each conversation.
    Format: SESS-YYYYMMDD-XXX
    """
    timestamp  = datetime.now().strftime("%Y%m%d")
    random_num = random.randint(100, 999)
    return f"SESS-{timestamp}-{random_num}"


# ── Core Log Function ─────────────────────────────────────────────────────────

def log_event(session_id, persona, event, details="", level="INFO"):
    """
    Writes one structured JSON log entry to logs/agent.log

    Parameters:
        session_id : unique ID for this conversation
        persona    : "new_customer" / "existing_customer" / "banker"
        event      : what happened e.g. "intent_detected"
        details    : extra info — always PII scrubbed before logging
        level      : "INFO" / "WARNING" / "ERROR"
    """

    # Auto-create logs folder if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Build the log entry as a dictionary
    log_entry = {
        "timestamp"  : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "session_id" : session_id,
        "persona"    : persona,
        "level"      : level,
        "event"      : event,
        "details"    : scrub_pii(str(details))
    }

    # Always write to file — "a" = append mode
    with open("logs/agent.log", "a") as log_file:
        log_file.write(json.dumps(log_entry) + "\n")

    # Only print to console if VERBOSE is True
    if VERBOSE:
        level_symbols = {
            "INFO"    : "ℹ️ ",
            "WARNING" : "⚠️ ",
            "ERROR"   : "❌"
        }
        symbol = level_symbols.get(level, "ℹ️ ")
        print(f"  {symbol} [{level}] {event} — {scrub_pii(str(details))}")


# ── Convenience Wrappers ──────────────────────────────────────────────────────

def log_info(session_id, persona, event, details=""):
    log_event(session_id, persona, event, details, level="INFO")

def log_warning(session_id, persona, event, details=""):
    log_event(session_id, persona, event, details, level="WARNING")

def log_error(session_id, persona, event, details=""):
    log_event(session_id, persona, event, details, level="ERROR")
