from pathlib import Path

import numpy as np
import numpy.typing as npt

from .base import BaseSegmentationHandler


class NumpySegmentationHandler(BaseSegmentationHandler):
    EXTENSIONS = {".bin"}

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def _create_labels(self, num_points: int) -> npt.NDArray[np.int8]:
        return np.ones(shape=(num_points,), dtype=np.int8) * self.default_label

    def _read_labels(self, label_path: Path) -> npt.NDArray[np.int8]:
        labels = np.fromfile(label_path, dtype=np.int8)
        return labels

    def _write_labels(self, label_path: Path, labels: npt.NDArray[np.int8]) -> None:
        if not label_path.parent.exists():
            label_path.parent.mkdir(parents=True)

        labels.tofile(label_path)
