from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

import numpy as np
import numpy.typing as npt
import open3d as o3d

from . import BasePointCloudHandler

if TYPE_CHECKING:
    from ...model import PointCloud


class Open3DHandler(BasePointCloudHandler):
    EXTENSIONS = {".pcd", ".ply", ".pts", ".xyz", ".xyzn", ".xyzrgb"}

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def to_point_cloud(
        pointcloud: o3d.geometry.PointCloud,
    ) -> Tuple[npt.NDArray, Optional[npt.NDArray]]:
        return (
            np.asarray(pointcloud.points).astype("float32"),
            np.asarray(pointcloud.colors).astype("float32"),
        )

    @staticmethod
    def to_open3d_point_cloud(pointcloud: "PointCloud") -> o3d.geometry.PointCloud:
        o3d_pointcloud = o3d.geometry.PointCloud(
            o3d.utility.Vector3dVector(pointcloud.points)
        )
        o3d_pointcloud.colors = o3d.utility.Vector3dVector(pointcloud.colors)
        return o3d_pointcloud

    def read_point_cloud(self, path: Path) -> Tuple[npt.NDArray, Optional[npt.NDArray]]:
        super().read_point_cloud(path)
        return self.to_point_cloud(
            o3d.io.read_point_cloud(str(path), remove_nan_points=True)
        )

    def write_point_cloud(self, path: Path, pointcloud: "PointCloud") -> None:
        super().write_point_cloud(path, pointcloud)
        o3d.io.write_point_cloud(str(path), self.to_open3d_point_cloud(pointcloud))
