"""assistant.py - the AI Sales Assistant chat API. This is the ONLY router
that talks to the LLM - it calls the existing Foundry Agent thin client
unchanged, preserving its existing scope guardrail and instructions."""

from fastapi import APIRouter
from pydantic import BaseModel

from ..services import foundry_service

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class AskRequest(BaseModel):
    question: str


@router.post("/ask")
def ask(body: AskRequest):
    answer, error = foundry_service.ask(body.question, maintain_history=True)
    if error:
        return {
            "available": False, "answer": None,
            "error": "AI Assistant is temporarily unavailable. Dashboard functionality is still available.",
        }
    return {"available": True, "answer": answer, "error": None}


@router.post("/reset")
def reset():
    """Starts a fresh chat thread - called when the frontend chat is cleared,
    so old conversation context doesn't leak into a new topic."""
    foundry_service.reset_chat_history()
    return {"status": "ok"}
