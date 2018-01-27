from enum import Enum


class TrialState(Enum):
    IDLE = 1
    READY = 2
    ONGOING = 3
    COMPLETED = 4
