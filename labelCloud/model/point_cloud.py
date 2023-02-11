import ctypes
import logging
from pathlib import Path
from typing import List, Optional, Tuple, cast

import numpy as np
import numpy.typing as npt
import OpenGL.GL as GL
from PyQt5.QtWidgets import QMessageBox

from labelCloud.io.labels.config import LabelConfig

from ..control.config_manager import config
from ..definitions import LabelingMode, Point3D, Rotations3D, Translation3D
from ..io.pointclouds import BasePointCloudHandler
from ..io.segmentations import BaseSegmentationHandler
from ..utils.color import colorize_points_with_height
from ..utils.logger import end_section, green, print_column, red, start_section, yellow
from . import Perspective

# Get size of float (4 bytes) for VBOs
SIZE_OF_FLOAT = ctypes.sizeof(ctypes.c_float)


def calculate_init_translation(
    center: Tuple[float, float, float], mins: npt.NDArray, maxs: npt.NDArray
) -> Point3D:
    """Calculates the initial translation (x, y, z) of the point cloud. Considers ...

    - the point cloud center
    - the point cloud extents
    - the far plane setting (caps zoom)
    """
    zoom = min(  # type: ignore
        np.linalg.norm(maxs - mins),
        config.getfloat("USER_INTERFACE", "far_plane") * 0.9,
    )
    return tuple(-np.add(center, [0, 0, zoom]))  # type: ignore


def consecutive(data: npt.NDArray[np.int64], stepsize=1) -> List[npt.NDArray[np.int64]]:
    """Split an 1-d array of integers to a list of 1-d array where the elements are consecutive"""
    return np.split(data, np.where(np.diff(data) != stepsize)[0] + 1)


