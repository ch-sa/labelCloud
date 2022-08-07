from abc import ABC, abstractmethod
from pathlib import Path
import json
from typing import Dict, Tuple
import numpy.typing as npt
import numpy as np
from ...utils.singleton import SingletonABCMeta


class BaseSegmentationHandler(object, metaclass=SingletonABCMeta):
    EXTENSIONS = set()  # should be set in subclasses

    def __init__(self, label_definition_path: Path) -> None:
        self.read_label_definition(label_definition_path)

    def read_label_definition(self, label_definition_path: Path) -> None:
        with open(label_definition_path, "r") as f:
            self.label_definition: Dict[str, int] = json.loads(f.read())

    def read_or_create_labels(
        self, label_path: Path, num_points: int
    ) -> Tuple[Dict[str, int], npt.NDArray[np.int8]]:
        """Read labels per point and its schema"""
        if label_path.exists():
            labels = self._read_labels(label_path)
        else:
            labels = np.zeros(shape=(num_points,), dtype=np.int8)
        return self.label_definition, labels

    @abstractmethod
    def _read_labels(self, label_path: Path) -> npt.NDArray[np.int8]:
        raise NotImplementedError

    @abstractmethod
    def overwrite_labels(self, label_path: Path, **kwargs) -> None:
        raise NotImplementedError

    @classmethod
    def get_handler(cls, file_extension: str, **kwargs) -> "BaseSegmentationHandler":
        for subclass in cls.__subclasses__():
            if file_extension in subclass.EXTENSIONS:
                return subclass(**kwargs)


def validate_label_definition(label_definition: Dict[str, int]):
    ...


def validate_labels(label_definition: Dict[str, int], labels: npt.NDArray[np.int8]):
    ...
