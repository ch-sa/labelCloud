from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

import numpy as np
import open3d as o3d

from . import BasePointCloudHandler

if TYPE_CHECKING:
    from ...model import PointCloud


class Open3DHandler(BasePointCloudHandler):
    EXTENSIONS = {".pcd", ".ply", ".pts", ".xyz", ".xyzn", ".xyzrgb"}

    def __init__(self) -> None:
        super().__init__()

    def read_point_cloud(self, path: Path) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        super().read_point_cloud(path)
        o3d_pcd = o3d.io.read_point_cloud(str(path), remove_nan_points=True)
        return (
            np.asarray(o3d_pcd.points).astype("float32"),
            np.asarray(o3d_pcd.colors).astype("float32"),
        )

    def write_point_cloud(self, path: Path, point_cloud: "PointCloud") -> None:
        # TODO: Implement
        return super().write_point_cloud(path, point_cloud)
