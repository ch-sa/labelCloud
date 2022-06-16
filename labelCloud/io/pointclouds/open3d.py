import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

import numpy as np
import open3d as o3d

from . import BasePointCloudHandler
from ...utils.logger import bold, end_section, red, start_section

if TYPE_CHECKING:
    from ...model import PointCloud


class Open3DHandler(BasePointCloudHandler):
    EXTENSIONS = {".pcd", ".ply", ".pts", ".xyz", ".xyzn", ".xyzrgb"}

    def __init__(self) -> None:
        super().__init__()

    def to_point_cloud(
        self, pointcloud: o3d.geometry.PointCloud
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        return (
            np.asarray(pointcloud.points).astype("float32"),
            np.asarray(pointcloud.colors).astype("float32"),
        )

    def to_open3d_point_cloud(
        self, pointcloud: "PointCloud"
    ) -> o3d.geometry.PointCloud:
        o3d_pointcloud = o3d.geometry.PointCloud(
            o3d.utility.Vector3dVector(pointcloud.points)
        )
        o3d_pointcloud.colors = o3d.utility.Vector3dVector(pointcloud.colors)
        return o3d_pointcloud

    def read_point_cloud(self, path: Path) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        if path.suffix == ".pcd":
            start_section(bold("IO WARNING"))
            logging.warning(
                "Loading *.pcd point clouds with Open3D currently leads to issues on Linux systems."
                "\n --> See https://github.com/isl-org/Open3D/issues/4969 for more details."
                "\n --> See https://github.com/ch-sa/labelCloud/issues/68#issuecomment-1086892957 for a workaround."
            )
            end_section()

        super().read_point_cloud(path)
        return self.to_point_cloud(
            o3d.io.read_point_cloud(str(path), remove_nan_points=True)
        )

    def write_point_cloud(self, path: Path, pointcloud: "PointCloud") -> None:
        super().write_point_cloud(path, pointcloud)
        o3d.io.write_point_cloud(str(path), self.to_open3d_point_cloud(pointcloud))
