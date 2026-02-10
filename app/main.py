from fastapi import FastAPI
from app.models import Ticket
from app.classifier import classify_ticket
from app.router import route_channel
from app.db import log_ticket

app = FastAPI()

@app.post("/support-ticket/")
def receive_ticket(ticket: Ticket):
    classified = classify_ticket(ticket.subject, ticket.body)
    channel = route_channel(classified.category)

    log_ticket(classified.dict())

    return {
        "routed_to": channel,
        "classification": classified
    }
