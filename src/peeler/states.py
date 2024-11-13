from enum import Enum, unique

@unique
class State(Enum):
    """State of the peeler"""
    OFF = 0
    RUNNING = 1
    IDLE = 2
    ERROR = 3
    UNKNOWN = 4