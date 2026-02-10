from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///tickets.db")
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class TicketLog(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    category = Column(String)
    urgency = Column(String)
    sentiment = Column(String)
    product_area = Column(String)
    confidence = Column(Float)
    summary = Column(String)

Base.metadata.create_all(bind=engine)

def log_ticket(data):
    session = SessionLocal()
    ticket = TicketLog(**data)
    session.add(ticket)
    session.commit()
    session.close()
