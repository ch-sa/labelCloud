import logging
import sys
import traceback
from pathlib import Path
from typing import Optional, Set

import pkg_resources
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import QEvent, pyqtSignal
from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QFileDialog,
    QMessageBox,
)

from ..control.config_manager import config
from ..definitions import Color3f, LabelingMode
from ..io.labels.config import LabelConfig
from ..io.pointclouds import BasePointCloudHandler
from ..model.point_cloud import PointCloud
from .settings_dialog import SettingsDialog  # type: ignore
from .startup.dialog import StartupDialog
from .status_manager import StatusManager
from .viewer import GLWidget



def set_floor_visibility(state: bool) -> None:
    logging.info(
        "%s floor grid (SHOW_FLOOR: %s).",
        "Activated" if state else "Deactivated",
        state,
    )
    config.set("USER_INTERFACE", "show_floor", str(state))


def set_orientation_visibility(state: bool) -> None:
    config.set("USER_INTERFACE", "show_orientation", str(state))


def set_zrotation_only(state: bool) -> None:
    config.set("USER_INTERFACE", "z_rotation_only", str(state))


def set_color_with_label(state: bool) -> None:
    config.set("POINTCLOUD", "color_with_label", str(state))


def set_keep_perspective(state: bool) -> None:
    config.set("USER_INTERFACE", "keep_perspective", str(state))


def set_propagate_labels(state: bool) -> None:
    config.set("LABEL", "propagate_labels", str(state))


# CSS file paths need to be set dynamically
STYLESHEET = """
    * {{
        background-color: #FFF;
        font-family: "DejaVu Sans", Arial;
    }}

    QMenu::item:selected {{
        background-color: #0000DD;
    }}

    QListWidget#label_list::item {{
        padding-left: 22px;
        padding-top: 7px;
        padding-bottom: 7px;
        background: url("{icons_dir}/cube-outline.svg") center left no-repeat;
    }}

    QListWidget#label_list::item:selected {{
        color: #FFF;
        border: none;
        background: rgb(0, 0, 255);
        background: url("{icons_dir}/cube-outline_white.svg") center left no-repeat, #0000ff;
    }}

    QComboBox#current_class_dropdown::item:checked{{
        color: gray;
    }}

    QComboBox#current_class_dropdown::item:selected {{
        color: #FFFFFF;
    }}

    QComboBox#current_class_dropdown{{
        selection-background-color: #0000FF;
    }}
"""


