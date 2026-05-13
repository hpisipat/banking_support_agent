import os
from typing import Optional

import httpx
import streamlit as st

API_BASE = os.getenv("BANKING_AGENT_API_URL", "http://127.0.0.1:8000")
PERSONA_LABELS = {
    "new_customer": "New Customer",
    "existing_customer": "Existing Customer",
    "banker": "Banker / Staff"
}


def api_post(path: str, payload: Optional[dict] = None) -> dict:
    with httpx.Client(timeout=120.0) as client:
        response = client.post(f"{st.session_state.api_base}{path}", json=payload)
        response.raise_for_status()
        return response.json()


def api_post_with_spinner(path: str, payload: Optional[dict], message: str) -> dict:
    with st.spinner(message):
        return api_post(path, payload)


def reset_ui():
    st.session_state.session_id = None
    st.session_state.messages = []
    st.session_state.ended = False
    st.session_state.needs_feedback = False


if "api_base" not in st.session_state:
    st.session_state.api_base = API_BASE
if "session_id" not in st.session_state:
    reset_ui()

st.set_page_config(page_title="Banking Support Agent", layout="wide")
st.title("Banking Support Agent")
st.caption("Phase 8 deployment UI for the IITM capstone agent")

with st.sidebar:
    st.header("Session")
    st.session_state.api_base = st.text_input("FastAPI URL", value=st.session_state.api_base)
    user_id = st.text_input("User ID", value=st.session_state.get("user_id", ""))
    st.session_state.user_id = user_id
    persona = st.radio(
        "Profile",
        options=list(PERSONA_LABELS.keys()),
        format_func=lambda key: PERSONA_LABELS[key]
    )

    start_clicked = st.button("Start New Session", use_container_width=True)
    end_clicked = st.button("End Session", use_container_width=True, disabled=not st.session_state.session_id)

if start_clicked:
    if not user_id.strip():
        st.warning("Please enter a User ID before starting a session.")
    else:
        data = api_post_with_spinner(
            "/sessions",
            {"user_id": user_id.strip(), "persona": persona},
            "Starting your banking session..."
        )
        st.session_state.session_id = data["session_id"]
        st.session_state.messages = [{"role": "assistant", "content": data["greeting"]}]
        st.session_state.ended = False
        st.session_state.needs_feedback = False
        st.rerun()

if end_clicked and st.session_state.session_id:
    data = api_post_with_spinner(
        f"/sessions/{st.session_state.session_id}/end",
        {},
        "Closing the session..."
    )
    st.session_state.messages.append({"role": "assistant", "content": data["response"]})
    st.session_state.ended = data.get("ended", False)
    st.session_state.needs_feedback = data.get("needs_feedback", False)
    st.rerun()

if st.session_state.session_id:
    st.info(
        f"User ID: {st.session_state.user_id or 'N/A'} | "
        f"Session ID: {st.session_state.session_id}"
    )
else:
    st.info("Enter a User ID, choose a profile, and start a new session.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if st.session_state.session_id and not st.session_state.ended:
    prompt = st.chat_input("Ask the banking agent anything non-transactional")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        result = api_post_with_spinner(
            f"/sessions/{st.session_state.session_id}/messages",
            {"message": prompt},
            "Thinking..."
        )
        st.session_state.messages.append({"role": "assistant", "content": result["response"]})
        st.session_state.ended = result.get("ended", False)
        st.session_state.needs_feedback = result.get("needs_feedback", False)
        st.rerun()

if st.session_state.session_id and st.session_state.needs_feedback:
    st.subheader("Session Feedback")
    with st.form("feedback_form"):
        rating_label = st.radio("How was the experience?", ["Positive", "Negative"], horizontal=True)
        comment = st.text_area("Optional comment")
        submitted = st.form_submit_button("Submit Feedback")

    if submitted:
        rating = "positive" if rating_label == "Positive" else "negative"
        result = api_post_with_spinner(
            f"/sessions/{st.session_state.session_id}/feedback",
            {"rating": rating, "comment": comment},
            "Saving your feedback..."
        )
        st.success(result["message"])
        reset_ui()
        st.rerun()
