"""
Module to manage the point clouds (loading, navigation, floor alignment).
Sets the point cloud and original point cloud path. Initiate the writing to the virtual object buffer.
"""
import ntpath
import os
from dataclasses import dataclass
from shutil import copyfile
from typing import TYPE_CHECKING, List, Optional, Tuple

import numpy as np
import open3d as o3d

from ..model import BBox, PointCloud
from .config_manager import config
from .label_manager import LabelManager

if TYPE_CHECKING:
    from ..view.gui import GUI

import pkg_resources


@dataclass
class Perspective(object):
    zoom: float
    rotation: Tuple[float, float, float]


def color_pointcloud(points, z_min, z_max) -> np.ndarray:
    palette = np.loadtxt(
        pkg_resources.resource_filename("labelCloud.ressources", "rocket-palette.txt")
    )
    palette_len = len(palette) - 1

    colors = np.zeros(points.shape)
    for ind, height in enumerate(points[:, 2]):
        colors[ind] = palette[round((height - z_min) / (z_max - z_min) * palette_len)]
    return colors


class PointCloudManger(object):
    PCD_EXTENSIONS = [".pcd", ".ply", ".pts", ".xyz", ".xyzn", ".xyzrgb", ".bin"]
    ORIGINALS_FOLDER = "original_pointclouds"
    TRANSLATION_FACTOR = config.getfloat("POINTCLOUD", "STD_TRANSLATION")
    ZOOM_FACTOR = config.getfloat("POINTCLOUD", "STD_ZOOM")
    COLORIZE = config.getboolean("POINTCLOUD", "COLORLESS_COLORIZE")

    def __init__(self) -> None:
        # Point cloud management
        self.pcd_folder = config.get("FILE", "pointcloud_folder")
        self.pcds = []
        self.current_id = -1

        self.current_o3d_pcd = None
        self.view: Optional[GUI] = None
        self.label_manager = LabelManager()

        # Point cloud control
        self.pointcloud = None
        self.collected_object_classes = set()
        self.saved_perspective: Perspective = None

    def read_pointcloud_folder(self) -> None:
        """Checks point cloud folder and sets self.pcds to all valid point cloud file names."""
        if os.path.isdir(self.pcd_folder):
            self.pcds = []
            for file in sorted(os.listdir(self.pcd_folder), key=str.casefold):
                if file.endswith(tuple(PointCloudManger.PCD_EXTENSIONS)):
                    self.pcds.append(file)
        else:
            print(f"Point cloud path {self.pcd_folder} is not a valid directory.")

        if self.pcds:
            self.view.update_status(
                f"Found {len(self.pcds)} point clouds in the point cloud folder."
            )
            self.update_pcd_infos()
        else:
            self.view.show_no_pointcloud_dialog(
                self.pcd_folder, PointCloudManger.PCD_EXTENSIONS
            )
            self.view.update_status(
                "Please set the point cloud folder to a location that contains point cloud files."
            )
            self.pointcloud = self.load_pointcloud(
                pkg_resources.resource_filename(
                    "labelCloud.ressources", "labelCloud_icon.pcd"
                )
            )
            self.update_pcd_infos(pointcloud_label=" – (select folder!)")

        self.view.init_progress(min_value=0, max_value=len(self.pcds))
        self.current_id = -1

    # GETTER
    def pcds_left(self) -> bool:
        return self.current_id + 1 < len(self.pcds)

    def get_next_pcd(self) -> None:
        print("Loading next point cloud...")
        if self.pcds_left():
            self.current_id += 1
            self.pointcloud = self.load_pointcloud(self.get_current_path())
            self.update_pcd_infos()
        else:
            print("No point clouds left!")

    def get_prev_pcd(self) -> None:
        print("Loading previous point cloud...")
        if self.current_id > 0:
            self.current_id -= 1
            self.pointcloud = self.load_pointcloud(self.get_current_path())
            self.update_pcd_infos()
        else:
            raise Exception("No point cloud left for loading!")

    def get_pointcloud(self) -> PointCloud:
        return self.pointcloud

    def get_current_name(self) -> str:
        if self.current_id >= 0:
            return self.pcds[self.current_id]

    def get_current_details(self) -> Tuple[str, int, int]:
        if self.current_id >= 0:
            return self.get_current_name(), self.current_id + 1, len(self.pcds)

    def get_current_path(self) -> str:
        return os.path.join(self.pcd_folder, self.pcds[self.current_id])

    def get_labels_from_file(self) -> List[BBox]:
        bboxes = self.label_manager.import_labels(self.get_current_name())
        print("Loaded %s bboxes!" % len(bboxes))
        return bboxes

    # SETTER
    def set_view(self, view: "GUI") -> None:
        self.view = view
        self.view.glWidget.set_pointcloud_controller(self)

    def save_labels_into_file(self, bboxes: List[BBox]) -> None:
        if self.pcds:
            self.label_manager.export_labels(self.get_current_path(), bboxes)
            self.collected_object_classes.update(
                {bbox.get_classname() for bbox in bboxes}
            )
            self.view.update_label_completer(self.collected_object_classes)
            self.view.update_default_object_class_menu(self.collected_object_classes)
        else:
            print("No point clouds to save labels for!")

    def save_current_perspective(self, active: bool = True) -> None:
        if active and self.pointcloud:
            self.saved_perspective = Perspective(
                zoom=self.pointcloud.trans_z,
                rotation=tuple(self.pointcloud.get_rotations()),
            )
            print(f"Saved current perspective ({self.saved_perspective}).")
        else:
            self.saved_perspective = None
            print("Reset saved perspective.")

    # MANIPULATOR
    def load_pointcloud(self, path_to_pointcloud: str) -> PointCloud:
        print("=" * 20, "Loading", ntpath.basename(path_to_pointcloud), "=" * 20)

        if config.getboolean("USER_INTERFACE", "keep_perspective"):
            self.save_current_perspective()

        if (
            os.path.splitext(path_to_pointcloud)[1] == ".bin"
        ):  # Loading binary pcds with numpy
            bin_pcd = np.fromfile(path_to_pointcloud, dtype=np.float32)
            points = bin_pcd.reshape((-1, 4))[
                :, 0:3
            ]  # Reshape and drop reflection values
            self.current_o3d_pcd = o3d.geometry.PointCloud(
                o3d.utility.Vector3dVector(points)
            )
        else:
            self.current_o3d_pcd = o3d.io.read_point_cloud(
                path_to_pointcloud
            )  # Load point cloud with open3d

        tmp_pcd = PointCloud(path_to_pointcloud)
        tmp_pcd.points = np.asarray(self.current_o3d_pcd.points).astype(
            "float32"
        )  # Unpack point cloud
        tmp_pcd.colors = np.asarray(self.current_o3d_pcd.colors).astype("float32")

        tmp_pcd.colorless = len(tmp_pcd.colors) == 0

        print("Number of Points: %s" % len(tmp_pcd.points))
        # Calculate and set initial translation to view full pointcloud
        tmp_pcd.center = self.current_o3d_pcd.get_center()
        tmp_pcd.set_mins_maxs()

        if PointCloudManger.COLORIZE and tmp_pcd.colorless:
            print("Generating colors for colorless point cloud!")
            min_height, max_height = tmp_pcd.get_min_max_height()
            tmp_pcd.colors = color_pointcloud(tmp_pcd.points, min_height, max_height)
            tmp_pcd.colorless = False

        max_dims = np.subtract(tmp_pcd.pcd_maxs, tmp_pcd.pcd_mins)
        diagonal = min(
            np.linalg.norm(max_dims),
            config.getfloat("USER_INTERFACE", "far_plane") * 0.9,
        )

        tmp_pcd.init_translation = -self.current_o3d_pcd.get_center() - [0, 0, diagonal]

        if self.saved_perspective != None:
            tmp_pcd.init_translation = tuple(
                list(tmp_pcd.init_translation[:2]) + [self.saved_perspective.zoom]
            )
            tmp_pcd.set_rotations(*self.saved_perspective.rotation)

        tmp_pcd.reset_translation()
        tmp_pcd.print_details()
        if self.pointcloud is not None:  # Skip first pcd to intialize OpenGL first
            tmp_pcd.write_vbo()

        print("Successfully loaded point cloud from %s!" % path_to_pointcloud)
        if tmp_pcd.colorless:
            print(
                "Did not find colors for the loaded point cloud, drawing in colorless mode!"
            )
        print("=" * 65)
        return tmp_pcd

    def rotate_around_x(self, dangle) -> None:
        self.pointcloud.set_rot_x(self.pointcloud.rot_x - dangle)

    def rotate_around_y(self, dangle) -> None:
        self.pointcloud.set_rot_y(self.pointcloud.rot_y - dangle)

    def rotate_around_z(self, dangle) -> None:
        self.pointcloud.set_rot_z(self.pointcloud.rot_z - dangle)

    def translate_along_x(self, distance) -> None:
        self.pointcloud.set_trans_x(
            self.pointcloud.trans_x - distance * PointCloudManger.TRANSLATION_FACTOR
        )

    def translate_along_y(self, distance) -> None:
        self.pointcloud.set_trans_y(
            self.pointcloud.trans_y + distance * PointCloudManger.TRANSLATION_FACTOR
        )

    def translate_along_z(self, distance) -> None:
        self.pointcloud.set_trans_z(
            self.pointcloud.trans_z - distance * PointCloudManger.TRANSLATION_FACTOR
        )

    def zoom_into(self, distance) -> None:
        zoom_distance = distance * PointCloudManger.ZOOM_FACTOR
        self.pointcloud.set_trans_z(self.pointcloud.trans_z + zoom_distance)

    def reset_translation(self) -> None:
        self.pointcloud.reset_translation()

    def reset_rotation(self) -> None:
        self.pointcloud.rot_x, self.pointcloud.rot_y, self.pointcloud.rot_z = (0, 0, 0)

    def reset_transformations(self) -> None:
        self.reset_translation()
        self.reset_rotation()

    def rotate_pointcloud(
        self, axis: List[float], angle: float, rotation_point: List[float]
    ) -> None:
        # Save current, original point cloud in ORIGINALS_FOLDER
        originals_path = os.path.join(
            self.pcd_folder, PointCloudManger.ORIGINALS_FOLDER
        )
        if not os.path.exists(originals_path):
            os.mkdir(originals_path)
        copyfile(
            self.get_current_path(),
            os.path.join(originals_path, self.get_current_name()),
        )
        # Rotate and translate point cloud
        rotation_matrix = o3d.geometry.get_rotation_matrix_from_axis_angle(
            np.multiply(axis, angle)
        )
        self.current_o3d_pcd.rotate(rotation_matrix, center=tuple(rotation_point))
        self.current_o3d_pcd.translate([0, 0, -rotation_point[2]])

        # Check if pointcloud is upside-down
        pcd_mins = np.amin(self.current_o3d_pcd.points, axis=0)
        pcd_maxs = np.amax(self.current_o3d_pcd.points, axis=0)

        if abs(pcd_mins[2]) > pcd_maxs[2]:
            print("Point cloud is upside down, rotating ...")
            self.current_o3d_pcd.rotate(
                o3d.geometry.get_rotation_matrix_from_xyz([np.pi, 0, 0]),
                center=(0, 0, 0),
            )

        save_path = self.get_current_path()
        if os.path.splitext(save_path)[1] == ".bin":
            save_path = save_path[:-4] + ".pcd"

        o3d.io.write_point_cloud(save_path, self.current_o3d_pcd)
        self.pointcloud = self.load_pointcloud(save_path)

    # HELPER

    def get_perspective(self) -> Tuple[float, float, float]:
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

    def update_pcd_infos(self, pointcloud_label: str = None) -> None:
        self.view.set_pcd_label(pointcloud_label or self.get_current_name())
        self.view.update_progress(self.current_id)

        if self.current_id <= 0:
            self.view.button_prev_pcd.setEnabled(False)
            if self.pcds:
                self.view.button_next_pcd.setEnabled(True)
        else:
            self.view.button_next_pcd.setEnabled(True)
            self.view.button_prev_pcd.setEnabled(True)
