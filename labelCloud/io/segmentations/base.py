import json
from abc import abstractmethod
from pathlib import Path
from typing import Dict, Set, Type

import numpy as np
import numpy.typing as npt

from ...utils.singleton import SingletonABCMeta


class BaseSegmentationHandler(object, metaclass=SingletonABCMeta):
    EXTENSIONS: Set[str] = set()  # should be set in subclasses

    def __init__(self, label_definition_path: Path) -> None:
        self.read_label_definition(label_definition_path)

    def read_label_definition(self, label_definition_path: Path) -> None:
        with open(label_definition_path, "r") as f:
            class_data = json.loads(f.read())

        self.label_definition = {
            label["name"]: label["id"] for label in class_data["classes"]
        }

        assert len(self.label_definition) > 0

    @property
    def default_label(self) -> int:
        return min(list(self.label_definition.values()))

    def read_or_create_labels(
        self, label_path: Path, num_points: int
    ) -> npt.NDArray[np.int8]:
        """Read labels per point and its schema"""
        if label_path.exists():
            labels = self._read_labels(label_path)
            if labels.shape[0] != num_points:
                raise ValueError(
                    f"The segmentation label doesn't match with the point cloud, label file contains {labels.shape[0]} while point cloud contains {num_points}."
                )
        else:
            labels = self._create_labels(num_points)
        return labels

    def overwrite_labels(self, label_path: Path, labels: npt.NDArray[np.int8]) -> None:
        return self._write_labels(label_path, labels)

    @abstractmethod
    def _read_labels(self, label_path: Path) -> npt.NDArray[np.int8]:
        raise NotImplementedError

    @abstractmethod
    def _create_labels(self, num_points: int) -> npt.NDArray[np.int8]:
        raise NotImplementedError

    @abstractmethod
    def _write_labels(self, label_path: Path, labels: npt.NDArray[np.int8]) -> None:
        raise NotImplementedError

    @classmethod
    def get_handler(cls, file_extension: str) -> Type["BaseSegmentationHandler"]:
        for subclass in cls.__subclasses__():
            if file_extension in subclass.EXTENSIONS:
                return subclass
        raise NotImplementedError(
            f"{file_extension} is not supported for segmentation labels."
        )
