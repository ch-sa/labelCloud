import ctypes
import logging
from pathlib import Path
from typing import List, Optional, Tuple

import pkg_resources

import numpy as np
import OpenGL.GL as GL

from . import Perspective
from ..control.config_manager import config
from ..io.pointclouds import BasePointCloudHandler
from ..utils.logger import end_section, green, print_column, red, start_section, yellow

# Get size of float (4 bytes) for VBOs
SIZE_OF_FLOAT = ctypes.sizeof(ctypes.c_float)


# Creates an array buffer in a VBO
def create_buffer(attributes) -> GL.glGenBuffers:
    bufferdata = (ctypes.c_float * len(attributes))(*attributes)  # float buffer
    buffersize = len(attributes) * SIZE_OF_FLOAT  # buffer size in bytes

    vbo = GL.glGenBuffers(1)
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
    GL.glBufferData(GL.GL_ARRAY_BUFFER, buffersize, bufferdata, GL.GL_STATIC_DRAW)
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
    return vbo


def calculate_init_translation(
    center: Tuple[float, float, float], mins: np.ndarray, maxs: np.ndarray
) -> np.ndarray:
    """Calculates the initial translation (x, y, z) of the point cloud. Considers ...

    - the point cloud center
    - the point cloud extents
    - the far plane setting (caps zoom)
    """
    zoom = min(
        np.linalg.norm(maxs - mins),
        config.getfloat("USER_INTERFACE", "far_plane") * 0.9,
    )
    return -np.add(center, [0, 0, zoom])


def colorize_points(points: np.ndarray, z_min: float, z_max: float) -> np.ndarray:
    palette = np.loadtxt(
        pkg_resources.resource_filename("labelCloud.resources", "rocket-palette.txt")
    )
    palette_len = len(palette) - 1

    colors = np.zeros(points.shape)
    for ind, height in enumerate(points[:, 2]):
        colors[ind] = palette[round((height - z_min) / (z_max - z_min) * palette_len)]
    return colors


