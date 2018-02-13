from enum import Enum

class DeviceState(Enum):
    NOT_READY = 1
    READY = 2
    READY_FOR_TRIAL = 3
    ACQUIRING = 4
    RECORDING = 5
    FINISHED = 6