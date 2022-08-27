import ctypes
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import numpy.typing as npt
import OpenGL.GL as GL

from ..control.config_manager import config
from ..io.pointclouds import BasePointCloudHandler
from ..io.segmentations import BaseSegmentationHandler
from ..utils.color import colorize_points_with_height, get_distinct_colors
from ..utils.logger import end_section, green, print_column, red, start_section, yellow
from . import Perspective

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


class PointCloud(object):
    SEGMENTATION = config.getboolean("MODE", "SEGMENTATION")

    def __init__(
        self,
        path: Path,
        points: np.ndarray,
        colors: Optional[np.ndarray] = None,
        labels: Optional[npt.NDArray[np.int8]] = None,
        label_definition: Optional[Dict[str, int]] = None,
        init_translation: Optional[Tuple[float, float, float]] = None,
        init_rotation: Optional[Tuple[float, float, float]] = None,
        write_buffer: bool = True,
    ) -> None:
        start_section(f"Loading {path.name}")
        self.path = path
        self.points = points
        self.colors = colors if type(colors) == np.ndarray and len(colors) > 0 else None

        self.labels = self.label_definition = self.label_color_map = None
        if self.SEGMENTATION:
            self.labels = labels
            self.label_definition = label_definition
            self.label_color_map = get_distinct_colors(len(label_definition))
            self.mix_ratio = config.getfloat("POINTCLOUD", "label_color_mix_ratio")

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

        self.point_size = config.getfloat("POINTCLOUD", "point_size")

        if self.colorless:
            # if no color in point cloud, either color with height or color with a single color
            if config.getboolean("POINTCLOUD", "COLORLESS_COLORIZE"):
                self.colors = colorize_points_with_height(
                    self.points, self.pcd_mins[2], self.pcd_maxs[2]
                )
                logging.info(
                    "Generated colors for colorless point cloud based on height."
                )
            else:
                colorless_color = np.array(
                    config.getlist("POINTCLOUD", "COLORLESS_COLOR")
                )
                self.colors = (np.ones_like(self.points) * colorless_color).astype(
                    np.float32
                )
                logging.info(
                    "Generated colors for colorless point cloud based on `colorless_color`."
                )

        if write_buffer:
            self.create_buffers()

        logging.info(green(f"Successfully loaded point cloud from {path}!"))
        self.print_details()
        end_section()

    def create_buffers(self) -> None:
        """Create 3 different buffers holding points, colors and label colors information"""
        (
            self.position_vbo,
            self.color_vbo,
            self.label_vbo,
        ) = GL.glGenBuffers(3)
        for data, vbo in [
            (self.points, self.position_vbo),
            (self.colors, self.color_vbo),
            (self.label_colors, self.label_vbo),
        ]:
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
            GL.glBufferData(GL.GL_ARRAY_BUFFER, data.nbytes, data, GL.GL_DYNAMIC_DRAW)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    @property
    def label_colors(self) -> npt.NDArray[np.float32]:
        """blend the points with label color map"""
        if self.labels is not None:
            label_one_hot = np.eye(len(self.label_definition))[self.labels]
            colors = np.dot(label_one_hot, self.label_color_map).astype(np.float32)
            return colors * self.mix_ratio + self.colors * (1 - self.mix_ratio)
        else:
            return self.colors

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

        labels = label_def = None
        if cls.SEGMENTATION:

            label_path = config.getpath("FILE", "label_folder") / Path(
                f"segmentation/{path.stem}.bin"
            )
            label_defintion_path = config.getpath("FILE", "label_folder") / Path(
                f"segmentation/schema/label_definition.json"
            )

            logging.info(f"Loading segmentation labels from {label_path}.")
            seg_handler = BaseSegmentationHandler.get_handler(label_path.suffix)(
                label_definition_path=label_defintion_path
            )
            label_def, labels = seg_handler.read_or_create_labels(
                label_path=label_path, num_points=points.shape[0]
            )

        return cls(
            path,
            points,
            colors,
            labels,
            label_def,
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

    def transform_data(self) -> np.ndarray:
        if self.colorless:
            attributes = self.points
        else:
            # Merge coordinates and colors in alternating order
            attributes = np.concatenate((self.points, self.label_colors), axis=1)

        return attributes.flatten()  # flatten to single list

    def set_gl_background(self) -> None:
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
        GL.glPointSize(self.point_size)

    def draw_pointcloud(self) -> None:
        self.set_gl_background()
        stride = 3 * SIZE_OF_FLOAT

        # Bind position buffer
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.position_vbo)
        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glVertexPointer(3, GL.GL_FLOAT, stride, None)

        # Bind color buffer
        if config.getboolean("POINTCLOUD", "color_with_label"):
            color_vbo = self.label_vbo
        else:
            color_vbo = self.color_vbo
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, color_vbo)
        GL.glEnableClientState(GL.GL_COLOR_ARRAY)
        GL.glColorPointer(3, GL.GL_FLOAT, stride, None)
        GL.glDrawArrays(GL.GL_POINTS, 0, self.get_no_of_points())  # Draw the points

        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        GL.glDisableClientState(GL.GL_COLOR_ARRAY)
        # Release the buffer binding
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