class PointCloud(object):
    def __init__(
        self,
        path: Path,
        points: np.ndarray,
        colors: Optional[np.ndarray] = None,
        init_translation: Optional[Tuple[float, float, float]] = None,
        init_rotation: Optional[Tuple[float, float, float]] = None,
        write_buffer: bool = True,
    ) -> None:
        start_section(f"Loading {path.name}")
        self.path = path
        self.points = points
        self.colors = colors if type(colors) == np.ndarray and len(colors) > 0 else None
        self.vbo = None
        self.center = tuple(np.sum(points[:, i]) / len(points) for i in range(3))
        self.pcd_mins = np.amin(points, axis=0)
        self.pcd_maxs = np.amax(points, axis=0)
        self.init_translation = init_translation or calculate_init_translation(
            self.center, self.pcd_mins, self.pcd_maxs
        )
        self.init_rotation = init_rotation or (0, 0, 0)

        # Point cloud transformations
        self.trans_x, self.trans_y, self.trans_z = self.init_translation
        self.rot_x, self.rot_y, self.rot_z = self.init_rotation

        if self.colorless and config.getboolean("POINTCLOUD", "COLORLESS_COLORIZE"):
            self.colors = colorize_points(
                self.points, self.pcd_mins[2], self.pcd_maxs[2]
            )
            logging.info("Generated colors for colorless point cloud based on height.")

        if write_buffer:
            self.write_vbo()

        logging.info(green(f"Successfully loaded point cloud from {path}!"))
        self.print_details()
        end_section()

    @classmethod
    def from_file(
        cls,
        path: Path,
        perspective: Optional[Perspective] = None,
        write_buffer: bool = True,
    ) -> "PointCloud":
        init_translation, init_rotation = (None, None)
        if perspective:
            init_translation = perspective.translation
            init_rotation = perspective.rotation

        points, colors = BasePointCloudHandler.get_handler(
            path.suffix
        ).read_point_cloud(path=path)
        return cls(path, points, colors, init_translation, init_rotation, write_buffer)

    def to_file(self, path: Optional[Path] = None) -> None:
        if not path:
            path = self.path
        BasePointCloudHandler.get_handler(path.suffix).write_point_cloud(
            path=path, pointcloud=self
        )

    @property
    def colorless(self):
        return self.colors is None

    # GETTERS AND SETTERS
    def get_no_of_points(self) -> int:
        return len(self.points)

    def get_no_of_colors(self) -> int:
        return len(self.colors)

    def get_rotations(self) -> List[float]:
        return [self.rot_x, self.rot_y, self.rot_z]

    def get_translations(self) -> List[float]:
        return [self.trans_x, self.trans_y, self.trans_z]

    def get_mins_maxs(self) -> Tuple[float, float]:
        return self.pcd_mins, self.pcd_maxs

    def get_min_max_height(self) -> Tuple[float, float]:
        return self.pcd_mins[2], self.pcd_maxs[2]

    def set_rot_x(self, angle) -> None:
        self.rot_x = angle % 360

    def set_rot_y(self, angle) -> None:
        self.rot_y = angle % 360

    def set_rot_z(self, angle) -> None:
        self.rot_z = angle % 360

    def set_rotations(self, x: float, y: float, z: float) -> None:
        self.rot_x = x % 360
        self.rot_y = y % 360
        self.rot_z = z % 360

    def set_trans_x(self, val) -> None:
        self.trans_x = val

    def set_trans_y(self, val) -> None:
        self.trans_y = val

    def set_trans_z(self, val) -> None:
        self.trans_z = val

    def set_translations(self, x: float, y: float, z: float) -> None:
        self.trans_x = x
        self.trans_y = y
        self.trans_z = z

    # MANIPULATORS

    def transform_data(self) -> np.ndarray:
        if self.colorless:
            attributes = self.points
        else:
            # Merge coordinates and colors in alternating order
            attributes = np.concatenate((self.points, self.colors), axis=1)

        return attributes.flatten()  # flatten to single list

    def write_vbo(self) -> None:
        self.vbo = create_buffer(self.transform_data())

    def draw_pointcloud(self) -> None:
        GL.glTranslate(
            self.trans_x, self.trans_y, self.trans_z
        )  # third, pcd translation

        pcd_center = np.add(
            self.pcd_mins, (np.subtract(self.pcd_maxs, self.pcd_mins) / 2)
        )
        GL.glTranslate(*pcd_center)  # move point cloud back

        GL.glRotate(self.rot_x, 1.0, 0.0, 0.0)
        GL.glRotate(self.rot_y, 0.0, 1.0, 0.0)  # second, pcd rotation
        GL.glRotate(self.rot_z, 0.0, 0.0, 1.0)

        GL.glTranslate(*(pcd_center * -1))  # move point cloud to center for rotation

        GL.glPointSize(config.getfloat("POINTCLOUD", "POINT_SIZE"))
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)

        if self.colorless:
            stride = 3 * SIZE_OF_FLOAT  # (12 bytes) : [x, y, z] * sizeof(float)
            GL.glPointSize(1)
            GL.glColor3d(
                *config.getlist("POINTCLOUD", "COLORLESS_COLOR")
            )  # IDEA: Color by (height) position
        else:
            stride = (
                6 * SIZE_OF_FLOAT
            )  # (24 bytes) : [x, y, z, r, g, b] * sizeof(float)

        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glVertexPointer(3, GL.GL_FLOAT, stride, None)

        if not self.colorless:
            GL.glEnableClientState(GL.GL_COLOR_ARRAY)
            offset = (
                3 * SIZE_OF_FLOAT
            )  # (12 bytes) : the rgb color starts after the 3 coordinates x, y, z
            GL.glColorPointer(3, GL.GL_FLOAT, stride, ctypes.c_void_p(offset))
        GL.glDrawArrays(GL.GL_POINTS, 0, self.get_no_of_points())  # Draw the points

        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        if not self.colorless:
            GL.glDisableClientState(GL.GL_COLOR_ARRAY)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    def reset_perspective(self) -> None:
        self.trans_x, self.trans_y, self.trans_z = self.init_rotation
        self.rot_x, self.rot_y, self.rot_z = self.init_rotation

    def print_details(self) -> None:
        print_column(
            [
                "Number of Points:",
                green(len(self.points))
                if len(self.points) > 0
                else red(len(self.points)),
            ]
        )
        print_column(
            [
                "Number of Colors:",
                yellow("None")
                if self.colorless
                else green(len(self.colors))
                if len(self.colors) == len(self.points)
                else red(len(self.colors)),
            ]
        )
        print_column(["Point Cloud Center:", np.round(self.center, 2)])
        print_column(["Point Cloud Minimums:", np.round(self.pcd_mins, 2)])
        print_column(["Point Cloud Maximums:", np.round(self.pcd_maxs, 2)])
        print_column(
            ["Initial Translation:", np.round(self.init_translation, 2)], last=True
        )
