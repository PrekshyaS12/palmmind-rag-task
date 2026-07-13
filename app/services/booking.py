"""
Interview booking — detect intent, extract details with the LLM, save.

"""
import json

from google import genai
from google.genai import types
from pydantic import BaseModel, EmailStr, ValidationError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Booking

settings = get_settings()
client = genai.Client(api_key=settings.google_api_key)

EXTRACTION_PROMPT = """\
Look at the user's message and decide if they want to book an interview.
If yes, extract these fields: name, email, date (YYYY-MM-DD), time (HH:MM, 24h).
Respond with ONLY a JSON object like this, nothing else:
{"wants_booking": true, "name": "...", "email": "...", "date": "...", "time": "..."}
If any field is missing or the user does not want to book, respond:
{"wants_booking": false}
"""

class BookingDetails(BaseModel):
    name: str
    email: EmailStr
    date: str
    time: str
  
def extract_booking_details(message: str) -> BookingDetails | None:
   
    response = client.models.generate_content(
        model=settings.chat_model,
        contents=message,
        config=types.GenerateContentConfig(
            system_instruction=EXTRACTION_PROMPT,
            response_mime_type="application/json",
        ),
    )

    raw = json.loads(response.text)

    if not raw.get("wants_booking"):
        return None

    try:
        return BookingDetails(**raw)
    except ValidationError:
        # LLM said "yes" but gave incomplete/invalid fields — treat as not ready yet
        return None


def save_booking(db: Session, session_id: str, details: BookingDetails) -> Booking:
    booking = Booking(
        session_id=session_id,
        name=details.name,
        email=details.email,
        interview_date=details.date,
        interview_time=details.time,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking