# observability/logger.py
# Async logging — single file, thread-safe, multi-user safe

import logging
import logging.handlers
import json
import os
import re
import random
import queue
import atexit

from datetime import datetime


# ── Configuration ─────────────────────────────────────────────────────────────
VERBOSE  = False
LOG_FILE = "logs/agent.log"

os.makedirs("logs", exist_ok=True)


# ── Async Logger Setup ────────────────────────────────────────────────────────

def _setup_logger():
    """
    Async logger using QueueHandler pattern.
    Single file, thread-safe, non-blocking.
    """
    logger = logging.getLogger("banking_agent")

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # File handler — single file, append mode
    file_handler = logging.FileHandler(
        filename = LOG_FILE,
        mode     = "a",
        encoding = "utf-8"
    )
    file_handler.setLevel(logging.DEBUG)

    # ✅ Key fix — write ONLY the message (our JSON string)
    # Without this, Python adds "INFO:banking_agent:" prefix
    # and may truncate or mangle our JSON content
    formatter = logging.Formatter("%(message)s")
    file_handler.setFormatter(formatter)

    # Queue — thread-safe in-memory buffer
    log_queue = queue.Queue(maxsize=0)

    # Queue handler — non-blocking, puts in queue instantly
    queue_handler = logging.handlers.QueueHandler(log_queue)
    queue_handler.setFormatter(formatter)   # ← apply to queue handler too
    logger.addHandler(queue_handler)

    # Queue listener — background thread reads queue, writes to file
    queue_listener = logging.handlers.QueueListener(
        log_queue,
        file_handler,
        respect_handler_level = True
    )
    queue_listener.start()
    logger._queue_listener = queue_listener

    atexit.register(queue_listener.stop)


    return logger


_logger = _setup_logger()


# ── PII Scrubber ──────────────────────────────────────────────────────────────

def scrub_pii(text):
    """Removes PII before logging — always called before any write"""
    text = str(text)
    text = re.sub(r'\b\d{10}\b',
                  '[MOBILE_REDACTED]',     text)
    text = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[EMAIL_REDACTED]',                text)
    text = re.sub(r'\b\d{12}\b',
                  '[ACCOUNT_REDACTED]',    text)
    text = re.sub(r'\b\d{4}\s\d{4}\s\d{4}\b',
                  '[AADHAAR_REDACTED]',    text)
    text = re.sub(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b',
                  '[PAN_REDACTED]',        text)
    text = re.sub(r'\bCUST-\d+\b',
                  '[CUSTOMER_ID_REDACTED]', text)
    return text


# ── Session ID Generator ──────────────────────────────────────────────────────

def generate_session_id():
    """Generates unique session ID — SESS-YYYYMMDD-XXX"""
    timestamp  = datetime.now().strftime("%Y%m%d")
    random_num = random.randint(100, 999)
    return f"SESS-{timestamp}-{random_num}"


# ── Core Log Function ─────────────────────────────────────────────────────────

def log_event(session_id, persona, event, details="", level="INFO"):
    """
    Writes structured JSON log entry asynchronously.

    Entry format:
    {
        "timestamp"  : "2024-04-12 10:30:45",
        "session_id" : "SESS-20240412-515",
        "persona"    : "existing_customer",
        "level"      : "INFO",
        "event"      : "faq_tool_called",
        "details"    : "what is minimum balance"
    }
    """

    log_entry = {
        "timestamp"  : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "session_id" : session_id,
        "persona"    : persona,
        "level"      : level,
        "event"      : event,
        "details"    : scrub_pii(str(details))
    }

    # Serialize full entry to JSON string
    log_line = json.dumps(log_entry)

    # Put in queue — non-blocking
    if level == "WARNING":
        _logger.warning(log_line)
    elif level == "ERROR":
        _logger.error(log_line)
    else:
        _logger.info(log_line)

    # Console output if VERBOSE
    if VERBOSE:
        symbols = {"INFO": "ℹ️ ", "WARNING": "⚠️ ", "ERROR": "❌"}
        symbol  = symbols.get(level, "ℹ️ ")
        print(f"  {symbol} [{level}] {event} "
              f"— {scrub_pii(str(details))}")


# ── Convenience Wrappers ──────────────────────────────────────────────────────

def log_info(session_id, persona, event, details=""):
    log_event(session_id, persona, event, details, level="INFO")

def log_warning(session_id, persona, event, details=""):
    log_event(session_id, persona, event, details, level="WARNING")

def log_error(session_id, persona, event, details=""):
    log_event(session_id, persona, event, details, level="ERROR")


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    import threading
    import time

    print("=" * 50)
    print("  Logger Test — Verifying details field")
    print("=" * 50)

    session = generate_session_id()

    # Test with actual details
    log_info(session, "existing_customer",
             "user_message",
             "what is minimum balance for savings account?")

    log_info(session, "existing_customer",
             "intent_detected", "faq")

    log_info(session, "existing_customer",
             "faq_tool_called",
             "what is minimum balance for savings account?")

    log_info(session, "existing_customer",
             "faq_chunks_retrieved", "count=3")

    log_info(session, "existing_customer",
             "faq_answer_generated", "length=312")

    log_warning(session, "existing_customer",
                "guardrail_triggered",
                "transfer money to my friend")

    log_error(session, "existing_customer",
              "tool_failed",
              "account_inquiry failed after 3 retries")

    # PII test — verify scrubbing
    log_info(session, "existing_customer",
             "user_message",
             "my mobile is 9876543210 and email ravi@gmail.com")

    time.sleep(0.5)   # flush queue

    print(f"\n✅ Check logs/agent.log")
    print("   You should see 'details' field populated for each entry")

    # Print log file content
    print("\n── Log File Contents ──────────────────────────────")
    with open(LOG_FILE, "r") as f:
        for line in f:
            entry = json.loads(line.strip())
            print(f"\nEvent   : {entry['event']}")
            print(f"Level   : {entry['level']}")
            print(f"Details : {entry['details']}")
            print(f"Session : {entry['session_id']}")