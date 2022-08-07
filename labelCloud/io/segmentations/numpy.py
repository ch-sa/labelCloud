from .base import BaseSegmentationHandler
from pathlib import Path
import numpy as np
import numpy.typing as npt


class NumpySegmentationHandler(BaseSegmentationHandler):
    EXTENSIONS = {".bin"}

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def _read_labels(self, label_path: Path) -> npt.NDArray[np.int8]:
        labels = np.fromfile(label_path, dtype=np.int8)
        return labels

    def overwrite_labels(self, label_path: Path, **kwargs) -> None:
        ...
