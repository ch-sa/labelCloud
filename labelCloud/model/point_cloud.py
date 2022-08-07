import ctypes
import logging
from pathlib import Path
from typing import List, Optional, Tuple

import pkg_resources

import numpy as np
import OpenGL.GL as GL
import pkg_resources
import colorsys

from labelCloud.io.segmentations.base import BaseSegmentationHandler

from . import Perspective
from ..control.config_manager import config
from ..io.pointclouds import BasePointCloudHandler
from ..utils.logger import end_section, green, print_column, red, start_section, yellow

# Get size of float (4 bytes) for VBOs
SIZE_OF_FLOAT = ctypes.sizeof(ctypes.c_float)


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
    return colors.astype(np.float32)


def hsv_to_rgb(h, s, v):
    (r, g, b) = colorsys.hsv_to_rgb(h, s, v)
    return (int(255 * r), int(255 * g), int(255 * b))


def get_distinct_colors(n):
    hue_partition = 1.0 / (n + 1)
    return np.vstack(
        [
            np.array(
                hsv_to_rgb(
                    hue_partition * value,
                    1.0 - (value % 2) * 0.5,
                    1.0 - (value % 3) * 0.1,
                ),
                dtype=np.float32,
            )
            / 255
            for value in range(0, n)
        ]
    )


def consecutive(data, stepsize=1):
    return np.split(data, np.where(np.diff(data) != stepsize)[0] + 1)


class PointCloud(object):
    def __init__(
        self,
        path: Path,
        points: np.ndarray,
        colors: Optional[np.ndarray] = None,
        labels=None,
        label_definition=None,
        init_translation: Optional[Tuple[float, float, float]] = None,
        init_rotation: Optional[Tuple[float, float, float]] = None,
        write_buffer: bool = True,
    ) -> None:
        start_section(f"Loading {path.name}")
        self.path = path
        self.points = points
        self.color_with_label_flag = False
        self.center = tuple(np.sum(points[:, i]) / len(points) for i in range(3))
        self.pcd_mins = np.amin(points, axis=0)
        self.pcd_maxs = np.amax(points, axis=0)
        self.init_translation = init_translation or calculate_init_translation(
            self.center, self.pcd_mins, self.pcd_maxs
        )
        self.init_rotation = init_rotation or (0, 0, 0)

        self.colors = colors
        self.pos_vbo = self.color_vbo = self.label_color_vbo = None
        self.label_definitions = label_definition
        self.labels = labels
        self.label_color_map = get_distinct_colors(len(self.label_definitions))
        self.mix_ratio = 0.5

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

    @property
    def label_colors(self):
        """color the points with labels"""
        label_one_hot = np.eye(len(self.label_definitions))[self.labels]
        colors = np.dot(label_one_hot, self.label_color_map).astype(np.float32)
        return self.colors * (1 - self.mix_ratio) + colors * self.mix_ratio

    @classmethod
    def from_file(
        cls,
        path: Path,
        perspective: Optional[Perspective] = None,
        label_path: Path = Path("bla.bin"),
        label_definition_path: Path = config.getpath(
            "SEGMENTATION", "label_definition_path"
        ),
        write_buffer: bool = True,
    ) -> "PointCloud":
        init_translation, init_rotation = (None, None)
        if perspective:
            init_translation = perspective.translation
            init_rotation = perspective.rotation

        points, colors = BasePointCloudHandler.get_handler(
            path.suffix
        ).read_point_cloud(path=path)

        segmentation_handler: BaseSegmentationHandler = (
            BaseSegmentationHandler.get_handler(
                file_extension=".bin", label_definition_path=label_definition_path
            )
        )

        label_definition, labels = segmentation_handler.read_or_create_labels(
            label_path=label_path, num_points=points.shape[0]
        )

        return cls(
            path,
            points,
            colors,
            labels,
            label_definition,
            init_translation,
            init_rotation,
            write_buffer,
        )

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
    def write_vbo(self) -> None:
        self.pos_vbo, self.color_vbo, self.label_color_vbo = GL.glGenBuffers(3)
        for data, vbo in [
            (self.points, self.pos_vbo),
            (self.colors, self.color_vbo),
            (self.label_colors, self.label_color_vbo),
        ]:
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, data.nbytes, data, GL.GL_DYNAMIC_DRAW)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

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
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.pos_vbo)

        stride = 3 * SIZE_OF_FLOAT
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glVertexPointer(3, GL.GL_FLOAT, stride, None)

        if not self.color_with_label_flag:
            color_vbo = self.color_vbo
        else:
            color_vbo = self.label_color_vbo
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, color_vbo)
        GL.glEnableClientState(GL.GL_COLOR_ARRAY)
        GL.glColorPointer(3, GL.GL_FLOAT, stride, None)
        GL.glDrawArrays(GL.GL_POINTS, 0, self.get_no_of_points())

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

    def update_colors_selected_points(self, points_inside):
        print(points_inside)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.label_color_vbo)
        colors = self.label_colors
        arrays = consecutive(np.where(points_inside)[0])  # find contiguous points
        for arr in arrays:
            col = colors[arr]
            GL.glBufferSubData(GL.GL_ARRAY_BUFFER, arr[0] * 12, col.nbytes, col)
