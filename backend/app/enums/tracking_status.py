import enum


class TrackingStatus(str, enum.Enum):
    not_started = "not_started"
    pending = "pending"
    active = "active"
    paused = "paused"
    arrived = "arrived"
    ended = "ended"
