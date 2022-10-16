from abc import abstractmethod
from pathlib import Path
from typing import Dict, Set, Type

import numpy as np
import numpy.typing as npt

from ...utils.singleton import SingletonABCMeta
from ..labels.config import LabelConfig


class BaseSegmentationHandler(object, metaclass=SingletonABCMeta):
    EXTENSIONS: Set[str] = set()  # should be set in subclasses

    @property
    def default_label(self) -> int:
        return LabelConfig().default

    def read_or_create_labels(
        self, label_path: Path, num_points: int
    ) -> npt.NDArray[np.int8]:
        """Read labels per point and its schema"""
        if label_path.exists():
            labels = self._read_labels(label_path)
            if labels.shape[0] != num_points:
                raise ValueError(
                    f"The segmentation label doesn't match with the point cloud, "
                    "label file contains {labels.shape[0]} while point cloud contains {num_points}."
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