class GUI(QtWidgets.QMainWindow):
    on_key_press = pyqtSignal(QEvent)
    on_key_release = pyqtSignal(QEvent)

    on_mouse_move = pyqtSignal(QEvent)
    on_mouse_scroll = pyqtSignal(QEvent)
    on_mouse_clicked = pyqtSignal(QEvent)
    on_mouse_double_clicked = pyqtSignal(QEvent)

    on_change_point_cloud_folder = pyqtSignal(Path)
    on_change_label_folder = pyqtSignal(Path)

    exit_event = pyqtSignal()

    def __init__(self) -> None:
        super(GUI, self).__init__()
        uic.loadUi(
            pkg_resources.resource_filename(
                "labelCloud.resources.interfaces", "interface.ui"
            ),
            self,
        )
        self.resize(1500, 900)
        self.setWindowTitle("labelCloud")
        self.setStyleSheet(
            STYLESHEET.format(
                icons_dir=str(
                    Path(__file__)
                    .resolve()
                    .parent.parent.joinpath("resources")
                    .joinpath("icons")
                )
            )
        )

        # MENU BAR
        # File
        self.act_set_pcd_folder: QtWidgets.QAction
        self.act_set_label_folder: QtWidgets.QAction

        # Labels
        self.act_delete_all_labels: QtWidgets.QAction
        self.act_set_default_class: QtWidgets.QMenu
        self.actiongroup_default_class = QActionGroup(self.act_set_default_class)
        self.act_propagate_labels: QtWidgets.QAction

        # Settings
        self.act_z_rotation_only: QtWidgets.QAction
        self.act_color_with_label: QtWidgets.QAction
        self.act_show_floor: QtWidgets.QAction
        self.act_show_orientation: QtWidgets.QAction
        self.act_save_perspective: QtWidgets.QAction
        self.act_align_pcd: QtWidgets.QAction
        self.act_change_settings: QtWidgets.QAction

        # STATUS BAR
        self.status_bar: QtWidgets.QStatusBar
        self.status_manager = StatusManager(self.status_bar)

        # CENTRAL WIDGET
        self.gl_widget: GLWidget

        # LEFT PANEL
        # point cloud management
        self.label_current_pcd: QtWidgets.QLabel
        self.button_prev_pcd: QtWidgets.QPushButton
        self.button_next_pcd: QtWidgets.QPushButton
        self.button_set_pcd: QtWidgets.QPushButton
        self.progressbar_pcds: QtWidgets.QProgressBar

        # bbox control section
        self.button_bbox_up: QtWidgets.QPushButton
        self.button_bbox_down: QtWidgets.QPushButton
        self.button_bbox_left: QtWidgets.QPushButton
        self.button_bbox_right: QtWidgets.QPushButton
        self.button_bbox_forward: QtWidgets.QPushButton
        self.button_bbox_backward: QtWidgets.QPushButton
        self.dial_bbox_z_rotation: QtWidgets.QDial
        self.button_bbox_decrease_dimension: QtWidgets.QPushButton
        self.button_bbox_increase_dimension: QtWidgets.QPushButton

        # 2d image viewer
        self.button_show_image: QtWidgets.QPushButton
        self.button_show_image.setVisible(
            config.getboolean("USER_INTERFACE", "show_2d_image")
        )

        # label mode selection
        self.button_pick_bbox: QtWidgets.QPushButton
        self.button_span_bbox: QtWidgets.QPushButton
        self.button_save_label: QtWidgets.QPushButton

        # RIGHT PANEL
        self.label_list: QtWidgets.QListWidget
        self.current_class_dropdown: QtWidgets.QComboBox
        self.button_deselect_label: QtWidgets.QPushButton
        self.button_delete_label: QtWidgets.QPushButton
        self.button_assign_label: QtWidgets.QPushButton

        # label list actions
        # self.act_rename_class = QtWidgets.QAction("Rename class") #TODO: Implement!
        self.act_change_class_color = QtWidgets.QAction("Change class color")
        self.act_delete_class = QtWidgets.QAction("Delete label")
        self.act_crop_pointcloud_inside = QtWidgets.QAction("Save points inside as")
        self.label_list.addActions(
            [
                self.act_change_class_color,
                self.act_delete_class,
                self.act_crop_pointcloud_inside,
            ]
        )
        self.label_list.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)

        # BOUNDING BOX PARAMETER EDITS
        self.edit_pos_x: QtWidgets.QLineEdit
        self.edit_pos_y: QtWidgets.QLineEdit
        self.edit_pos_z: QtWidgets.QLineEdit

        self.edit_length: QtWidgets.QLineEdit
        self.edit_width: QtWidgets.QLineEdit
        self.edit_height: QtWidgets.QLineEdit

        self.edit_rot_x: QtWidgets.QLineEdit
        self.edit_rot_y: QtWidgets.QLineEdit
        self.edit_rot_z: QtWidgets.QLineEdit

        self.all_line_edits = [
            self.edit_pos_x,
            self.edit_pos_y,
            self.edit_pos_z,
            self.edit_length,
            self.edit_width,
            self.edit_height,
            self.edit_rot_x,
            self.edit_rot_y,
            self.edit_rot_z,
        ]

        self.label_volume: QtWidgets.QLabel

        # Connect all events to functions
        self.connect_to_signals()
        self.set_checkbox_states()  # tick in menu

        # Run startup dialog
        self.startup_dialog = StartupDialog()
        if self.startup_dialog.exec():
            pass
        else:
            sys.exit()
        # Segmentation only functionalities
        if LabelConfig().type == LabelingMode.OBJECT_DETECTION:
            self.button_assign_label.setVisible(False)
            self.act_color_with_label.setVisible(False)

    # Event connectors
    def connect_to_signals(self) -> None:

        # MENU BAR
        self.act_set_pcd_folder.triggered.connect(self.change_pointcloud_folder)
        self.act_set_label_folder.triggered.connect(self.change_label_folder)
        self.actiongroup_default_class.triggered.connect(
            self.change_default_object_class
        )

        self.act_propagate_labels.toggled.connect(set_propagate_labels)
        self.act_z_rotation_only.toggled.connect(set_zrotation_only)
        self.act_color_with_label.toggled.connect(set_color_with_label)
        self.act_show_floor.toggled.connect(set_floor_visibility)
        self.act_show_orientation.toggled.connect(set_orientation_visibility)
        self.act_save_perspective.toggled.connect(set_keep_perspective)
        self.act_change_settings.triggered.connect(self.show_settings_dialog)

    def set_checkbox_states(self) -> None:
        self.act_propagate_labels.setChecked(
            config.getboolean("LABEL", "propagate_labels")
        )
        self.act_show_floor.setChecked(
            config.getboolean("USER_INTERFACE", "show_floor")
        )
        self.act_show_orientation.setChecked(
            config.getboolean("USER_INTERFACE", "show_orientation")
        )
        self.act_z_rotation_only.setChecked(
            config.getboolean("USER_INTERFACE", "z_rotation_only")
        )
        self.act_color_with_label.setChecked(
            config.getboolean("POINTCLOUD", "color_with_label")
        )

    # Collect, filter and forward events to viewer
    def eventFilter(self, event_object, event) -> bool:
        # Keyboard Events
        if (event.type() == QEvent.KeyPress) and event_object in [
            self,
            self.label_list,  # otherwise steals focus for keyboard shortcuts
        ]:
            self.on_key_press.emit(event)
            return True  # TODO: Recheck pyqt behaviour
        elif event.type() == QEvent.KeyRelease:
            self.on_key_release.emit(event)

        # Mouse Events
        elif (event.type() == QEvent.MouseMove) and (event_object == self.gl_widget):
            self.on_mouse_move.emit(event)
        elif (event.type() == QEvent.Wheel) and (event_object == self.gl_widget):
            self.on_mouse_scroll.emit(event)
        elif event.type() == QEvent.MouseButtonDblClick and (
            event_object == self.gl_widget
        ):
            self.on_mouse_double_clicked.emit(event)
            return True
        elif (event.type() == QEvent.MouseButtonPress) and (
            event_object == self.gl_widget
        ):
            self.on_mouse_clicked.emit(event)
        elif (event.type() == QEvent.MouseButtonPress) and (
            event_object != self.current_class_dropdown
        ):
            self.current_class_dropdown.clearFocus()
            # self.update_bbox_stats(self.controller.bbox_controller.get_active_bbox())
        return False

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        logging.info("Closing window after saving ...")
        self.exit_event.emit()
        a0.accept()

    def show_settings_dialog(self) -> None:
        dialog = SettingsDialog(self)
        dialog.exec()



    def show_no_pointcloud_dialog(
        self, pcd_folder: Path, pcd_extensions: Set[str]
    ) -> None:
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setText(
            "<b>labelCloud could not find any valid point cloud files inside the "
            "specified folder.</b>"
        )
        msg.setInformativeText(
            f"Please copy all your point clouds into <code>{pcd_folder.resolve()}</code> or update "
            "the point cloud folder location. labelCloud supports the following point "
            f"cloud file formats:\n {', '.join(pcd_extensions)}."
        )
        msg.setWindowTitle("No Point Clouds Found")
        msg.exec_()

    # VISUALIZATION METHODS

    def set_pcd_label(self, pcd_name: str) -> None:
        self.label_current_pcd.setText("Current: <em>%s</em>" % pcd_name)

    def init_progress(self, min_value, max_value):
        self.progressbar_pcds.setMinimum(min_value)
        self.progressbar_pcds.setMaximum(max_value)

    def update_progress(self, value) -> None:
        self.progressbar_pcds.setValue(value)

    def update_bbox_stats(self, bbox) -> None:
        viewing_precision = config.getint("USER_INTERFACE", "viewing_precision")
        if bbox and not self.line_edited_activated():
            self.edit_pos_x.setText(str(round(bbox.get_center()[0], viewing_precision)))
            self.edit_pos_y.setText(str(round(bbox.get_center()[1], viewing_precision)))
            self.edit_pos_z.setText(str(round(bbox.get_center()[2], viewing_precision)))

            self.edit_length.setText(
                str(round(bbox.get_dimensions()[0], viewing_precision))
            )
            self.edit_width.setText(
                str(round(bbox.get_dimensions()[1], viewing_precision))
            )
            self.edit_height.setText(
                str(round(bbox.get_dimensions()[2], viewing_precision))
            )

            self.edit_rot_x.setText(str(round(bbox.get_x_rotation(), 1)))
            self.edit_rot_y.setText(str(round(bbox.get_y_rotation(), 1)))
            self.edit_rot_z.setText(str(round(bbox.get_z_rotation(), 1)))

            self.label_volume.setText(str(round(bbox.get_volume(), viewing_precision)))

    # Enables, disables the draw mode
    def activate_draw_modes(self, state: bool) -> None:
        self.button_pick_bbox.setEnabled(state)
        self.button_span_bbox.setEnabled(state)

    def line_edited_activated(self) -> bool:
        for line_edit in self.all_line_edits:
            if line_edit.hasFocus():
                return True
        return False

    def change_pointcloud_folder(self) -> None:
        path_to_folder = Path(
            QFileDialog.getExistingDirectory(
                self,
                "Change Point Cloud Folder",
                directory=config.get("FILE", "pointcloud_folder"),
            )
        )
        if not path_to_folder.is_dir():
            logging.warning("Please specify a valid folder path.")
            return

        self.on_change_point_cloud_folder.emit(path_to_folder)

    def change_label_folder(self) -> None:
        path_to_folder = Path(
            QFileDialog.getExistingDirectory(
                self,
                "Change Label Folder",
                directory=config.get("FILE", "label_folder"),
            )
        )
        if not path_to_folder.is_dir():
            logging.warning("Please specify a valid folder path.")
            return

        self.on_change_label_folder.emit(path_to_folder)

    def update_default_object_class_menu(
        self, new_classes: Optional[Set[str]] = None
    ) -> None:
        object_classes = set(LabelConfig().get_classes())

        object_classes.update(new_classes or [])
        existing_classes = {
            action.text() for action in self.actiongroup_default_class.actions()
        }
        for object_class in object_classes.difference(existing_classes):
            action = self.actiongroup_default_class.addAction(
                object_class
            )  # TODO: Add limiter for number of classes
            action.setCheckable(True)
            if object_class == LabelConfig().get_default_class_name():
                action.setChecked(True)

        self.act_set_default_class.addActions(self.actiongroup_default_class.actions())

    def change_default_object_class(self, action: QAction) -> None:
        LabelConfig().set_default_class(action.text())
        logging.info("Changed default object class to %s.", action.text())



    @staticmethod
    def save_point_cloud_as(pointcloud: PointCloud) -> None:
        extensions = BasePointCloudHandler.get_supported_extensions()
        make_filter = " ".join(["*" + extension for extension in extensions])
        file_filter = f"Point Cloud File ({make_filter})"
        file_name, _ = QFileDialog.getSaveFileName(
            caption="Select a file name to save the point cloud",
            directory=str(pointcloud.path.parent),
            filter=file_filter,
            initialFilter=file_filter,
        )
        if file_name == "":
            logging.warning("No file path provided. Ignored.")
            return

        try:
            path = Path(file_name)
            handler = BasePointCloudHandler.get_handler(path.suffix)
            handler.write_point_cloud(path, pointcloud)
        except Exception as e:
            msg = QMessageBox()
            msg.setWindowTitle("Failed to save a point cloud")
            msg.setText(e.__class__.__name__)
            msg.setInformativeText(traceback.format_exc())
            msg.setIcon(QMessageBox.Critical)
            msg.setStandardButtons(QMessageBox.Cancel)
            msg.exec_()
