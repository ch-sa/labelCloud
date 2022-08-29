import logging
from pathlib import Path
from typing import TYPE_CHECKING, Tuple

import numpy as np
import numpy.typing as npt

from . import BasePointCloudHandler

if TYPE_CHECKING:
    from ...model import PointCloud


class NumpyHandler(BasePointCloudHandler):
    EXTENSIONS = {".bin"}

    def __init__(self) -> None:
        super().__init__()

    def read_point_cloud(self, path: Path) -> Tuple[npt.NDArray, None]:
        """Read point cloud file as array and drop reflection and nan values."""
        super().read_point_cloud(path)
        points = np.fromfile(path, dtype=np.float32)
        points = points.reshape((-1, 4 if len(points) % 4 == 0 else 3))[:, 0:3]
        return (points[~np.isnan(points).any(axis=1)], None)

    def write_point_cloud(self, path: Path, pointcloud: "PointCloud") -> None:
        """Write point cloud points into binary file."""
        super().write_point_cloud(path, pointcloud)
        logging.warning(
            "Only writing point coordinates, any previous reflection values will be dropped."
        )
        pointcloud.points.tofile(path)
