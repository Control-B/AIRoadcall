import enum


class IssueType(str, enum.Enum):
    flat_tire = "flat_tire"
    dead_battery = "dead_battery"
    lockout = "lockout"
    fuel_delivery = "fuel_delivery"
    tow_needed = "tow_needed"
    engine_trouble = "engine_trouble"
    overheating = "overheating"
    accident = "accident"
    stuck_off_road = "stuck_off_road"
    other = "other"
