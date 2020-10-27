"""
Module to manage the point clouds (loading, navigation, floor alignment).
Sets the point cloud and original point cloud path. Initiate the writing to the virtual object buffer.
"""

import os
import sys
from typing import List, Tuple, TYPE_CHECKING, Set

import numpy as np
import open3d as o3d
from PyQt5.QtWidgets import QCompleter, QMessageBox

from modules.control import config_parser
from modules.control.label_manager import LabelManager
from modules.model.bbox import BBox
from modules.model.point_cloud import PointCloud

if TYPE_CHECKING:
    from modules.view.gui import GUI


def find_pcd_files(path: str) -> List[str]:
    pcd_files = []

    for file in os.listdir(path):
        if file.endswith(PointCloudControler.PCD_EXTENSIONS):
            pcd_files.append(file)

    return sorted(pcd_files)


def get_unique_classnames(bboxes: List[BBox]) -> Set[str]:
    for box in bboxes:
        BBox.LIST_OF_CLASSES.add(box.get_classname())
    return BBox.LIST_OF_CLASSES


def show_no_pcd_dialog():
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setText("Did not find any point cloud.")
    msg.setInformativeText("Please copy all your point clouds into the <i>pointcloud</i> folder. "
                           "If you already have done that check the supported formats %s."
                           % str(PointCloudControler.PCD_EXTENSIONS))
    msg.setWindowTitle("No Point Clouds Found")
    msg.exec_()


