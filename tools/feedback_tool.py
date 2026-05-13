# tools/feedback_tool.py
# Phase 7 — Adaptive Behaviour

import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FEEDBACK_FILE = "data/feedback.json"


def _log(session_id, persona, event, details):
    try:
        from observability.logger import log_info
        log_info(session_id, persona, event, details)
    except Exception:
        pass


def load_feedback():
    if not os.path.exists(FEEDBACK_FILE):
        return {}
    try:
        with open(FEEDBACK_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_feedback(session_id, persona, intent, rating, comment=""):
    feedback = load_feedback()

    if persona not in feedback:
        feedback[persona] = {}

    if intent not in feedback[persona]:
        feedback[persona][intent] = {
            "positive"  : 0,
            "negative"  : 0,
            "comments"  : [],
            "last_rated": None
        }

    feedback[persona][intent][rating]      += 1
    feedback[persona][intent]["last_rated"] = (
        datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    if comment:
        feedback[persona][intent].setdefault("comments", []).append({
            "text"     : comment,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

    os.makedirs("data", exist_ok=True)
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(feedback, f, indent=2)

    _log(session_id, persona, "feedback_saved",
         f"intent={intent} rating={rating} comment={bool(comment)}")


def get_feedback_style(persona, intent):
    feedback = load_feedback()
    data     = feedback.get(persona, {}).get(intent, {})

    positive = data.get("positive", 0)
    negative = data.get("negative", 0)
    total    = positive + negative

    if total < 3:
        return "default"

    negative_rate = negative / total

    if negative_rate >= 0.6:
        return "detailed"
    elif negative_rate <= 0.2:
        return "concise"
    else:
        return "balanced"


def get_recent_comments(persona, intent="session", limit=3):
    """Returns the most recent negative feedback comments for this persona."""
    feedback = load_feedback()
    comments = (feedback.get(persona, {})
                        .get(intent, {})
                        .get("comments", []))
    # Most recent first, capped at limit
    return [c["text"] for c in reversed(comments[-limit:])]


def get_style_guidance(feedback_style, persona=""):
    """
    Returns a system-prompt snippet that instructs the LLM how to adapt
    its response based on accumulated session feedback.
    Includes recent negative comments so the LLM knows specifically
    what users found unhelpful.
    Injected into every tool's system prompt.
    """
    if feedback_style == "default":
        return ""

    # Pull recent negative comments to give the LLM concrete context
    comment_block = ""
    if persona:
        recent = get_recent_comments(persona, intent="session")
        if recent:
            quoted = "\n".join(f'  - "{c}"' for c in recent)
            comment_block = (f"\nPrevious users left this feedback — "
                             f"keep it in mind while responding:\n{quoted}\n")

    # All styles are ADDITIVE — the full base response is always given.
    # These instructions only ADD to the response, never remove content.
    if feedback_style == "detailed":
        return f"""
ADDITIONAL GUIDANCE (based on user feedback — additive only):
- Give your complete normal response first
- Then add a brief example or clarification if it helps understanding
- Use plain language alongside any technical terms
- After your response, add: "Would you like me to clarify anything?"{comment_block}"""

    elif feedback_style == "concise":
        return f"""
ADDITIONAL GUIDANCE (based on user feedback — additive only):
- Give your complete normal response
- Users have appreciated clear, direct answers in the past
- You may lead with the key point before the supporting details{comment_block}"""

    elif feedback_style == "balanced":
        return f"""
ADDITIONAL GUIDANCE (based on user feedback — additive only):
- Give your complete normal response
- Structure it clearly with bullet points where appropriate{comment_block}"""

    return ""


def get_feedback_summary(persona):
    feedback = load_feedback()
    data     = feedback.get(persona, {})

    if not data:
        return "No feedback collected yet."

    lines = [f"\nFeedback Summary — "
             f"{persona.replace('_', ' ').title()}:\n"
             f"{'─'*50}"]

    for intent, scores in data.items():
        pos   = scores.get("positive", 0)
        neg   = scores.get("negative", 0)
        total = pos + neg
        pct   = round((pos / total) * 100) if total > 0 else 0
        style = get_feedback_style(persona, intent)
        rated = scores.get("last_rated", "never")

        lines.append(
            f"  {intent:<22}: "
            f"👍 {pos}  👎 {neg}  "
            f"({pct}% positive) "
            f"→ style: {style} "
            f"| last: {rated}"
        )

    lines.append(f"{'─'*50}")
    return "\n".join(lines)


if __name__ == "__main__":

    print("=" * 55)
    print("  Phase 7 — Feedback Tool Test")
    print("=" * 55)

    TEST_SESSION = "TEST-PHASE7-001"
    TEST_PERSONA = "existing_customer"

    # Clear for clean test
    if os.path.exists(FEEDBACK_FILE):
        os.remove(FEEDBACK_FILE)
    print(f"\n✅ Cleared feedback file for clean test")

    # Test 1
    print("\n── Test 1: Less than 3 feedbacks → default ────────────")
    save_feedback(TEST_SESSION, TEST_PERSONA, "faq", "negative")
    save_feedback(TEST_SESSION, TEST_PERSONA, "faq", "negative")
    style = get_feedback_style(TEST_PERSONA, "faq")
    print(f"Style after 2 feedbacks : {style}")
    print(f"Expected                : default")
    print("✅ PASS" if style == "default" else f"❌ FAIL got {style}")

    # Test 2
    print("\n── Test 2: 3+ negative feedbacks → detailed ───────────")
    save_feedback(TEST_SESSION, TEST_PERSONA, "faq", "negative")
    style = get_feedback_style(TEST_PERSONA, "faq")
    print(f"Style after 3 negative  : {style}")
    print(f"Expected                : detailed")
    print("✅ PASS" if style == "detailed" else f"❌ FAIL got {style}")

    # Test 3
    print("\n── Test 3: Mostly positive → concise ──────────────────")
    for _ in range(5):
        save_feedback(TEST_SESSION, TEST_PERSONA, "eligibility", "positive")
    style = get_feedback_style(TEST_PERSONA, "eligibility")
    print(f"Style after 5 positive  : {style}")
    print(f"Expected                : concise")
    print("✅ PASS" if style == "concise" else f"❌ FAIL got {style}")

    # Test 4
    print("\n── Test 4: Mixed feedback → balanced ──────────────────")
    for _ in range(2):
        save_feedback(TEST_SESSION, TEST_PERSONA, "locator", "positive")
    for _ in range(2):
        save_feedback(TEST_SESSION, TEST_PERSONA, "locator", "negative")
    style = get_feedback_style(TEST_PERSONA, "locator")
    print(f"Style after 2+2 mixed   : {style}")
    print(f"Expected                : balanced")
    print("✅ PASS" if style == "balanced" else f"❌ FAIL got {style}")

    # Test 5
    print("\n── Test 5: Feedback Summary ────────────────────────────")
    print(get_feedback_summary(TEST_PERSONA))

    # Verify file exists
    print(f"\n── File check ──────────────────────────────────────────")
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE) as f:
            data = json.load(f)
        print(f"✅ {FEEDBACK_FILE} exists")
        print(f"   Personas : {list(data.keys())}")
        print(f"   Intents  : {list(data.get(TEST_PERSONA, {}).keys())}")
    else:
        print(f"❌ {FEEDBACK_FILE} not found — save_feedback() failed")