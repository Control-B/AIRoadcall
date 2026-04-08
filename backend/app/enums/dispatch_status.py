import enum


class DispatchStatus(str, enum.Enum):
    queued = "queued"
    calling = "calling"
    accepted = "accepted"
    declined = "declined"
    unavailable = "unavailable"
    no_answer = "no_answer"
    timed_out = "timed_out"
    superseded = "superseded"