class PointCloud(object):
    def __init__(
        self,
        path: Path,
        points: npt.NDArray[np.float32],
        colors: Optional[np.ndarray] = None,
        segmentation_labels: Optional[npt.NDArray[np.int8]] = None,
        init_translation: Optional[Tuple[float, float, float]] = None,
        init_rotation: Optional[Tuple[float, float, float]] = None,
        write_buffer: bool = True,
    ) -> None:
        start_section(f"Loading {path.name}")
        self.path = path
        self.points = points
        self.colors = colors if type(colors) == np.ndarray and len(colors) > 0 else None

        self.labels = None
        if LabelConfig().type == LabelingMode.SEMANTIC_SEGMENTATION:
            self.labels = segmentation_labels
            self.validate_segmentation_label()
            self.mix_ratio = config.getfloat("POINTCLOUD", "label_color_mix_ratio")

        self.vbo = None
        self.center: Point3D = tuple(np.sum(points[:, i]) / len(points) for i in range(3))  # type: ignore
        self.pcd_mins: npt.NDArray[np.float32] = np.amin(points, axis=0)
        self.pcd_maxs: npt.NDArray[np.float32] = np.amax(points, axis=0)
        self.init_translation: Point3D = init_translation or calculate_init_translation(
            self.center, self.pcd_mins, self.pcd_maxs
        )
        self.init_rotation: Rotations3D = init_rotation or tuple([0, 0, 0])  # type: ignore

        # Point cloud transformations
        self.trans_x, self.trans_y, self.trans_z = self.init_translation
        self.rot_x, self.rot_y, self.rot_z = self.init_rotation

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

    @property
    def point_size(self) -> float:
        return config.getfloat("POINTCLOUD", "point_size")

    def create_buffers(self) -> None:
        """Create 3 different buffers holding points, colors and label colors information"""
        self.colors = cast(npt.NDArray[np.float32], self.colors)
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
        self.colors = cast(npt.NDArray[np.float32], self.colors)
        if self.labels is not None:
            colors = LabelConfig().color_map[LabelConfig().class_order[self.labels]]
            return colors * self.mix_ratio + self.colors * (1 - self.mix_ratio)
        else:
            return self.colors

    def save_segmentation_labels(self, extension=".bin") -> None:
        label_path = (
            config.getpath("FILE", "segmentation_folder")
            / f"{self.path.stem}{extension}"
        )
        seg_handler: BaseSegmentationHandler = BaseSegmentationHandler.get_handler(
            label_path.suffix
        )()
        assert self.labels is not None
        self.validate_segmentation_label()
        seg_handler.overwrite_labels(label_path=label_path, labels=self.labels)
        logging.info(f"Writing segmentation labels to {label_path}")

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

        labels = None
        if LabelConfig().type == LabelingMode.SEMANTIC_SEGMENTATION:
            label_path = (
                config.getpath("FILE", "segmentation_folder") / f"{path.stem}.bin"
            )
            logging.info(f"Loading segmentation labels from {label_path}.")
            seg_handler = BaseSegmentationHandler.get_handler(label_path.suffix)()
            labels = seg_handler.read_or_create_labels(
                label_path=label_path, num_points=points.shape[0]
            )

        return cls(
            path,
            points,
            colors,
            labels,
            init_translation,
            init_rotation,
            write_buffer,
        )

    def validate_segmentation_label(self) -> None:
        unique_label_ids = set(np.unique(self.labels))  # type: ignore
        unique_class_ids = set(c.id for c in LabelConfig().classes)
        if not unique_class_ids.issuperset(unique_label_ids):
            msg = QMessageBox()
            msg.setWindowTitle("Invalid segmentation label")
            msg.setText(
                f"Segmentation labels {unique_label_ids} of `{self.path}` don't match with the label config {unique_class_ids}."
            )
            labels_to_replace = unique_label_ids.difference(unique_class_ids)
            msg.setInformativeText(
                f"""
                Do you want to overwrite 
                the undefined labels {labels_to_replace} with 
                default label `{LabelConfig().get_default_class_name()}` of id `{LabelConfig().default}`?
                """
            )
            msg.setIcon(QMessageBox.Critical)
            msg.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ok)

            msg.accepted.connect(self.replace_missing_labels_with_default)
            msg.exec_()

    def replace_missing_labels_with_default(self):
        unique_label_ids = set(np.unique(self.labels))
        unique_class_ids = set(c.id for c in LabelConfig().classes)
        labels_to_replace = list(unique_label_ids.difference(unique_class_ids))
        self.labels[np.isin(self.labels, labels_to_replace)] = LabelConfig().default

    def to_file(self, path: Optional[Path] = None) -> None:
        if not path:
            path = self.path
        BasePointCloudHandler.get_handler(path.suffix).write_point_cloud(
            path=path, pointcloud=self
        )

    @property
    def colorless(self) -> bool:
        return self.colors is None

    @property
    def color_with_label(self) -> bool:
        return config.getboolean("POINTCLOUD", "color_with_label")

    @property
    def has_label(self) -> bool:
        return self.labels is not None

    def update_selected_points_in_label_vbo(
        self, points_inside: npt.NDArray[np.bool_]
    ) -> None:
        """Send the selected updated label colors to label vbo. This function
        assumes the `self.label_colors[points_inside]` have been altered.
        This function only partially updates the label vbo to minimise the
        data sent to gpu. It leverages `glBufferSubData` method to perform
        partial update and `consecutive` method to find consecutive indexes
        so they can be updated in one single `glBufferSubData` call.
        """
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.label_vbo)
        inside_idx = np.where(points_inside)[0]
        if inside_idx.shape[0] == 0:
            logging.warning("No points are found inside the selected boxes.")
            return
        logging.debug(f"Update {len(inside_idx)} point colors in label VBO.")
        # find contiguous points so they can be updated together in one glBufferSubData call
        arrays = consecutive(inside_idx)
        label_color = self.label_colors
        stride = label_color.shape[1] * SIZE_OF_FLOAT
        for arr in arrays:
            colors: npt.NDArray[np.float32] = label_color[arr]
            # partially update label_vbo from positions arr[0] to arr[-1]
            GL.glBufferSubData(
                GL.GL_ARRAY_BUFFER,
                offset=arr[0] * stride,
                size=colors.nbytes,
                data=colors,
            )

    # GETTERS AND SETTERS
    def get_no_of_points(self) -> int:
        return len(self.points)

    def get_no_of_colors(self) -> int:
        return len(self.colors) if self.colors else 0

    def get_rotations(self) -> Rotations3D:
        return self.rot_x, self.rot_y, self.rot_z

    def get_translation(self) -> Translation3D:
        return self.trans_x, self.trans_y, self.trans_z

    def get_mins_maxs(self) -> Tuple[npt.NDArray, npt.NDArray]:
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
        if self.color_with_label:
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

    def get_filtered_pointcloud(
        self, indicies: npt.NDArray[np.bool_]
    ) -> Optional["PointCloud"]:
        assert self.points is not None
        assert self.colors is not None
        points = self.points[indicies]
        if points.shape[0] == 0:
            return None
        colors = self.colors[indicies]
        labels = self.labels[indicies] if self.labels is not None else None
        path = self.path.parent / (self.path.stem + "_cropped" + self.path.suffix)
        return PointCloud(
            path=path,
            points=points,
            colors=colors,
            segmentation_labels=labels,
            write_buffer=False,
        )

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
                else green(len(self.colors))  # type: ignore
                if len(self.colors) == len(self.points)  # type: ignore
                else red(len(self.colors)),  # type: ignore
            ]
        )
        print_column(["Point Cloud Center:", str(np.round(self.center, 2))])
        print_column(["Point Cloud Minimums:", str(np.round(self.pcd_mins, 2))])
        print_column(["Point Cloud Maximums:", str(np.round(self.pcd_maxs, 2))])
        print_column(
            ["Initial Translation:", str(np.round(self.init_translation, 2))], last=True
        )
