from dataclasses import dataclass
from typing import Tuple


@dataclass
class Perspective(object):
    translation: Tuple[float, float, float]
    rotation: Tuple[float, float, float]

