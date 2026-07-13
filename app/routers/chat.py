"""
Conversational RAG API.

POST /chat

"""
from fastapi import APIRouter, Depends
from app.core.security import verify_api_key
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import memory
from app.services.booking import extract_booking_details, save_booking
from app.services.retrieval import answer_question

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    history = memory.get_history(request.session_id)

    # 1. Check if this message is a booking request first.
    booking_details = extract_booking_details(request.message)
    if booking_details is not None:
        save_booking(db, request.session_id, booking_details)
        answer = (
            f"Your interview is booked for {booking_details.date} at "
            f"{booking_details.time}. We'll send a confirmation to "
            f"{booking_details.email}."
        )
        memory.append_turn(request.session_id, "user", request.message)
        memory.append_turn(request.session_id, "assistant", answer)
        return ChatResponse(session_id=request.session_id, answer=answer, booking_confirmed=True)

    # 2. Otherwise, answer normally using RAG.
    answer = answer_question(request.message, history)

    memory.append_turn(request.session_id, "user", request.message)
    memory.append_turn(request.session_id, "assistant", answer)

    return ChatResponse(session_id=request.session_id, answer=answer)