from enum import IntEnum


class Context(IntEnum):
    """Context of a Status hint.

    - integer determines the importance of the related message (higher = more important)
    """

    DEFAULT = 1
    SIDE_HOVERED = 2
    CONTROL_PRESSED = 3
