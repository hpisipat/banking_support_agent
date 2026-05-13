# Phase 7 - Adaptive Behaviour

from datetime import datetime

from core.sqlite_store import load_feedback_map, load_feedback_record, save_feedback_record


def _log(session_id, persona, event, details):
    try:
        from observability.logger import log_info
        log_info(session_id, persona, event, details)
    except Exception:
        pass


def load_feedback(persona=None, user_id=None):
    if persona:
        return load_feedback_map(user_id, persona)
    return {}


def save_feedback(session_id, persona, intent, rating, comment="", user_id=None):
    feedback = load_feedback_record(user_id, persona, intent)

    feedback[rating] = feedback.get(rating, 0) + 1
    feedback["last_rated"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    if comment:
        comments = feedback.setdefault("comments", [])
        comments.append({
            "text": comment,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

    save_feedback_record(user_id, persona, intent, feedback)

    _log(session_id, persona, "feedback_saved",
         f"intent={intent} rating={rating} comment={bool(comment)}")


def get_feedback_style(persona, intent, user_id=None):
    data = load_feedback_record(user_id, persona, intent)

    positive = data.get("positive", 0)
    negative = data.get("negative", 0)
    total = positive + negative

    if total < 3:
        return "default"

    negative_rate = negative / total

    if negative_rate >= 0.6:
        return "detailed"
    if negative_rate <= 0.2:
        return "concise"
    return "balanced"


def get_recent_comments(persona, intent="session", limit=3, user_id=None):
    """Returns the most recent negative feedback comments for this user/persona."""
    feedback = load_feedback_record(user_id, persona, intent)
    comments = feedback.get("comments", [])
    return [entry["text"] for entry in reversed(comments[-limit:])]


def get_style_guidance(feedback_style, persona="", user_id=None):
    """
    Returns a system-prompt snippet that instructs the LLM how to adapt
    its response based on accumulated session feedback.
    """
    if feedback_style == "default":
        return ""

    comment_block = ""
    if persona:
        recent = get_recent_comments(persona, intent="session",
                                     limit=3, user_id=user_id)
        if recent:
            quoted = "\n".join(f'  - "{comment}"' for comment in recent)
            comment_block = (
                "\nPrevious feedback from this user - keep it in mind while responding:\n"
                f"{quoted}\n"
            )

    if feedback_style == "detailed":
        return f"""
ADDITIONAL GUIDANCE (based on user feedback - additive only):
- Give your complete normal response first
- Then add a brief example or clarification if it helps understanding
- Use plain language alongside any technical terms
- After your response, add: "Would you like me to clarify anything?"{comment_block}"""

    if feedback_style == "concise":
        return f"""
ADDITIONAL GUIDANCE (based on user feedback - additive only):
- Give your complete normal response
- This user has appreciated clear, direct answers in the past
- You may lead with the key point before the supporting details{comment_block}"""

    if feedback_style == "balanced":
        return f"""
ADDITIONAL GUIDANCE (based on user feedback - additive only):
- Give your complete normal response
- Structure it clearly with bullet points where appropriate{comment_block}"""

    return ""


def get_feedback_summary(persona, user_id=None):
    data = load_feedback_map(user_id, persona)

    if not data:
        return "No feedback collected yet."

    lines = [
        f"\nFeedback Summary - {persona.replace('_', ' ').title()}:\n"
        f"{'-' * 50}"
    ]

    for intent, scores in data.items():
        pos = scores.get("positive", 0)
        neg = scores.get("negative", 0)
        total = pos + neg
        pct = round((pos / total) * 100) if total > 0 else 0
        style = get_feedback_style(persona, intent, user_id=user_id)
        rated = scores.get("last_rated", "never")

        lines.append(
            f"  {intent:<22}: + {pos}  - {neg}  "
            f"({pct}% positive) -> style: {style} "
            f"| last: {rated}"
        )

    lines.append(f"{'-' * 50}")
    return "\n".join(lines)
