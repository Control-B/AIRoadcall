from pydantic import BaseModel
from typing import Optional


class PaymentIntentRequest(BaseModel):
    amount: Optional[float] = None  # Override hold amount if needed


class PaymentIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str
    amount: float
    currency: str = "usd"
    status: str


class PaymentConfirmRequest(BaseModel):
    payment_intent_id: str


class PaymentConfirmResponse(BaseModel):
    success: bool
    payment_status: str
    job_status: str
