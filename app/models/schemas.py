from pydantic import BaseModel
from enum import Enum
from typing import Optional


class Sentiment(str, Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class CallerRecord(BaseModel):
    first_name: str
    last_name: str
    phone: str
    claim_status: str
    claim_id: str
    policy_number: str


class InteractionRecord(BaseModel):
    caller_name: str
    phone: str
    summary: str
    sentiment: Sentiment
    authenticated: bool
    timestamp: str


class LookupCallerArgs(BaseModel):
    phone_number: str


class LogInteractionArgs(BaseModel):
    caller_name: str
    summary: str
    sentiment: Sentiment
