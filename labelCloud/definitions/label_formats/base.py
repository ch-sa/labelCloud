from enum import Enum
from typing import List


class BaseLabelFormat(str, Enum):
    @classmethod
    def list(cls) -> List["BaseLabelFormat"]:
        return [e.value for e in cls]