class PointCloudControler:
    PCD_EXTENSIONS = (".pcd", ".ply", ".pts", ".xyz", ".xyzn", "xyzrgb")
    ORIGINALS_FOLDER = "original_pointclouds"
    TRANSLATION_FACTOR = config_parser.get_pointcloud_settings("STD_TRANSLATION")
    ZOOM_FACTOR = config_parser.get_pointcloud_settings("STD_ZOOM")

    def __init__(self):
        # Point cloud management
        self.pcd_folder = config_parser.get_file_settings("POINTCLOUD_FOLDER")
        self.pcds = find_pcd_files(self.pcd_folder)
        self.no_of_pcds = len(self.pcds)
        self.current_id = -1
        self.current_o3d_pcd = None
        self.view = None
        self.label_manager = LabelManager()
        # Point cloud control
        self.pointcloud = None

    # GETTER
    def pcds_left(self) -> bool:
        return self.current_id + 1 < self.no_of_pcds

    def get_next_pcd(self):
        print("Loading next point cloud...")
        if self.pcds_left():
            self.current_id += 1
            self.pointcloud = self.load_pointcloud(self.get_current_path())
            self.update_pcd_infos()
        else:
            if self.current_id == -1:
                show_no_pcd_dialog()
                sys.exit()
            raise Exception("No point cloud left for loading!")

    def get_prev_pcd(self):
        print("Loading previous point cloud...")
        if self.current_id > 0:
            self.current_id -= 1
            self.pointcloud = self.load_pointcloud(self.get_current_path())
            self.update_pcd_infos()
        else:
            raise Exception("No point cloud left for loading!")

    def get_pointcloud(self):
        return self.pointcloud

    def get_current_name(self) -> str:
        if self.current_id >= 0:
            return self.pcds[self.current_id]

    def get_current_details(self) -> Tuple[str, int, int]:
        if self.current_id >= 0:
            return self.get_current_name(), self.current_id + 1, self.no_of_pcds

    def get_current_path(self) -> str:
        return os.path.join(self.pcd_folder, self.pcds[self.current_id])

    def get_labels_from_file(self):
        bboxes = self.label_manager.import_labels(self.get_current_name())
        print("Loaded %s bboxes!" % len(bboxes))
        return bboxes

    # SETTER
    def set_view(self, view: 'GUI') -> None:
        self.view = view
        self.view.glWidget.set_pointcloud_controler(self)
        self.get_next_pcd()

    def save_labels_into_file(self, bboxes: List[BBox]):
        self.label_manager.export_labels(self.get_current_path(), bboxes)
        self.update_label_completer(get_unique_classnames(bboxes))

    # MANIPULATOR
    def load_pointcloud(self, path_to_pointcloud: str) -> PointCloud:
        self.current_o3d_pcd = o3d.io.read_point_cloud(path_to_pointcloud)  # Load point cloud with open3d
        tmp_pcd = PointCloud(path_to_pointcloud)
        tmp_pcd.points = np.asarray(self.current_o3d_pcd.points).astype("float32")  # Unpack point cloud
        tmp_pcd.colors = np.asarray(self.current_o3d_pcd.colors).astype("float32")
        tmp_pcd.colorless = len(tmp_pcd.colors) == 0
        # Calculate and set initial translation to view full pointcloud
        tmp_pcd.center = self.current_o3d_pcd.get_center()
        tmp_pcd.set_mins_maxs()
        max_dims = np.subtract(tmp_pcd.pcd_maxs, tmp_pcd.pcd_mins)
        init_trans_z = tmp_pcd.center[2] - max(((max(max_dims[:2]) / 2) / np.tan(0.39) + 2), -15)
        init_trans_x = -tmp_pcd.center[0] + max_dims[0] * 0.1
        init_trans_y = -tmp_pcd.center[1] + max_dims[1] * -0.1
        tmp_pcd.init_translation = init_trans_x, init_trans_y, init_trans_z
        tmp_pcd.reset_translation()
        tmp_pcd.print_details()
        if self.pointcloud is not None:  # Skip first pcd to intialize OpenGL first
            tmp_pcd.write_vbo()

        print("Loaded point cloud from %s with %s points: " % (path_to_pointcloud, len(tmp_pcd.points)))
        if tmp_pcd.colorless:
            print("Did not find colors for the loaded point cloud, drawing in colorless mode!")
        return tmp_pcd

    def rotate_around_x(self, dangle):
        self.pointcloud.set_rot_x(self.pointcloud.rot_x - dangle)

    def rotate_around_y(self, dangle):
        self.pointcloud.set_rot_y(self.pointcloud.rot_y - dangle)

    def rotate_around_z(self, dangle):
        self.pointcloud.set_rot_z(self.pointcloud.rot_z - dangle)

    def translate_along_x(self, distance):
        self.pointcloud.set_trans_x(self.pointcloud.trans_x - distance * PointCloudControler.TRANSLATION_FACTOR)

    def translate_along_y(self, distance):
        self.pointcloud.set_trans_y(self.pointcloud.trans_y + distance * PointCloudControler.TRANSLATION_FACTOR)

    def translate_along_z(self, distance):
        self.pointcloud.set_trans_z(self.pointcloud.trans_z - distance * PointCloudControler.TRANSLATION_FACTOR)

    def zoom_into(self, distance):
        zoom_distance = distance * PointCloudControler.ZOOM_FACTOR
        self.pointcloud.set_trans_z(self.pointcloud.trans_z + zoom_distance)

    def reset_translation(self):
        self.pointcloud.reset_translation()

    def reset_rotation(self):
        self.pointcloud.rot_x, self.pointcloud.rot_y, self.pointcloud.rot_z = (0, 0, 0)

    def reset_transformations(self):
        self.reset_translation()
        self.reset_rotation()

    def rotate_pointcloud(self, axis: List[float], angle: float, rotation_point: List[float]) -> None:
        # Save current, original point cloud in ORIGINALS_FOLDER
        originals_path = os.path.join(self.pcd_folder, PointCloudControler.ORIGINALS_FOLDER)
        if not os.path.exists(originals_path):
            os.mkdir(originals_path)
        o3d.io.write_point_cloud(os.path.join(originals_path, self.get_current_name()), self.current_o3d_pcd)

        # Rotate and translate point cloud
        rotation_matrix = o3d.geometry.get_rotation_matrix_from_axis_angle(np.multiply(axis, angle))
        self.current_o3d_pcd.rotate(rotation_matrix, center=tuple(rotation_point))
        self.current_o3d_pcd.translate([0, 0, -rotation_point[2]])

        # Check if pointcloud is upside-down
        pcd_mins = np.amin(self.current_o3d_pcd.points, axis=0)
        pcd_maxs = np.amax(self.current_o3d_pcd.points, axis=0)

        if abs(pcd_mins[2]) > pcd_maxs[2]:
            print("Point cloud is upside down, rotating ...")
            self.current_o3d_pcd.rotate(o3d.geometry.get_rotation_matrix_from_xyz([np.pi, 0, 0]), center=(0, 0, 0))

        # Overwrite current point cloud and reload
        o3d.io.write_point_cloud(self.get_current_path(), self.current_o3d_pcd)
        self.pointcloud = self.load_pointcloud(self.get_current_path())

    # HELPER

    def get_perspective(self):
        x_rotation = self.pointcloud.rot_x
        # y_rotation = self.pcdc.get_pointcloud().rot_y
        z_rotation = self.pointcloud.rot_z
        # print("PCD-ROTX/y/z: %s, %s, %s" % (x_rotation, y_rotation, z_rotation))

        cosz = round(np.cos(np.deg2rad(z_rotation)), 1)
        sinz = -round(np.sin(np.deg2rad(z_rotation)), 1)

        # detect bottom-up state
        bottom_up = 1
        if 30 < x_rotation < 210:
            bottom_up = -1
            print("bottom up")

        return cosz, sinz, bottom_up

    # UPDATE GUI
    def update_label_completer(self, classnames: Set[str]):
        self.view.curr_class_edit.setCompleter(QCompleter(classnames))

    def update_pcd_infos(self):
        self.view.set_pcd_label(*self.get_current_details())
        self.view.update_progress(self.current_id / self.no_of_pcds)

        if self.current_id <= 0:
            self.view.button_prev_pcd.setEnabled(False)
        else:
            self.view.button_next_pcd.setEnabled(True)
            self.view.button_prev_pcd.setEnabled(True)
