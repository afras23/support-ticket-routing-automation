from pydantic import BaseModel
from typing import Literal

TicketType = Literal["bug", "feature_request", "billing", "technical_question"]
Urgency = Literal["low", "medium", "high"]
Sentiment = Literal["negative", "neutral", "positive"]

class Ticket(BaseModel):
    subject: str
    body: str
    customer_email: str

class ClassifiedTicket(BaseModel):
    category: TicketType
    urgency: Urgency
    sentiment: Sentiment
    product_area: str
    confidence: float
    summary: str
