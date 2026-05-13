from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.session_service import SessionManager

app = FastAPI(title="Banking Support Agent API", version="0.1.0")
manager = SessionManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SessionCreateRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    persona: Literal["new_customer", "existing_customer", "banker"]


class MessageRequest(BaseModel):
    message: str = Field(..., min_length=1)


class FeedbackRequest(BaseModel):
    rating: Literal["positive", "negative"]
    comment: str = ""


@app.get("/health")
def healthcheck():
    return {"status": "ok"}


@app.post("/sessions")
def create_session(request: SessionCreateRequest):
    try:
        return manager.create_session(request.persona, request.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/sessions/{session_id}/messages")
def send_message(session_id: str, request: MessageRequest):
    try:
        return manager.process_message(session_id, request.message)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/sessions/{session_id}/end")
def end_session(session_id: str):
    try:
        return manager.end_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/sessions/{session_id}/feedback")
def submit_feedback(session_id: str, request: FeedbackRequest):
    try:
        result = manager.submit_feedback(session_id, request.rating, request.comment)
        manager.close_session(session_id)
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
