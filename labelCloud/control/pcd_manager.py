"""
Module to manage the point clouds (loading, navigation, floor alignment).
Sets the point cloud and original point cloud path. Initiate the writing to the virtual object buffer.
"""
import logging
from pathlib import Path
from shutil import copyfile
from typing import TYPE_CHECKING, List, Optional, Set, Tuple

import numpy as np
import open3d as o3d
import pkg_resources

from ..definitions import LabelingMode, Point3D
from ..io.labels.config import LabelConfig
from ..io.pointclouds import BasePointCloudHandler, Open3DHandler
from ..model import BBox, Perspective, PointCloud
from ..utils.logger import blue, green, print_column
from .config_manager import config
from .label_manager import LabelManager

if TYPE_CHECKING:
    from ..view.gui import GUI


class PointCloudManger(object):
    PCD_EXTENSIONS = BasePointCloudHandler.get_supported_extensions()
    ORIGINALS_FOLDER = "original_pointclouds"
    TRANSLATION_FACTOR = config.getfloat("POINTCLOUD", "STD_TRANSLATION")
    ZOOM_FACTOR = config.getfloat("POINTCLOUD", "STD_ZOOM")
    SEGMENTATION = LabelConfig().type == LabelingMode.SEMANTIC_SEGMENTATION

    def __init__(self) -> None:
        # Point cloud management
        self.pcd_folder = config.getpath("FILE", "pointcloud_folder")
        self.pcds: List[Path] = []
        self.current_id = -1

        self.view: GUI
        self.label_manager = LabelManager()

        # Point cloud control
        self.pointcloud: Optional[PointCloud] = None
        self.collected_object_classes: Set[
            str
        ] = set()  # TODO: this should integrate with the new label definition setup.
        self.saved_perspective: Optional[Perspective] = None

    @property
    def pcd_path(self) -> Path:
        return self.pcds[self.current_id]

    @property
    def pcd_name(self) -> Optional[str]:
        if self.current_id >= 0:
            return self.pcd_path.name
        return None

    def read_pointcloud_folder(self) -> None:
        """Checks point cloud folder and sets self.pcds to all valid point cloud file names."""
        if self.pcd_folder.is_dir():
            self.pcds = []
            for file in sorted(self.pcd_folder.iterdir()):
                if file.suffix in PointCloudManger.PCD_EXTENSIONS:
                    self.pcds.append(file)
        else:
            logging.warning(
                f"Point cloud path {self.pcd_folder} is not a valid directory."
            )

        if self.pcds:
            self.view.status_manager.set_message(
                f"Found {len(self.pcds)} point clouds in the point cloud folder."
            )
            self.update_pcd_infos()
        else:
            self.view.show_no_pointcloud_dialog(
                self.pcd_folder, PointCloudManger.PCD_EXTENSIONS
            )
            self.view.status_manager.set_message(
                "Please set the point cloud folder to a location that contains point cloud files."
            )
            self.pointcloud = PointCloud.from_file(
                Path(
                    pkg_resources.resource_filename(
                        "labelCloud.resources", "labelCloud_icon.pcd"
                    )
                )
            )
            self.update_pcd_infos(pointcloud_label=" – (select folder!)")

        self.view.init_progress(min_value=0, max_value=len(self.pcds) - 1)
        self.current_id = -1

    # GETTER
    def pcds_left(self) -> bool:
        return self.current_id + 1 < len(self.pcds)

    def get_next_pcd(self) -> None:
        logging.info("Loading next point cloud...")
        if self.pcds_left():
            self.current_id += 1
            self.save_current_perspective()
            self.pointcloud = PointCloud.from_file(
                self.pcd_path,
                self.saved_perspective,
                write_buffer=self.pointcloud is not None,
            )
            self.update_pcd_infos()
        else:
            logging.warning("No point clouds left!")

    def get_custom_pcd(self, pcd_index: int) -> None:
        logging.info("Loading custom point cloud...")
        if pcd_index < len(self.pcds):
            self.current_id = pcd_index
            self.save_current_perspective()
            self.pointcloud = PointCloud.from_file(
                self.pcd_path,
                self.saved_perspective,
                write_buffer=self.pointcloud is not None,
            )
            self.update_pcd_infos()
        else:
            logging.warning("This point cloud does not exists!")

    def get_prev_pcd(self) -> None:
        logging.info("Loading previous point cloud...")
        if self.current_id > 0:
            self.current_id -= 1
            self.save_current_perspective()
            self.pointcloud = PointCloud.from_file(
                self.pcd_path, self.saved_perspective
            )
            self.update_pcd_infos()
        else:
            raise Exception("No point cloud left for loading!")

    def populate_class_dropdown(self) -> None:
        # Add point label list
        self.view.current_class_dropdown.clear()
        assert self.pointcloud is not None

        for label_class in LabelConfig().classes:
            self.view.current_class_dropdown.addItem(label_class.name)

    def get_labels_from_file(self) -> List[BBox]:
        bboxes = self.label_manager.import_labels(self.pcd_path)
        logging.info(green("Loaded %s bboxes!" % len(bboxes)))
        return bboxes

    # SETTER
    def set_view(self, view: "GUI") -> None:
        self.view = view
        self.view.gl_widget.set_pointcloud_controller(self)
        self.view.update_default_object_class_menu(
            set(LabelConfig().get_classes().keys())
        )  # TODO: Move to better location

    def save_labels_into_file(self, bboxes: List[BBox]) -> None:
        if self.pcds:
            self.label_manager.export_labels(self.pcd_path, bboxes)
            self.collected_object_classes.update(
                {bbox.get_classname() for bbox in bboxes}
            )
        else:
            logging.warning("No point clouds to save labels for!")

    def save_current_perspective(self) -> None:
        if config.getboolean("USER_INTERFACE", "KEEP_PERSPECTIVE") and self.pointcloud:
            self.saved_perspective = Perspective.from_point_cloud(self.pointcloud)
            logging.info(f"Saved current perspective ({self.saved_perspective}).")

    # MANIPULATOR
    def rotate_around_x(self, dangle) -> None:
        assert self.pointcloud is not None
        self.pointcloud.set_rot_x(self.pointcloud.rot_x - dangle)

    def rotate_around_y(self, dangle) -> None:
        assert self.pointcloud is not None
        self.pointcloud.set_rot_y(self.pointcloud.rot_y - dangle)

    def rotate_around_z(self, dangle) -> None:
        assert self.pointcloud is not None
        self.pointcloud.set_rot_z(self.pointcloud.rot_z - dangle)

    def translate_along_x(self, distance) -> None:
        assert self.pointcloud is not None
        self.pointcloud.set_trans_x(
            self.pointcloud.trans_x - distance * PointCloudManger.TRANSLATION_FACTOR
        )

    def translate_along_y(self, distance) -> None:
        assert self.pointcloud is not None
        self.pointcloud.set_trans_y(
            self.pointcloud.trans_y + distance * PointCloudManger.TRANSLATION_FACTOR
        )

    def translate_along_z(self, distance) -> None:
        assert self.pointcloud is not None
        self.pointcloud.set_trans_z(
            self.pointcloud.trans_z - distance * PointCloudManger.TRANSLATION_FACTOR
        )

    def zoom_into(self, distance) -> None:
        assert self.pointcloud is not None
        zoom_distance = distance * PointCloudManger.ZOOM_FACTOR
        self.pointcloud.set_trans_z(self.pointcloud.trans_z + zoom_distance)

    def reset_translation(self) -> None:
        assert self.pointcloud is not None
        self.pointcloud.reset_perspective()

    def reset_rotation(self) -> None:
        assert self.pointcloud is not None
        self.pointcloud.rot_x, self.pointcloud.rot_y, self.pointcloud.rot_z = (0, 0, 0)

    def reset_transformations(self) -> None:
        self.reset_translation()
        self.reset_rotation()

    def rotate_pointcloud(
        self, axis: List[float], angle: float, rotation_point: Point3D
    ) -> None:
        assert self.pointcloud is not None and self.pcd_name is not None
        # Save current, original point cloud in ORIGINALS_FOLDER
        originals_path = self.pcd_folder.joinpath(PointCloudManger.ORIGINALS_FOLDER)
        originals_path.mkdir(parents=True, exist_ok=True)
        copyfile(
            str(self.pcd_path),
            str(originals_path.joinpath(self.pcd_name)),
        )
        logging.info("Copyied the original point cloud to %s.", blue(originals_path))

        # Rotate and translate point cloud
        rotation_matrix = o3d.geometry.get_rotation_matrix_from_axis_angle(
            np.multiply(axis, angle)
        )
        o3d_pointcloud = Open3DHandler.to_open3d_point_cloud(self.pointcloud)
        o3d_pointcloud.rotate(rotation_matrix, center=tuple(rotation_point))
        o3d_pointcloud.translate([0, 0, -rotation_point[2]])
        logging.info("Rotating point cloud...")
        print_column(["Angle:", str(np.round(angle, 3))])
        print_column(["Axis:", str(np.round(axis, 3))])
        print_column(["Point:", str(np.round(rotation_point, 3))], last=True)

        # Check if pointcloud is upside-down
        if abs(self.pointcloud.pcd_mins[2]) > self.pointcloud.pcd_maxs[2]:
            logging.warning("Point cloud is upside down, rotating ...")
            o3d_pointcloud.rotate(
                o3d.geometry.get_rotation_matrix_from_xyz([np.pi, 0, 0]),
                center=(0, 0, 0),
            )

        points, colors = Open3DHandler.to_point_cloud(o3d_pointcloud)
        self.pointcloud = PointCloud(
            self.pcd_path,
            points,
            colors,
            self.pointcloud.labels,
        )
        self.pointcloud.to_file()

    def assign_point_label_in_box(self, box: BBox) -> None:
        assert self.pointcloud is not None
        points = self.pointcloud.points
        points_inside = box.is_inside(points)

        # Relabel the points if its inside the box
        if self.pointcloud.has_label:
            assert self.pointcloud.labels is not None
            self.pointcloud.labels[points_inside] = (
                LabelConfig().get_class(box.classname).id
            )
            self.pointcloud.update_selected_points_in_label_vbo(points_inside)
            logging.info(
                f"Labeled {np.sum(points_inside)} points inside the current bounding box with label `{box.classname}`"
            )

    # HELPER

    def get_perspective(self) -> Tuple[float, float, float]:
        assert self.pointcloud is not None
        x_rotation = self.pointcloud.rot_x
        z_rotation = self.pointcloud.rot_z

        cosz = round(np.cos(np.deg2rad(z_rotation)), 1)
        sinz = -round(np.sin(np.deg2rad(z_rotation)), 1)

        # detect bottom-up state
        bottom_up = 1
        if 30 < x_rotation < 210:
            bottom_up = -1
        return cosz, sinz, bottom_up

    # UPDATE GUI

    def update_pcd_infos(self, pointcloud_label: Optional[str] = None) -> None:
        self.view.set_pcd_label(pointcloud_label or self.pcd_name or "")
        self.view.update_progress(self.current_id)

        if self.current_id <= 0:
            self.view.button_prev_pcd.setEnabled(False)
            if self.pcds:
                self.view.button_next_pcd.setEnabled(True)
        else:
            self.view.button_next_pcd.setEnabled(True)
            self.view.button_prev_pcd.setEnabled(True)
