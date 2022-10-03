import json
import logging
from dataclasses import dataclass
from typing import Dict, List

from ...control.config_manager import config
from ...definitions.types import Color4f
from ...utils.color import hex_to_rgba
from ...utils.singleton import SingletonABCMeta

CONFIG_FILE = "_classes.json"  # TODO: Move to config?


@dataclass
class ClassConfig:
    name: str
    id: int
    color: Color4f

    @classmethod
    def from_dict(cls, data: dict) -> "ClassConfig":
        return cls(name=data["name"], id=data["id"], color=hex_to_rgba(data["color"]))


class LabelConfig(object, metaclass=SingletonABCMeta):
    def __init__(self) -> None:
        self.classes: List[ClassConfig]
        self.default: int
        self.type: str
        self.format: str

        if getattr(self, "_loaded", False) != True:
            self.load_config()

    def load_config(self) -> None:
        with config.getpath("FILE", "label_folder").joinpath(CONFIG_FILE).open(
            "r"
        ) as stream:
            data = json.load(stream)

        self.classes = [ClassConfig.from_dict(c) for c in data["classes"]]
        self.default = data["default"]
        self.type = data["type"]
        self.format = data["format"]
        self._loaded = True

    def get_classes(self) -> Dict[str, ClassConfig]:
        return {c.name: c for c in self.classes}

    def get_class_color(self, class_name: str) -> Color4f:
        try:
            return self.get_classes()[class_name].color
        except KeyError:
            logging.warning(
                f"No color defined for class '{class_name}'!" "Proceeding with red."
            )
            return hex_to_rgba("#FF0000")

    def get_default_class_name(self) -> str:
        return next((c.name for c in self.classes if c.id == self.default))
