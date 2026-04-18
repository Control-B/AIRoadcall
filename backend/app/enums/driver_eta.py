import enum


class DriverEtaDecision(str, enum.Enum):
    """Driver response to the proposed mechanic ETA."""

    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
