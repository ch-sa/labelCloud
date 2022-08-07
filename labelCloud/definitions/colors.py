from enum import Enum


class Color(tuple, Enum):
    RED = (1, 0, 0, 1)
    GREEN = (0, 1, 0, 1)
