from dataclasses import dataclass
from typing import Dict, List, Optional

from ...definitions.types import Color4f


def hex_to_rgba(hex: str) -> Color4f:
    """Converts a hex color to a list of RGBA values.

    Args:
        hex (str): The hex color to convert.

    Returns:
        List[float]: The RGBA values.
    """
    hex = hex.lstrip("#")

    if len(hex) == 6:
        hex = hex + "ff"

    return tuple(  # type: ignore
        [int(hex[i : i + 2], 16) / 255 for i in range(0, 8, 2)]
    )


@dataclass
class ClassConfig:
    name: str
    id: int
    color: Color4f

    @classmethod
    def from_dict(cls, data: dict) -> "ClassConfig":
        return cls(name=data["name"], id=data["id"], color=hex_to_rgba(data["color"]))


@dataclass
class LabelConfig:
    classes: List[ClassConfig]
    default: int
    type: str
    format: str

    def get_classes(self) -> Dict[str, ClassConfig]:
        return {c.name: c for c in self.classes}

    @classmethod
    def from_dict(cls, data: dict) -> "LabelConfig":
        classes = [ClassConfig.from_dict(c) for c in data["classes"]]
        return cls(classes, data["default"], data["type"], data["format"])
