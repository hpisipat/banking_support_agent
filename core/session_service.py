import json
from dataclasses import dataclass, field
from threading import RLock
from typing import Dict, List

from langchain_core.messages import AIMessage, HumanMessage

from core.guardrails import check_guardrails
from core.llm_agent import detect_intent_llm, get_llm_response
from core.router import detect_intent
from core.sqlite_store import load_session_record, save_session_record
from core.tool_access import get_access_denied_message, is_tool_allowed
from llm_agent_runner import (
    MAX_RETRIES,
    is_conversation_ending,
    is_small_talk,
    route_to_tool,
    track_products,
    track_ticket_id,
)
from memory.memory_manager import build_memory_context, load_memory, save_session_memory
from observability.logger import generate_session_id, log_error, log_info, log_warning
from tools.feedback_tool import get_feedback_style, save_feedback

VALID_PERSONAS = {"new_customer", "existing_customer", "banker"}

WELCOME_NEW = (
    "Hi! Welcome to Banking Support.\n\n"
    "I can help you with:\n"
    "- Document checklists & process guides\n"
    "- Loan & credit card eligibility\n"
    "- Banking FAQs & policies\n"
    "- Complaint logging & tracking\n"
    "- Branch & ATM locations\n"
    "- Account details"
)

WELCOME_RETURNING = (
    "Welcome back! Great to have you again.\n"
    "{history_line}\n"
    "How can I help you today?"
)

GOODBYE = "Thank you for contacting us.\nHave a great day! Goodbye!"

GENERIC_HELP = (
    "I'd be happy to help. I can assist with:\n"
    "- Opening accounts or applying for loans\n"
    "- Loan / credit card eligibility\n"
    "- Banking FAQs and policies\n"
    "- Raising or tracking complaints\n"
    "- Nearest branch or ATM\n"
    "- Account details\n\n"
    "Could you tell me more about what you need?"
)


@dataclass
class SessionState:
    session_id: str
    user_id: str
    persona: str
    chat_history: List[object] = field(default_factory=list)
    retry_count: int = 0
    last_intent: str = "unknown"
    session_data: Dict[str, object] = field(default_factory=lambda: {
        "products_enquired": [],
        "last_intent": "unknown",
        "ticket_ids": []
    })
    memory: Dict[str, object] = field(default_factory=dict)
    memory_context: str = ""
    is_returning: bool = False
    ended: bool = False
    created_at: str = ""


