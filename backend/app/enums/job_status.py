import enum


class JobStatus(str, enum.Enum):
    created = "created"
    awaiting_driver_location = "awaiting_driver_location"
    awaiting_payment_authorization = "awaiting_payment_authorization"
    payment_authorized = "payment_authorized"
    matching_mechanics = "matching_mechanics"
    calling_mechanics = "calling_mechanics"
    mechanic_assigned = "mechanic_assigned"
    mechanic_en_route = "mechanic_en_route"
    mechanic_arrived = "mechanic_arrived"
    completed = "completed"
    canceled = "canceled"
