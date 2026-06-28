from enum import Enum, auto


class InstallState(Enum):

    IDLE = auto()

    DOWNLOADING = auto()

    BACKUP = auto()

    INSTALLING = auto()

    FINISHED = auto()

    ERROR = auto()