import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Set

import pkg_resources
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import QEvent
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QCompleter,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMessageBox,
)

from ..control.config_manager import config
from ..labeling_strategies import PickingStrategy, SpanningStrategy
from .settings_dialog import SettingsDialog
from .status_manager import StatusManager
from .viewer import GLWidget

if TYPE_CHECKING:
    from ..control.controller import Controller


def string_is_float(string: str, recect_negative: bool = False) -> bool:
    """Returns True if string can be converted to float"""
    try:
        decimal = float(string)
    except ValueError:
        return False
    if recect_negative and decimal < 0:
        return False
    return True


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


def set_keep_perspective(state: bool) -> None:
    config.set("USER_INTERFACE", "keep_perspective", str(state))


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
"""


class GUI(QtWidgets.QMainWindow):
    def __init__(self, control: "Controller") -> None:
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
        self.action_setpcdfolder: QtWidgets.QAction = self.findChild(
            QtWidgets.QAction, "action_setpcdfolder"
        )  # type: ignore
        self.action_setlabelfolder: QtWidgets.QAction = self.findChild(
            QtWidgets.QAction, "action_setlabelfolder"
        )  # type: ignore

        # Labels
        self.action_deletelabels: QtWidgets.QAction = self.findChild(
            QtWidgets.QAction, "action_deletealllabels"
        )  # type: ignore
        self.menu_setdefaultclass: QtWidgets.QMenu = self.findChild(
            QtWidgets.QMenu, "menu_setdefaultclass"
        )  # type: ignore
        self.actiongroup_defaultclass = QActionGroup(self.menu_setdefaultclass)

        # Settings
        self.action_zrotation: QtWidgets.QAction = self.findChild(
            QtWidgets.QAction, "action_zrotationonly"
        )  # type: ignore
        self.action_showfloor: QtWidgets.QAction = self.findChild(QtWidgets.QAction, "action_showfloor")  # type: ignore
        self.action_showorientation: QtWidgets.QAction = self.findChild(
            QtWidgets.QAction, "action_showorientation"
        )  # type: ignore
        self.action_saveperspective: QtWidgets.QAction = self.findChild(
            QtWidgets.QAction, "action_saveperspective"
        )  # type: ignore
        self.action_alignpcd: QtWidgets.QAction = self.findChild(QtWidgets.QAction, "action_alignpcd")  # type: ignore
        self.action_change_settings: QtWidgets.QAction = self.findChild(
            QtWidgets.QAction, "action_changesettings"
        )  # type: ignore

        # STATUS BAR
        self.status_bar: QtWidgets.QStatusBar = self.findChild(QtWidgets.QStatusBar, "statusbar")  # type: ignore
        self.status_manager = StatusManager(self.status_bar)

        # CENTRAL WIDGET
        self.glWidget: GLWidget = self.findChild(GLWidget, "openGLWidget")  # type: ignore

        # LEFT PANEL
        # point cloud management
        self.label_curr_pcd: QtWidgets.QLabel = self.findChild(QtWidgets.QLabel, "label_pcd_current")  # type: ignore
        self.button_prev_pcd: QtWidgets.QPushButton = self.findChild(QtWidgets.QPushButton, "button_pcd_prev")  # type: ignore
        self.button_next_pcd: QtWidgets.QPushButton = self.findChild(QtWidgets.QPushButton, "button_pcd_next")  # type: ignore
        self.button_set_pcd: QtWidgets.QPushButton = self.findChild(QtWidgets.QPushButton, "button_pcd_set")  # type: ignore
        self.progressbar_pcd: QtWidgets.QProgressBar = self.findChild(
            QtWidgets.QProgressBar, "progressbar_pcds"
        )  # type: ignore

        # bbox control section
        self.button_up: QtWidgets.QPushButton = self.findChild(QtWidgets.QPushButton, "button_bbox_up")  # type: ignore
        self.button_down: QtWidgets.QPushButton = self.findChild(QtWidgets.QPushButton, "button_bbox_down")  # type: ignore
        self.button_left: QtWidgets.QPushButton = self.findChild(QtWidgets.QPushButton, "button_bbox_left")  # type: ignore
        self.button_right: QtWidgets.QPushButton = self.findChild(QtWidgets.QPushButton, "button_bbox_right")  # type: ignore
        self.button_forward: QtWidgets.QPushButton = self.findChild(
            QtWidgets.QPushButton, "button_bbox_forward"
        )  # type: ignore
        self.button_backward: QtWidgets.QPushButton = self.findChild(
            QtWidgets.QPushButton, "button_bbox_backward"
        )  # type: ignore
        self.dial_zrotation: QtWidgets.QDial = self.findChild(QtWidgets.QDial, "dial_bbox_zrotation")  # type: ignore
        self.button_decr_dim: QtWidgets.QPushButton = self.findChild(QtWidgets.QPushButton, "button_bbox_decr")  # type: ignore
        self.button_incr_dim: QtWidgets.QPushButton = self.findChild(QtWidgets.QPushButton, "button_bbox_incr")  # type: ignore

        # 2d image viewer
        self.button_2D: QtWidgets.QPushButton = self.findChild(QtWidgets.QPushButton, "button_open_2D")  # type: ignore
        self.button_2D.setVisible(config.getboolean("USER_INTERFACE", "show_2d_image"))

        # label mode selection
        self.button_activate_picking: QtWidgets.QPushButton = self.findChild(
            QtWidgets.QPushButton, "button_pick_bbox"
        )  # type: ignore
        self.button_activate_spanning: QtWidgets.QPushButton = self.findChild(
            QtWidgets.QPushButton, "button_span_bbox"
        )  # type: ignore
        self.button_save_labels: QtWidgets.QPushButton = self.findChild(
            QtWidgets.QPushButton, "button_save_label"
        )  # type: ignore

        # RIGHT PANEL
        self.label_list: QtWidgets.QListWidget = self.findChild(QtWidgets.QListWidget, "label_list")  # type: ignore
        self.curr_class_edit: QtWidgets.QLineEdit = self.findChild(
            QtWidgets.QLineEdit, "current_class_lineedit"
        )  # type: ignore
        # self.curr_bbox_stats = self.findChild(QtWidgets.QLabel, "current_bbox_stats")
        self.button_deselect_label: QtWidgets.QPushButton = self.findChild(
            QtWidgets.QPushButton, "button_label_deselect"
        )  # type: ignore
        self.button_delete_label: QtWidgets.QPushButton = self.findChild(
            QtWidgets.QPushButton, "button_label_delete"
        )  # type: ignore

        # BOUNDING BOX PARAMETER EDITS
        self.pos_x_edit: QtWidgets.QLineEdit = self.findChild(QtWidgets.QLineEdit, "pos_x_edit")  # type: ignore
        self.pos_y_edit: QtWidgets.QLineEdit = self.findChild(QtWidgets.QLineEdit, "pos_y_edit")  # type: ignore
        self.pos_z_edit: QtWidgets.QLineEdit = self.findChild(QtWidgets.QLineEdit, "pos_z_edit")  # type: ignore

        self.length_edit: QtWidgets.QLineEdit = self.findChild(QtWidgets.QLineEdit, "length_edit")  # type: ignore
        self.width_edit: QtWidgets.QLineEdit = self.findChild(QtWidgets.QLineEdit, "width_edit")  # type: ignore
        self.height_edit: QtWidgets.QLineEdit = self.findChild(QtWidgets.QLineEdit, "height_edit")  # type: ignore

        self.rot_x_edit: QtWidgets.QLineEdit = self.findChild(QtWidgets.QLineEdit, "rot_x_edit")  # type: ignore
        self.rot_y_edit: QtWidgets.QLineEdit = self.findChild(QtWidgets.QLineEdit, "rot_y_edit")  # type: ignore
        self.rot_z_edit: QtWidgets.QLineEdit = self.findChild(QtWidgets.QLineEdit, "rot_z_edit")  # type: ignore

        self.all_line_edits = [
            self.curr_class_edit,
            self.pos_x_edit,
            self.pos_y_edit,
            self.pos_z_edit,
            self.length_edit,
            self.width_edit,
            self.height_edit,
            self.rot_x_edit,
            self.rot_y_edit,
            self.rot_z_edit,
        ]

        self.volume_label: QtWidgets.QLabel = self.findChild(QtWidgets.QLabel, "volume_value_label")  # type: ignore

        # Connect with controller
        self.controller = control
        self.controller.startup(self)

        # Connect all events to functions
        self.connect_events()
        self.set_checkbox_states()  # tick in menu
        self.update_label_completer()  # initialize label completer with classes in config
        self.update_default_object_class_menu()

        # Start event cycle
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(20)  # period, in milliseconds
        self.timer.timeout.connect(self.controller.loop_gui)
        self.timer.start()

    # Event connectors
    def connect_events(self) -> None:
        # POINTCLOUD CONTROL
        self.button_next_pcd.clicked.connect(
            lambda: self.controller.next_pcd(save=True)
        )
        self.button_prev_pcd.clicked.connect(self.controller.prev_pcd)

        # BBOX CONTROL
        self.button_up.pressed.connect(
            lambda: self.controller.bbox_controller.translate_along_z()
        )
        self.button_down.pressed.connect(
            lambda: self.controller.bbox_controller.translate_along_z(down=True)
        )
        self.button_left.pressed.connect(
            lambda: self.controller.bbox_controller.translate_along_x(left=True)
        )
        self.button_right.pressed.connect(
            self.controller.bbox_controller.translate_along_x
        )
        self.button_forward.pressed.connect(
            lambda: self.controller.bbox_controller.translate_along_y(forward=True)
        )
        self.button_set_pcd.pressed.connect(lambda: self.ask_custom_index())
        self.button_backward.pressed.connect(
            lambda: self.controller.bbox_controller.translate_along_y()
        )

        self.dial_zrotation.valueChanged.connect(
            lambda x: self.controller.bbox_controller.rotate_around_z(x, absolute=True)
        )
        self.button_decr_dim.clicked.connect(
            lambda: self.controller.bbox_controller.scale(decrease=True)
        )
        self.button_incr_dim.clicked.connect(
            lambda: self.controller.bbox_controller.scale()
        )

        # LABELING CONTROL
        self.curr_class_edit.textChanged.connect(
            self.controller.bbox_controller.set_classname
        )
        self.button_deselect_label.clicked.connect(
            self.controller.bbox_controller.deselect_bbox
        )
        self.button_delete_label.clicked.connect(
            self.controller.bbox_controller.delete_current_bbox
        )
        self.label_list.currentRowChanged.connect(
            self.controller.bbox_controller.set_active_bbox
        )

        # open_2D_img
        self.button_2D.pressed.connect(lambda: self.show_2d_image())

        # LABEL CONTROL
        self.button_activate_picking.clicked.connect(
            lambda: self.controller.drawing_mode.set_drawing_strategy(
                PickingStrategy(self)
            )
        )
        self.button_activate_spanning.clicked.connect(
            lambda: self.controller.drawing_mode.set_drawing_strategy(
                SpanningStrategy(self)
            )
        )
        self.button_save_labels.clicked.connect(self.controller.save)

        # BOUNDING BOX PARAMETER
        self.pos_x_edit.editingFinished.connect(
            lambda: self.update_bbox_parameter("pos_x")
        )
        self.pos_y_edit.editingFinished.connect(
            lambda: self.update_bbox_parameter("pos_y")
        )
        self.pos_z_edit.editingFinished.connect(
            lambda: self.update_bbox_parameter("pos_z")
        )

        self.length_edit.editingFinished.connect(
            lambda: self.update_bbox_parameter("length")
        )
        self.width_edit.editingFinished.connect(
            lambda: self.update_bbox_parameter("width")
        )
        self.height_edit.editingFinished.connect(
            lambda: self.update_bbox_parameter("height")
        )

        self.rot_x_edit.editingFinished.connect(
            lambda: self.update_bbox_parameter("rot_x")
        )
        self.rot_y_edit.editingFinished.connect(
            lambda: self.update_bbox_parameter("rot_y")
        )
        self.rot_z_edit.editingFinished.connect(
            lambda: self.update_bbox_parameter("rot_z")
        )

        # MENU BAR
        self.action_setpcdfolder.triggered.connect(self.change_pointcloud_folder)
        self.action_setlabelfolder.triggered.connect(self.change_label_folder)
        self.actiongroup_defaultclass.triggered.connect(
            self.change_default_object_class
        )
        self.action_deletelabels.triggered.connect(
            self.controller.bbox_controller.reset
        )
        self.action_zrotation.toggled.connect(set_zrotation_only)
        self.action_showfloor.toggled.connect(set_floor_visibility)
        self.action_showorientation.toggled.connect(set_orientation_visibility)
        self.action_saveperspective.toggled.connect(set_keep_perspective)
        self.action_alignpcd.toggled.connect(
            self.controller.align_mode.change_activation
        )
        self.action_change_settings.triggered.connect(self.show_settings_dialog)

    def set_checkbox_states(self) -> None:
        self.action_showfloor.setChecked(
            config.getboolean("USER_INTERFACE", "show_floor")
        )
        self.action_showorientation.setChecked(
            config.getboolean("USER_INTERFACE", "show_orientation")
        )
        self.action_zrotation.setChecked(
            config.getboolean("USER_INTERFACE", "z_rotation_only")
        )

    # Collect, filter and forward events to viewer
    def eventFilter(self, event_object, event) -> bool:
        # Keyboard Events
        # if (event.type() == QEvent.KeyPress) and (not self.line_edited_activated()):
        if (event.type() == QEvent.KeyPress) and (
            event_object == self
        ):  # TODO: Cleanup old filter
            self.controller.key_press_event(event)
            self.update_bbox_stats(self.controller.bbox_controller.get_active_bbox())
            return True  # TODO: Recheck pyqt behaviour
        elif event.type() == QEvent.KeyRelease:
            self.controller.key_release_event(event)

        # Mouse Events
        elif (event.type() == QEvent.MouseMove) and (event_object == self.glWidget):
            self.controller.mouse_move_event(event)
            self.update_bbox_stats(self.controller.bbox_controller.get_active_bbox())
        elif (event.type() == QEvent.Wheel) and (event_object == self.glWidget):
            self.controller.mouse_scroll_event(event)
            self.update_bbox_stats(self.controller.bbox_controller.get_active_bbox())
        elif event.type() == QEvent.MouseButtonDblClick and (
            event_object == self.glWidget
        ):
            self.controller.mouse_double_clicked(event)
            return True
        elif (event.type() == QEvent.MouseButtonPress) and (
            event_object == self.glWidget
        ):
            self.controller.mouse_clicked(event)
            self.update_bbox_stats(self.controller.bbox_controller.get_active_bbox())
        elif (event.type() == QEvent.MouseButtonPress) and (
            event_object != self.curr_class_edit
        ):
            self.curr_class_edit.clearFocus()
            self.update_bbox_stats(self.controller.bbox_controller.get_active_bbox())
        return False

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        logging.info("Closing window after saving ...")
        self.controller.save()
        self.timer.stop()
        a0.accept()

    def show_settings_dialog(self) -> None:
        dialog = SettingsDialog(self)
        dialog.exec()

    def show_2d_image(self):
        """Searches for a 2D image with the point cloud name and displays it in a new window."""
        image_folder = config.getpath("FILE", "image_folder")

        # Look for image files with the name of the point cloud
        pcd_name = self.controller.pcd_manager.pcd_path.stem
        image_file_pattern = re.compile(f"{pcd_name}+(\.(?i:(jpe?g|png|gif|bmp|tiff)))")

        try:
            image_name = next(
                filter(image_file_pattern.search, os.listdir(image_folder))
            )
        except StopIteration:
            QMessageBox.information(
                self,
                "No 2D Image File",
                (
                    f"Could not find a related image in the image folder ({image_folder}).\n"
                    "Check your path to the folder or if an image for this point cloud exists."
                ),
                QMessageBox.Ok,
            )
        else:
            image_path = image_folder.joinpath(image_name)
            image = QtGui.QImage(QtGui.QImageReader(str(image_path)).read())
            self.imageLabel = QLabel()
            self.imageLabel.setWindowTitle(f"2D Image ({image_name})")
            self.imageLabel.setPixmap(QPixmap.fromImage(image))
            self.imageLabel.show()

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
        self.label_curr_pcd.setText("Current: <em>%s</em>" % pcd_name)

    def init_progress(self, min_value, max_value):
        self.progressbar_pcd.setMinimum(min_value)
        self.progressbar_pcd.setMaximum(max_value)

    def update_progress(self, value) -> None:
        self.progressbar_pcd.setValue(value)

    def update_curr_class_edit(self, force: str = None) -> None:
        if force is not None:
            self.curr_class_edit.setText(force)
        else:
            bbox = self.controller.bbox_controller.get_active_bbox()
            if bbox:
                self.curr_class_edit.setText(bbox.get_classname())

    def update_label_completer(self, classnames=None) -> None:
        if classnames is None:
            classnames = set()
        classnames.update(config.getlist("LABEL", "object_classes"))
        self.curr_class_edit.setCompleter(QCompleter(classnames))

    def update_bbox_stats(self, bbox) -> None:
        viewing_precision = config.getint("USER_INTERFACE", "viewing_precision")
        if bbox and not self.line_edited_activated():
            self.pos_x_edit.setText(str(round(bbox.get_center()[0], viewing_precision)))
            self.pos_y_edit.setText(str(round(bbox.get_center()[1], viewing_precision)))
            self.pos_z_edit.setText(str(round(bbox.get_center()[2], viewing_precision)))

            self.length_edit.setText(
                str(round(bbox.get_dimensions()[0], viewing_precision))
            )
            self.width_edit.setText(
                str(round(bbox.get_dimensions()[1], viewing_precision))
            )
            self.height_edit.setText(
                str(round(bbox.get_dimensions()[2], viewing_precision))
            )

            self.rot_x_edit.setText(str(round(bbox.get_x_rotation(), 1)))
            self.rot_y_edit.setText(str(round(bbox.get_y_rotation(), 1)))
            self.rot_z_edit.setText(str(round(bbox.get_z_rotation(), 1)))

            self.volume_label.setText(str(round(bbox.get_volume(), viewing_precision)))

    def update_bbox_parameter(self, parameter: str) -> None:
        str_value = None
        self.setFocus()  # Changes the focus from QLineEdit to the window

        if parameter == "pos_x":
            str_value = self.pos_x_edit.text()
        if parameter == "pos_y":
            str_value = self.pos_y_edit.text()
        if parameter == "pos_z":
            str_value = self.pos_z_edit.text()
        if str_value and string_is_float(str_value):
            self.controller.bbox_controller.update_position(parameter, float(str_value))
            return

        if parameter == "length":
            str_value = self.length_edit.text()
        if parameter == "width":
            str_value = self.width_edit.text()
        if parameter == "height":
            str_value = self.height_edit.text()
        if str_value and string_is_float(str_value, recect_negative=True):
            self.controller.bbox_controller.update_dimension(
                parameter, float(str_value)
            )
            return

        if parameter == "rot_x":
            str_value = self.rot_x_edit.text()
        if parameter == "rot_y":
            str_value = self.rot_y_edit.text()
        if parameter == "rot_z":
            str_value = self.rot_z_edit.text()
        if str_value and string_is_float(str_value):
            self.controller.bbox_controller.update_rotation(parameter, float(str_value))
            return

    # Enables, disables the draw mode
    def activate_draw_modes(self, state: bool) -> None:
        self.button_activate_picking.setEnabled(state)
        self.button_activate_spanning.setEnabled(state)

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
        else:
            self.controller.pcd_manager.pcd_folder = path_to_folder
            self.controller.pcd_manager.read_pointcloud_folder()
            self.controller.pcd_manager.get_next_pcd()
            logging.info("Changed point cloud folder to %s!" % path_to_folder)

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
        else:
            self.controller.pcd_manager.label_manager.label_folder = path_to_folder
            self.controller.pcd_manager.label_manager.label_strategy.update_label_folder(
                path_to_folder
            )
            logging.info("Changed label folder to %s!" % path_to_folder)

    def update_default_object_class_menu(self, new_classes: Set[str] = None) -> None:
        object_classes = {
            str(class_name) for class_name in config.getlist("LABEL", "object_classes")
        }
        object_classes.update(new_classes or [])
        existing_classes = {
            action.text() for action in self.actiongroup_defaultclass.actions()
        }
        for object_class in object_classes.difference(existing_classes):
            action = self.actiongroup_defaultclass.addAction(
                object_class
            )  # TODO: Add limiter for number of classes
            action.setCheckable(True)
            if object_class == config.get("LABEL", "std_object_class"):
                action.setChecked(True)

        self.menu_setdefaultclass.addActions(self.actiongroup_defaultclass.actions())

    def change_default_object_class(self, action: QAction) -> None:
        config.set("LABEL", "std_object_class", action.text())
        logging.info("Changed default object class to %s.", action.text())

    def ask_custom_index(self):
        input_d = QInputDialog(self)
        self.input_pcd = input_d
        input_d.setInputMode(QInputDialog.IntInput)
        input_d.setWindowTitle("labelCloud")
        input_d.setLabelText("Insert Point Cloud number: ()")
        input_d.setIntMaximum(len(self.controller.pcd_manager.pcds) - 1)
        input_d.intValueChanged.connect(lambda val: self.update_dialog_pcd(val))
        input_d.intValueSelected.connect(lambda val: self.controller.custom_pcd(val))
        input_d.open()
        self.update_dialog_pcd(0)

    def update_dialog_pcd(self, value: int) -> None:
        pcd_path = self.controller.pcd_manager.pcds[value]
        self.input_pcd.setLabelText(f"Insert Point Cloud number: {pcd_path.name}")
