import logging
import os
import re
from pathlib import Path
from typing import Optional

import numpy as np
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QColorDialog, QInputDialog, QLabel, QMessageBox

from ..definitions import BBOX_SIDES, Color3f, Colors, Context, LabelingMode
from ..io.labels.config import LabelConfig
from ..labeling_strategies import PickingStrategy, SpanningStrategy
from ..utils import oglhelper
from ..utils.validation import string_is_float
from ..view.gui import GUI
from .alignmode import AlignMode
from .bbox_controller import BoundingBoxController
from .config_manager import config
from .drawing_manager import DrawingManager
from .pcd_manager import PointCloudManger


class Controller:
    MOVEMENT_THRESHOLD = 0.1

    def __init__(self, view: GUI) -> None:
        """Initializes all controllers and managers."""
        self.view = view
        self.pcd_manager = PointCloudManger()
        self.bbox_controller = BoundingBoxController()

        # Drawing states
        self.drawing_mode = DrawingManager(self.bbox_controller)
        self.align_mode = AlignMode(self.pcd_manager)

        # Control states
        self.curr_cursor_pos: Optional[QPoint] = None  # updated by mouse movement
        self.last_cursor_pos: Optional[QPoint] = None  # updated by mouse click
        self.ctrl_pressed = False
        self.scroll_mode = False  # to enable the side-pulling

        # Correction states
        self.side_mode = False
        self.selected_side: Optional[str] = None

        self.connect_to_signals()
        self.startup()

    def connect_to_signals(self) -> None:
        # POINTCLOUD CONTROL
        self.view.button_next_pcd.clicked.connect(lambda: self.next_pcd(save=True))
        self.view.button_prev_pcd.clicked.connect(self.prev_pcd)

        # BBOX CONTROL
        self.view.button_bbox_up.pressed.connect(
            lambda: self.bbox_controller.translate_along_z()
        )
        self.view.button_bbox_down.pressed.connect(
            lambda: self.bbox_controller.translate_along_z(down=True)
        )
        self.view.button_bbox_left.pressed.connect(
            lambda: self.bbox_controller.translate_along_x(left=True)
        )
        self.view.button_bbox_right.pressed.connect(
            self.bbox_controller.translate_along_x
        )
        self.view.button_bbox_forward.pressed.connect(
            lambda: self.bbox_controller.translate_along_y(forward=True)
        )
        self.view.button_bbox_backward.pressed.connect(
            lambda: self.bbox_controller.translate_along_y()
        )

        self.view.dial_bbox_z_rotation.valueChanged.connect(
            lambda x: self.bbox_controller.rotate_around_z(x, absolute=True)
        )
        self.view.button_bbox_decrease_dimension.clicked.connect(
            lambda: self.bbox_controller.scale(decrease=True)
        )
        self.view.button_bbox_increase_dimension.clicked.connect(
            lambda: self.bbox_controller.scale()
        )
        self.view.button_set_pcd.pressed.connect(lambda: self.ask_custom_index())

        # OPEN 2D IMAGE
        self.view.button_show_image.pressed.connect(lambda: self.show_2d_image())

        # LABELING CONTROL
        self.view.current_class_dropdown.currentTextChanged.connect(
            self.bbox_controller.set_classname
        )
        self.view.button_deselect_label.clicked.connect(
            self.bbox_controller.deselect_bbox
        )
        self.view.button_delete_label.clicked.connect(
            self.bbox_controller.delete_current_bbox
        )
        self.view.label_list.currentRowChanged.connect(
            self.bbox_controller.set_active_bbox
        )
        self.view.button_assign_label.clicked.connect(
            self.bbox_controller.assign_point_label_in_active_box
        )

        # CONTEXT MENU
        self.view.act_delete_class.triggered.connect(
            self.bbox_controller.delete_current_bbox
        )
        self.view.act_crop_pointcloud_inside.triggered.connect(
            self.crop_pointcloud_inside_active_bbox
        )
        self.view.act_change_class_color.triggered.connect(self.change_label_color)

        # LABEL CONTROL
        self.view.button_pick_bbox.clicked.connect(
            lambda: self.drawing_mode.set_drawing_strategy(PickingStrategy(self.view))
        )
        self.view.button_span_bbox.clicked.connect(
            lambda: self.drawing_mode.set_drawing_strategy(SpanningStrategy(self.view))
        )
        self.view.button_save_label.clicked.connect(self.save)

        # BOUNDING BOX PARAMETER
        self.view.edit_pos_x.editingFinished.connect(
            lambda: self.update_bbox_parameter("pos_x")
        )
        self.view.edit_pos_y.editingFinished.connect(
            lambda: self.update_bbox_parameter("pos_y")
        )
        self.view.edit_pos_z.editingFinished.connect(
            lambda: self.update_bbox_parameter("pos_z")
        )

        self.view.edit_length.editingFinished.connect(
            lambda: self.update_bbox_parameter("length")
        )
        self.view.edit_width.editingFinished.connect(
            lambda: self.update_bbox_parameter("width")
        )
        self.view.edit_height.editingFinished.connect(
            lambda: self.update_bbox_parameter("height")
        )

        self.view.edit_rot_x.editingFinished.connect(
            lambda: self.update_bbox_parameter("rot_x")
        )
        self.view.edit_rot_y.editingFinished.connect(
            lambda: self.update_bbox_parameter("rot_y")
        )
        self.view.edit_rot_z.editingFinished.connect(
            lambda: self.update_bbox_parameter("rot_z")
        )

        # MENU BAR
        self.view.act_delete_all_labels.triggered.connect(self.bbox_controller.reset)
        self.view.act_align_pcd.toggled.connect(self.align_mode.change_activation)
        self.view.on_change_point_cloud_folder.connect(self.change_point_cloud_folder)

        # KEY EVENTS
        self.view.on_key_press.connect(self.key_press_event)
        self.view.on_key_release.connect(self.key_release_event)

        # MOUSE EVENTS
        self.view.on_mouse_move.connect(self.mouse_move_event)
        self.view.on_mouse_scroll.connect(self.mouse_scroll_event)

        self.view.on_mouse_clicked.connect(self.mouse_clicked)
        self.view.on_mouse_double_clicked.connect(self.mouse_double_clicked)

        self.view.exit_event

        # UPDATE BBOX STATS
        update_bbox_stats = lambda: self.view.update_bbox_stats(
            self.bbox_controller.get_active_bbox()
        )
        self.view.on_key_press.connect(update_bbox_stats)
        self.view.on_mouse_move.connect(update_bbox_stats)
        self.view.on_mouse_scroll.connect(update_bbox_stats)
        self.view.on_mouse_clicked.connect(update_bbox_stats)

    def ask_custom_index(self):  # TODO: Refactor
        input_d = QInputDialog(self)
        self.input_pcd = input_d
        input_d.setInputMode(QInputDialog.IntInput)
        input_d.setWindowTitle("labelCloud")
        input_d.setLabelText("Insert Point Cloud number: ()")
        input_d.setIntMaximum(len(self.pcd_manager.pcds) - 1)
        input_d.intValueChanged.connect(lambda val: self.update_dialog_pcd(val))
        input_d.intValueSelected.connect(lambda val: self.custom_pcd(val))
        input_d.open()
        self.update_dialog_pcd(0)

    def update_dialog_pcd(self, value: int) -> None:
        pcd_path = self.pcd_manager.pcds[value]
        self.input_pcd.setLabelText(f"Insert Point Cloud number: {pcd_path.name}")

    def show_2d_image(self):  # TODO: Refactor
        """Searches for a 2D image with the point cloud name and displays it in a new window."""
        image_folder = config.getpath("FILE", "image_folder")

        # Look for image files with the name of the point cloud
        pcd_name = self.pcd_manager.pcd_path.stem
        image_file_pattern = re.compile(
            f"{pcd_name}+(\\.(?i:(jpe?g|png|gif|bmp|tiff)))"
        )

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

    def change_label_color(self):
        bbox = self.bbox_controller.get_active_bbox()
        LabelConfig().set_class_color(
            bbox.classname, Color3f.from_qcolor(QColorDialog.getColor())
        )

    def update_bbox_parameter(self, parameter: str) -> None:
        str_value = None
        self.view.setFocus()  # Changes the focus from QLineEdit to the window

        if parameter == "pos_x":
            str_value = self.view.edit_pos_x.text()
        if parameter == "pos_y":
            str_value = self.view.edit_pos_y.text()
        if parameter == "pos_z":
            str_value = self.view.edit_pos_z.text()
        if str_value and string_is_float(str_value):
            self.bbox_controller.update_position(parameter, float(str_value))
            return

        if parameter == "length":
            str_value = self.view.edit_length.text()
        if parameter == "width":
            str_value = self.view.edit_width.text()
        if parameter == "height":
            str_value = self.view.edit_height.text()
        if str_value and string_is_float(str_value, recect_negative=True):
            self.bbox_controller.update_dimension(parameter, float(str_value))
            return

        if parameter == "rot_x":
            str_value = self.view.edit_rot_x.text()
        if parameter == "rot_y":
            str_value = self.view.edit_rot_y.text()
        if parameter == "rot_z":
            str_value = self.view.edit_rot_z.text()
        if str_value and string_is_float(str_value):
            self.bbox_controller.update_rotation(parameter, float(str_value))
            return

    def change_point_cloud_folder(self, path_to_folder: Path) -> None:
        self.pcd_manager.pcd_folder = path_to_folder
        self.pcd_manager.read_pointcloud_folder()
        self.pcd_manager.get_next_pcd()
        logging.info("Changed point cloud folder to %s!" % path_to_folder)

    def change_label_folder(self, path_to_folder: Path) -> None:
        self.pcd_manager.label_manager.label_folder = path_to_folder
        self.pcd_manager.label_manager.label_strategy.update_label_folder(
            path_to_folder
        )
        logging.info("Changed label folder to %s!" % path_to_folder)

    def exit(self) -> None:
        self.save()
        self.timer.stop()

    def startup(self) -> None:
        """Sets the view in all controllers and dependent modules; Loads labels from file."""
        self.bbox_controller.set_view(self.view)
        self.pcd_manager.set_view(self.view)
        self.drawing_mode.set_view(self.view)
        self.align_mode.set_view(self.view)
        self.view.gl_widget.set_bbox_controller(self.bbox_controller)
        self.bbox_controller.pcd_manager = self.pcd_manager

        # Read labels from folders
        self.pcd_manager.read_pointcloud_folder()
        self.next_pcd(save=False)

        # Start event cycle
        self.timer = QtCore.QTimer(self.view)
        self.timer.setInterval(20)  # period, in milliseconds
        self.timer.timeout.connect(self.loop_gui)
        self.timer.start()

    def loop_gui(self) -> None:
        """Function collection called during each event loop iteration."""
        self.set_crosshair()
        self.set_selected_side()
        self.view.gl_widget.updateGL()

    # POINT CLOUD METHODS
    def next_pcd(self, save: bool = True) -> None:
        if save:
            self.save()
        if self.pcd_manager.pcds_left():
            previous_bboxes = self.bbox_controller.bboxes
            self.pcd_manager.get_next_pcd()
            self.reset()
            self.bbox_controller.set_bboxes(self.pcd_manager.get_labels_from_file())

            if not self.bbox_controller.bboxes and config.getboolean(
                "LABEL", "propagate_labels"
            ):
                self.bbox_controller.set_bboxes(previous_bboxes)
        else:
            self.view.update_progress(len(self.pcd_manager.pcds))
            self.view.button_next_pcd.setEnabled(False)

    def prev_pcd(self) -> None:
        self.save()
        if self.pcd_manager.current_id > 0:
            self.pcd_manager.get_prev_pcd()
            self.reset()
            self.bbox_controller.set_bboxes(self.pcd_manager.get_labels_from_file())

    def custom_pcd(self, custom: int) -> None:
        self.save()
        self.pcd_manager.get_custom_pcd(custom)
        self.reset()
        self.bbox_controller.set_bboxes(self.pcd_manager.get_labels_from_file())

    # CONTROL METHODS
    def save(self) -> None:
        """Saves all bounding boxes and optionally segmentation labels in the label file."""
        self.pcd_manager.save_labels_into_file(self.bbox_controller.bboxes)

        if LabelConfig().type == LabelingMode.SEMANTIC_SEGMENTATION:
            assert self.pcd_manager.pointcloud is not None
            self.pcd_manager.pointcloud.save_segmentation_labels()

    def reset(self) -> None:
        """Resets the controllers and bounding boxes from the current screen."""
        self.bbox_controller.reset()
        self.drawing_mode.reset()
        self.align_mode.reset()

    # CORRECTION METHODS
    def set_crosshair(self) -> None:
        """Sets the crosshair position in the glWidget to the current cursor position."""
        if self.curr_cursor_pos:
            self.view.gl_widget.crosshair_col = Colors.GREEN.value
            self.view.gl_widget.crosshair_pos = (
                self.curr_cursor_pos.x(),
                self.curr_cursor_pos.y(),
            )

    def set_selected_side(self) -> None:
        """Sets the currently hovered bounding box side in the glWidget."""
        if (
            (not self.side_mode)
            and self.curr_cursor_pos
            and self.bbox_controller.has_active_bbox()
            and (not self.scroll_mode)
        ):
            _, self.selected_side = oglhelper.get_intersected_sides(
                self.curr_cursor_pos.x(),
                self.curr_cursor_pos.y(),
                self.bbox_controller.get_active_bbox(),  # type: ignore
                self.view.gl_widget.modelview,
                self.view.gl_widget.projection,
            )
        if (
            self.selected_side
            and (not self.ctrl_pressed)
            and self.bbox_controller.has_active_bbox()
        ):
            self.view.gl_widget.crosshair_col = Colors.RED.value
            side_vertices = self.bbox_controller.get_active_bbox().get_vertices()  # type: ignore
            self.view.gl_widget.selected_side_vertices = side_vertices[
                BBOX_SIDES[self.selected_side]
            ]
            self.view.status_manager.set_message(
                "Scroll to change the bounding box dimension.",
                context=Context.SIDE_HOVERED,
            )
        else:
            self.view.gl_widget.selected_side_vertices = np.array([])
            self.view.status_manager.clear_message(Context.SIDE_HOVERED)

    # EVENT PROCESSING
    def mouse_clicked(self, a0: QtGui.QMouseEvent) -> None:
        """Triggers actions when the user clicks the mouse."""
        self.last_cursor_pos = a0.pos()

        if (
            self.drawing_mode.is_active()
            and (a0.buttons() & QtCore.Qt.LeftButton)
            and (not self.ctrl_pressed)
        ):
            self.drawing_mode.register_point(a0.x(), a0.y(), correction=True)

        elif self.align_mode.is_active and (not self.ctrl_pressed):
            self.align_mode.register_point(
                self.view.gl_widget.get_world_coords(a0.x(), a0.y(), correction=False)
            )

        elif self.selected_side:
            self.side_mode = True

    def mouse_double_clicked(self, a0: QtGui.QMouseEvent) -> None:
        """Triggers actions when the user double clicks the mouse."""
        self.bbox_controller.select_bbox_by_ray(a0.x(), a0.y())

    def mouse_move_event(self, a0: QtGui.QMouseEvent) -> None:
        """Triggers actions when the user moves the mouse."""
        self.curr_cursor_pos = a0.pos()  # Updates the current mouse cursor position

        # Methods that use absolute cursor position
        if self.drawing_mode.is_active() and (not self.ctrl_pressed):
            self.drawing_mode.register_point(
                a0.x(), a0.y(), correction=True, is_temporary=True
            )

        elif self.align_mode.is_active and (not self.ctrl_pressed):
            self.align_mode.register_tmp_point(
                self.view.gl_widget.get_world_coords(a0.x(), a0.y(), correction=False)
            )

        if self.last_cursor_pos:
            dx = (
                self.last_cursor_pos.x() - a0.x()
            ) / 5  # Calculate relative movement from last click position
            dy = (self.last_cursor_pos.y() - a0.y()) / 5

            if (
                self.ctrl_pressed
                and (not self.drawing_mode.is_active())
                and (not self.align_mode.is_active)
            ):
                if a0.buttons() & QtCore.Qt.LeftButton:  # bbox rotation
                    self.bbox_controller.rotate_with_mouse(-dx, -dy)
                elif a0.buttons() & QtCore.Qt.RightButton:  # bbox translation
                    new_center = self.view.gl_widget.get_world_coords(
                        a0.x(), a0.y(), correction=True
                    )
                    self.bbox_controller.set_center(*new_center)  # absolute positioning
            else:
                if a0.buttons() & QtCore.Qt.LeftButton:  # pcd rotation
                    self.pcd_manager.rotate_around_x(dy)
                    self.pcd_manager.rotate_around_z(dx)
                elif a0.buttons() & QtCore.Qt.RightButton:  # pcd translation
                    self.pcd_manager.translate_along_x(dx)
                    self.pcd_manager.translate_along_y(dy)

            # Reset scroll locks of "side scrolling" for significant cursor movements
            if dx > Controller.MOVEMENT_THRESHOLD or dy > Controller.MOVEMENT_THRESHOLD:
                if self.side_mode:
                    self.side_mode = False
                else:
                    self.scroll_mode = False
        self.last_cursor_pos = a0.pos()

    def mouse_scroll_event(self, a0: QtGui.QWheelEvent) -> None:
        """Triggers actions when the user scrolls the mouse wheel."""
        if self.selected_side:
            self.side_mode = True

        if (
            self.drawing_mode.is_active()
            and (not self.ctrl_pressed)
            and self.drawing_mode.drawing_strategy is not None
        ):
            self.drawing_mode.drawing_strategy.register_scrolling(a0.angleDelta().y())
        elif self.side_mode and self.bbox_controller.has_active_bbox():
            self.bbox_controller.get_active_bbox().change_side(  # type: ignore
                self.selected_side, -a0.angleDelta().y() / 4000  # type: ignore
            )  # ToDo implement method
        else:
            self.pcd_manager.zoom_into(a0.angleDelta().y())
            self.scroll_mode = True

    def key_press_event(self, a0: QtGui.QKeyEvent) -> None:
        """Triggers actions when the user presses a key."""

        # Reset position to intial value
        if a0.key() == QtCore.Qt.Key_Control:
            self.ctrl_pressed = True
            self.view.status_manager.set_message(
                "Hold right mouse button to translate or left mouse button to rotate "
                "the bounding box.",
                context=Context.CONTROL_PRESSED,
            )

        # Reset point cloud pose to intial rotation and translation
        elif (a0.key() == QtCore.Qt.Key_R) or (a0.key() == QtCore.Qt.Key_Home):
            self.pcd_manager.reset_transformations()
            logging.info("Reseted position to default.")

        elif a0.key() == QtCore.Qt.Key_Delete:  # Delete active bbox
            self.bbox_controller.delete_current_bbox()

        # Save labels to file
        elif (a0.key() == QtCore.Qt.Key_S) and self.ctrl_pressed:
            self.save()

        elif a0.key() == QtCore.Qt.Key_Escape:
            if self.drawing_mode.is_active():
                self.drawing_mode.reset()
                logging.info("Resetted drawn points!")
            elif self.align_mode.is_active:
                self.align_mode.reset()
                logging.info("Resetted selected points!")

        # BBOX MANIPULATION
        elif (a0.key() == QtCore.Qt.Key_Y) or (a0.key() == QtCore.Qt.Key_Comma):
            # z rotate counterclockwise
            self.bbox_controller.rotate_around_z()
        elif (a0.key() == QtCore.Qt.Key_X) or (a0.key() == QtCore.Qt.Key_Period):
            # z rotate clockwise
            self.bbox_controller.rotate_around_z(clockwise=True)
        elif a0.key() == QtCore.Qt.Key_C:
            # y rotate counterclockwise
            self.bbox_controller.rotate_around_y()
        elif a0.key() == QtCore.Qt.Key_V:
            # y rotate clockwise
            self.bbox_controller.rotate_around_y(clockwise=True)
        elif a0.key() == QtCore.Qt.Key_B:
            # x rotate counterclockwise
            self.bbox_controller.rotate_around_x()
        elif a0.key() == QtCore.Qt.Key_N:
            # x rotate clockwise
            self.bbox_controller.rotate_around_x(clockwise=True)
        elif (a0.key() == QtCore.Qt.Key_W) or (a0.key() == QtCore.Qt.Key_Up):
            # move backward
            self.bbox_controller.translate_along_y()
        elif (a0.key() == QtCore.Qt.Key_S) or (a0.key() == QtCore.Qt.Key_Down):
            # move forward
            self.bbox_controller.translate_along_y(forward=True)
        elif (a0.key() == QtCore.Qt.Key_A) or (a0.key() == QtCore.Qt.Key_Left):
            # move left
            self.bbox_controller.translate_along_x(left=True)
        elif (a0.key() == QtCore.Qt.Key_D) or (a0.key() == QtCore.Qt.Key_Right):
            # move right
            self.bbox_controller.translate_along_x()
        elif (a0.key() == QtCore.Qt.Key_Q) or (a0.key() == QtCore.Qt.Key_PageUp):
            # move up
            self.bbox_controller.translate_along_z()
        elif (a0.key() == QtCore.Qt.Key_E) or (a0.key() == QtCore.Qt.Key_PageDown):
            # move down
            self.bbox_controller.translate_along_z(down=True)

    def key_release_event(self, a0: QtGui.QKeyEvent) -> None:
        """Triggers actions when the user releases a key."""
        if a0.key() == QtCore.Qt.Key_Control:
            self.ctrl_pressed = False
            self.view.status_manager.clear_message(Context.CONTROL_PRESSED)

    def crop_pointcloud_inside_active_bbox(self) -> None:
        bbox = self.bbox_controller.get_active_bbox()
        assert bbox is not None
        assert self.pcd_manager.pointcloud is not None
        points_inside = bbox.is_inside(self.pcd_manager.pointcloud.points)
        pointcloud = self.pcd_manager.pointcloud.get_filtered_pointcloud(points_inside)
        if pointcloud is None:
            logging.warning("No points found inside the box. Ignored.")
            return
        self.view.save_point_cloud_as(pointcloud)