class SessionManager:
    def __init__(self):
        self._lock = RLock()

    def create_session(self, persona: str, user_id: str) -> Dict[str, object]:
        if persona not in VALID_PERSONAS:
            raise ValueError(f"Unsupported persona: {persona}")

        if not (user_id or "").strip():
            raise ValueError("user_id is required.")

        session_id = generate_session_id()
        memory = load_memory(session_id, persona, user_id=user_id)
        memory_context = build_memory_context(memory, persona)
        is_returning = memory.get("session_count", 0) > 0

        state = SessionState(
            session_id=session_id,
            user_id=user_id.strip(),
            persona=persona,
            memory=memory,
            memory_context=memory_context,
            is_returning=is_returning
        )

        with self._lock:
            self._save_state(state)

        log_info(session_id, persona, "session_started",
                 f"user_id={user_id} persona={persona} returning={is_returning}")

        return {
            "session_id": session_id,
            "user_id": state.user_id,
            "persona": persona,
            "is_returning": is_returning,
            "visits": memory.get("session_count", 0) + 1,
            "greeting": self._build_greeting(state)
        }

    def process_message(self, session_id: str, user_message: str) -> Dict[str, object]:
        user_message = user_message.strip()
        if not user_message:
            raise ValueError("Message cannot be empty.")

        with self._lock:
            state = self._load_state(session_id)
            if state.ended:
                raise ValueError("This session has already ended.")

            log_info(state.session_id, state.persona, "user_message", user_message)

            if is_small_talk(user_message, state.chat_history):
                log_info(state.session_id, state.persona, "small_talk", user_message)
                self._save_state(state)
                return self._result(
                    response="You're welcome! Is there anything else I can help you with?"
                )

            is_blocked, block_message = check_guardrails(user_message)
            if is_blocked:
                log_warning(state.session_id, state.persona, "guardrail_triggered", user_message)
                self._save_state(state)
                return self._result(response=block_message)

            intent = "unknown"
            try:
                intent = detect_intent_llm(user_message)
                log_info(state.session_id, state.persona, "intent_detected_llm", intent)
                state.retry_count = 0
            except Exception as exc:
                state.retry_count += 1
                log_error(state.session_id, state.persona, "intent_llm_failed",
                          f"attempt={state.retry_count} error={str(exc)}")
                intent = detect_intent(user_message)
                log_info(state.session_id, state.persona, "intent_detected_fallback", intent)

            if intent == "unknown" and is_conversation_ending(user_message, state.chat_history):
                result = self._end_session_locked(state, "natural_ending")
                self._save_state(state)
                return result

            if intent == "unknown" and state.last_intent != "unknown":
                intent = self._continue_last_intent(state, user_message)

            if intent != "unknown" and not is_tool_allowed(intent, state.persona):
                log_warning(state.session_id, state.persona, "access_denied",
                            f"intent={intent} persona={state.persona}")
                self._save_state(state)
                return self._result(response=get_access_denied_message(intent, state.persona))

            if intent == "unknown":
                result = self._handle_unknown_locked(state, user_message)
                self._save_state(state)
                return result

            feedback_style = get_feedback_style(
                state.persona, "session", user_id=state.user_id
            )
            log_info(state.session_id, state.persona, "feedback_style_applied",
                     f"intent={intent} style={feedback_style}")

            log_info(state.session_id, state.persona, "intent_confirmed", intent)
            try:
                response = route_to_tool(
                    intent=intent,
                    user_message=user_message,
                    persona=state.persona,
                    session_id=state.session_id,
                    chat_history=state.chat_history,
                    memory_context=state.memory_context,
                    session_data=state.session_data,
                    memory=state.memory,
                    feedback_style=feedback_style,
                    user_id=state.user_id
                )
                log_info(state.session_id, state.persona, "agent_response",
                         f"intent={intent} style={feedback_style} length={len(response)}")
                state.last_intent = intent
                state.retry_count = 0

                track_products(user_message, response,
                               state.session_data, state.session_id, state.persona)
                if intent == "complaint":
                    track_ticket_id(response, state.session_data, state.session_id, state.persona)

                self._append_turn_locked(state, user_message, response)
                self._save_state(state)
                return self._result(response=response, intent=intent)
            except Exception as exc:
                state.retry_count += 1
                log_error(state.session_id, state.persona, "tool_failed",
                          f"intent={intent} attempt={state.retry_count} error={str(exc)}")
                if state.retry_count >= MAX_RETRIES:
                    log_error(state.session_id, state.persona, "max_retries_exceeded",
                              f"intent={intent}")
                    state.retry_count = 0
                    state.last_intent = "unknown"
                    self._save_state(state)
                    return self._result(
                        response=(
                            "I'm unable to process your request right now.\n"
                            "Please visit your nearest branch or call us at 1800-XXX-XXXX."
                        ),
                        intent=intent
                    )
                self._save_state(state)
                return self._result(
                    response="I encountered an issue. Please try again.",
                    intent=intent
                )

    def end_session(self, session_id: str) -> Dict[str, object]:
        with self._lock:
            state = self._load_state(session_id)
            result = self._end_session_locked(state, "api_end")
            self._save_state(state)
            return result

    def submit_feedback(self, session_id: str, rating: str, comment: str = "") -> Dict[str, str]:
        if rating not in {"positive", "negative"}:
            raise ValueError("Rating must be 'positive' or 'negative'.")

        with self._lock:
            state = self._load_state(session_id)
            save_feedback(
                state.session_id,
                state.persona,
                "session",
                rating,
                comment=comment,
                user_id=state.user_id
            )
            self._save_state(state)
            return {"message": "Feedback saved. Thank you!"}

    def close_session(self, session_id: str) -> None:
        # Session rows are persisted intentionally so completed sessions survive restarts.
        _ = session_id

    def _load_state(self, session_id: str) -> SessionState:
        record = load_session_record(session_id)
        if not record:
            raise KeyError(f"Session not found: {session_id}")

        return SessionState(
            session_id=record["session_id"],
            user_id=record["user_id"],
            persona=record["persona"],
            chat_history=self._deserialize_history(record["chat_history"]),
            retry_count=record["retry_count"],
            last_intent=record["last_intent"],
            session_data=json.loads(record["session_data"] or "{}"),
            memory=json.loads(record["memory_json"] or "{}"),
            memory_context=record["memory_context"] or "",
            is_returning=bool(record["is_returning"]),
            ended=bool(record["ended"]),
            created_at=record["created_at"]
        )

    def _save_state(self, state: SessionState) -> None:
        save_session_record({
            "session_id": state.session_id,
            "user_id": state.user_id,
            "persona": state.persona,
            "chat_history": self._serialize_history(state.chat_history),
            "retry_count": state.retry_count,
            "last_intent": state.last_intent,
            "session_data": json.dumps(state.session_data),
            "memory_json": json.dumps(state.memory),
            "memory_context": state.memory_context,
            "is_returning": state.is_returning,
            "ended": state.ended,
            "created_at": state.created_at
        })

    def _build_greeting(self, state: SessionState) -> str:
        if state.is_returning:
            products = state.memory.get("products_enquired", [])
            history_line = (
                f"Last time you enquired about: {', '.join(products)}."
                if products else
                "I'm ready to continue where we left off."
            )
            return WELCOME_RETURNING.format(history_line=history_line)
        return WELCOME_NEW

    def _continue_last_intent(self, state: SessionState, user_message: str) -> str:
        if len(user_message.split()) <= 15:
            eligibility_signals = [
                "eligible", "eligibility", "qualify",
                "can i get", "will i get", "am i"
            ]
            message_lower = user_message.lower()

            if any(signal in message_lower for signal in eligibility_signals):
                intent = "eligibility"
                log_info(state.session_id, state.persona,
                         "intent_override_eligibility",
                         f"from={state.last_intent} message='{user_message}'")
                return intent

            log_info(state.session_id, state.persona, "intent_continued",
                     f"last_intent={state.last_intent} reply='{user_message}'")
            return state.last_intent

        return "unknown"

    def _handle_unknown_locked(self, state: SessionState, user_message: str) -> Dict[str, object]:
        log_warning(state.session_id, state.persona, "intent_unknown", user_message)

        if state.chat_history:
            try:
                response = get_llm_response(
                    user_message,
                    state.persona,
                    state.chat_history,
                    state.memory_context,
                    user_id=state.user_id
                )
                log_info(state.session_id, state.persona, "agent_response",
                         f"intent=llm_contextual length={len(response)}")
                self._append_turn_locked(state, user_message, response)
                return self._result(response=response)
            except Exception as exc:
                log_error(state.session_id, state.persona,
                          "llm_contextual_failed", str(exc))
                return self._result(response="Could you please rephrase that?")

        return self._result(response=GENERIC_HELP)

    def _append_turn_locked(self, state: SessionState, user_message: str, response: str) -> None:
        state.chat_history.append(HumanMessage(content=user_message))
        state.chat_history.append(AIMessage(content=response))
        if len(state.chat_history) > 20:
            state.chat_history = state.chat_history[-20:]
            log_info(state.session_id, state.persona, "history_trimmed",
                     "kept last 10 turns")

        if len(state.chat_history) % 6 == 0:
            state.session_data["last_intent"] = state.last_intent
            state.memory = save_session_memory(
                state.session_id,
                state.persona,
                state.chat_history,
                state.session_data,
                user_id=state.user_id,
                increment_session_count=False
            )
            state.memory_context = build_memory_context(state.memory, state.persona)
            log_info(state.session_id, state.persona,
                     "memory_auto_saved",
                     f"turns={len(state.chat_history)//2}")

    def _end_session_locked(self, state: SessionState, reason: str) -> Dict[str, object]:
        if not state.ended:
            state.session_data["last_intent"] = state.last_intent
            state.memory = save_session_memory(
                state.session_id,
                state.persona,
                state.chat_history,
                state.session_data,
                user_id=state.user_id,
                increment_session_count=True
            )
            state.memory_context = build_memory_context(state.memory, state.persona)
            log_info(state.session_id, state.persona, "session_ended",
                     f"total_turns={len(state.chat_history)//2} reason={reason}")
            state.ended = True

        return self._result(
            response=GOODBYE,
            ended=True,
            needs_feedback=True
        )

    @staticmethod
    def _serialize_history(chat_history: List[object]) -> str:
        rows = []
        for message in chat_history:
            if isinstance(message, HumanMessage):
                rows.append({"type": "human", "content": message.content})
            elif isinstance(message, AIMessage):
                rows.append({"type": "ai", "content": message.content})
        return json.dumps(rows)

    @staticmethod
    def _deserialize_history(raw_history: str) -> List[object]:
        history = []
        try:
            rows = json.loads(raw_history or "[]")
        except Exception:
            rows = []

        for row in rows:
            msg_type = row.get("type")
            content = row.get("content", "")
            if msg_type == "human":
                history.append(HumanMessage(content=content))
            elif msg_type == "ai":
                history.append(AIMessage(content=content))
        return history

    @staticmethod
    def _result(response: str, intent: str = "unknown",
                ended: bool = False, needs_feedback: bool = False) -> Dict[str, object]:
        return {
            "response": response,
            "intent": intent,
            "ended": ended,
            "needs_feedback": needs_feedback
        }
