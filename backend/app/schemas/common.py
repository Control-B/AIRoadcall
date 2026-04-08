from pydantic import BaseModel
from datetime import datetime


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime


class ErrorResponse(BaseModel):
    detail: str


class SuccessResponse(BaseModel):
    success: bool = True
    message: str = "OK"
