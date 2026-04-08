import enum


class PaymentStatus(str, enum.Enum):
    not_started = "not_started"
    pending = "pending"
    authorized = "authorized"
    capture_required = "capture_required"
    captured = "captured"
    released = "released"
    failed = "failed"
