import os
from typing import TYPE_CHECKING

from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtCore import QEvent, Qt

from control import config_parser
from view.viewer import GLWidget

if TYPE_CHECKING:
    from control.controller import Controller


def string_is_float(string: str, recect_negative: bool = False) -> bool:
    """Returns True if string can be converted to float"""
    try:
        decimal = float(string)
    except ValueError:
        return False
    if recect_negative and decimal < 0:
        return False
    return True


class GUI(QtWidgets.QMainWindow):
    VIEWING_PRECISION = int(config_parser.get_label_settings("VIEWING_PRECISION"))

    def __init__(self, control: 'Controller'):
        super(GUI, self).__init__()
        print(os.getcwd())
        uic.loadUi("labelCloud/ressources/interface.ui", self)
        self.resize(1500, 900)
        self.setWindowTitle('labelCloud')

        # MENU BAR
        # File
        self.action_setpcdfolder = self.findChild(QtWidgets.QAction, "action_setpcdfolder")
        self.action_setpcdfolder.setEnabled(False)  # TODO: Implement
        self.action_setlabelfolder = self.findChild(QtWidgets.QAction, "action_setlabelfolder")
        self.action_setlabelfolder.setEnabled(False)  # TODO: Implement
        self.action_loadsinglepcd = self.findChild(QtWidgets.QAction, "action_loadsinglepcd")
        self.action_loadsinglepcd.setEnabled(False)  # TODO: Implement

        # Labels
        self.action_zrotation = self.findChild(QtWidgets.QAction, "action_zrotationonly")
        self.action_deletelabels = self.findChild(QtWidgets.QAction, "action_deletealllabels")
        self.action_setclasslist = self.findChild(QtWidgets.QAction, "action_setclasslist")
        self.action_setclasslist.setEnabled(False)  # TODO: Implement
        self.action_setstddimensions = self.findChild(QtWidgets.QAction, "action_setstddimensions")
        self.action_setstddimensions.setEnabled(False)  # TODO: Implement
        self.action_setstdtransformations = self.findChild(QtWidgets.QAction, "action_setstdtransformations")
        self.action_setstddimensions.setEnabled(False)  # TODO: Implement

        # Settings
        self.action_pointsize = self.findChild(QtWidgets.QAction, "action_pointsize")
        self.action_pointsize.setEnabled(False)  # TODO: Implement
        self.action_showfloor = self.findChild(QtWidgets.QAction, "action_showfloor")
        self.action_showorientation = self.findChild(QtWidgets.QAction, "action_showorientation")
        self.action_alignpcd = self.findChild(QtWidgets.QAction, "action_alignpcd")

        # STATUS BAR
        self.status = self.findChild(QtWidgets.QStatusBar, "statusbar")
        self.mode_status = QtWidgets.QLabel("Navigation Mode")
        self.mode_status.setStyleSheet("font-weight: bold; font-size: 14px; min-width: 235px;")
        self.mode_status.setAlignment(Qt.AlignCenter)
        self.status.addWidget(self.mode_status, stretch=0)
        self.tmp_status = QtWidgets.QLabel()
        self.tmp_status.setStyleSheet("font-size: 14px;")
        self.status.addWidget(self.tmp_status, stretch=1)

        # CENTRAL WIDGET
        self.glWidget: GLWidget = self.findChild(GLWidget, "openGLWidget")

        # LEFT PANEL
        # point cloud management
        self.label_curr_pcd = self.findChild(QtWidgets.QLabel, "label_pcd_current")
        self.button_prev_pcd = self.findChild(QtWidgets.QPushButton, "button_pcd_prev")
        self.button_next_pcd = self.findChild(QtWidgets.QPushButton, "button_pcd_next")
        self.progressbar_pcd = self.findChild(QtWidgets.QProgressBar, "progressbar_pcds")

        # bbox control section
        self.button_up = self.findChild(QtWidgets.QPushButton, "button_bbox_up")
        self.button_down = self.findChild(QtWidgets.QPushButton, "button_bbox_down")
        self.button_left = self.findChild(QtWidgets.QPushButton, "button_bbox_left")
        self.button_right = self.findChild(QtWidgets.QPushButton, "button_bbox_right")
        self.button_forward = self.findChild(QtWidgets.QPushButton, "button_bbox_forward")
        self.button_backward = self.findChild(QtWidgets.QPushButton, "button_bbox_backward")
        self.dial_zrotation = self.findChild(QtWidgets.QDial, "dial_bbox_zrotation")
        self.button_decr_dim = self.findChild(QtWidgets.QPushButton, "button_bbox_decr")
        self.button_incr_dim = self.findChild(QtWidgets.QPushButton, "button_bbox_incr")

        # label mode selection
        self.button_activate_picking = self.findChild(QtWidgets.QPushButton, "button_pick_bbox")
        self.button_activate_drag = self.findChild(QtWidgets.QPushButton, "button_drag_bbox")  # ToDo Remove?
        self.button_activate_drag.setVisible(False)
        self.button_activate_spanning = self.findChild(QtWidgets.QPushButton, "button_span_bbox")
        self.button_save_labels = self.findChild(QtWidgets.QPushButton, "button_save_label")

        # RIGHT PANEL
        self.label_list = self.findChild(QtWidgets.QListWidget, "label_list")
        self.curr_class_edit = self.findChild(QtWidgets.QLineEdit, "current_class_lineedit")
        # self.curr_bbox_stats = self.findChild(QtWidgets.QLabel, "current_bbox_stats")
        self.button_deselect_label = self.findChild(QtWidgets.QPushButton, "button_label_deselect")
        self.button_delete_label = self.findChild(QtWidgets.QPushButton, "button_label_delete")

        # BOUNDING BOX PARAMETER EDITS
        self.pos_x_edit = self.findChild(QtWidgets.QLineEdit, "pos_x_edit")
        self.pos_y_edit = self.findChild(QtWidgets.QLineEdit, "pos_y_edit")
        self.pos_z_edit = self.findChild(QtWidgets.QLineEdit, "pos_z_edit")

        self.length_edit = self.findChild(QtWidgets.QLineEdit, "length_edit")
        self.width_edit = self.findChild(QtWidgets.QLineEdit, "width_edit")
        self.height_edit = self.findChild(QtWidgets.QLineEdit, "height_edit")

        self.rot_x_edit = self.findChild(QtWidgets.QLineEdit, "rot_x_edit")
        self.rot_y_edit = self.findChild(QtWidgets.QLineEdit, "rot_y_edit")
        self.rot_z_edit = self.findChild(QtWidgets.QLineEdit, "rot_z_edit")

        self.all_line_edits = [self.curr_class_edit, self.pos_x_edit, self.pos_y_edit, self.pos_z_edit,
                               self.length_edit, self.width_edit, self.height_edit,
                               self.rot_x_edit, self.rot_y_edit, self.rot_z_edit]

        self.volume_label = self.findChild(QtWidgets.QLabel, "volume_value_label")

        # Connect with controller
        self.controller = control
        self.controller.set_view(self)

        # Connect all events to functions
        self.connect_events()

        # Start event cycle
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(20)  # period, in milliseconds
        self.timer.timeout.connect(self.controller.loop_gui)
        self.timer.start()

    # Event connectors
    def connect_events(self):
        # POINTCLOUD CONTROL
        self.button_next_pcd.clicked.connect(self.controller.next_pcd)
        self.button_prev_pcd.clicked.connect(self.controller.prev_pcd)

        # BBOX CONTROL
        self.button_up.pressed.connect(lambda: self.controller.bbox_controller.translate_along_z())
        self.button_down.pressed.connect(lambda: self.controller.bbox_controller.translate_along_z(down=True))
        self.button_left.pressed.connect(lambda: self.controller.bbox_controller.translate_along_x(left=True))
        self.button_right.pressed.connect(self.controller.bbox_controller.translate_along_x)
        self.button_forward.pressed.connect(lambda: self.controller.bbox_controller.translate_along_y(forward=True))
        self.button_backward.pressed.connect(lambda: self.controller.bbox_controller.translate_along_y())

        self.dial_zrotation.valueChanged.connect(
            lambda x: self.controller.bbox_controller.rotate_around_z(x, absolute=True)
        )
        self.button_decr_dim.clicked.connect(lambda: self.controller.bbox_controller.scale(decrease=True))
        self.button_incr_dim.clicked.connect(lambda: self.controller.bbox_controller.scale())

        # LABELING CONTROL
        self.curr_class_edit.textChanged.connect(self.controller.bbox_controller.set_classname)
        self.button_deselect_label.clicked.connect(self.controller.bbox_controller.deselect_bbox)
        self.button_delete_label.clicked.connect(self.controller.bbox_controller.delete_current_bbox)
        self.label_list.currentRowChanged.connect(self.controller.bbox_controller.set_active_bbox)

        # LABEL CONTROL
        self.button_activate_picking.clicked.connect(lambda: self.controller.drawing_mode.
                                                     set_drawing_strategy("PickingStrategy"))
        self.button_activate_spanning.clicked.connect(lambda: self.controller.drawing_mode.
                                                      set_drawing_strategy("SpanStrategy"))
        self.button_activate_drag.clicked.connect(lambda: self.controller.drawing_mode.
                                                  set_drawing_strategy("RectangleStrategy"))
        self.button_save_labels.clicked.connect(self.controller.save)

        # BOUNDING BOX PARAMETER
        self.pos_x_edit.editingFinished.connect(lambda: self.update_bbox_parameter("pos_x"))
        self.pos_y_edit.editingFinished.connect(lambda: self.update_bbox_parameter("pos_y"))
        self.pos_z_edit.editingFinished.connect(lambda: self.update_bbox_parameter("pos_z"))

        self.length_edit.editingFinished.connect(lambda: self.update_bbox_parameter("length"))
        self.width_edit.editingFinished.connect(lambda: self.update_bbox_parameter("width"))
        self.height_edit.editingFinished.connect(lambda: self.update_bbox_parameter("height"))

        self.rot_x_edit.editingFinished.connect(lambda: self.update_bbox_parameter("rot_x"))
        self.rot_y_edit.editingFinished.connect(lambda: self.update_bbox_parameter("rot_y"))
        self.rot_z_edit.editingFinished.connect(lambda: self.update_bbox_parameter("rot_z"))

        # MENU BAR
        self.action_zrotation.toggled.connect(self.controller.bbox_controller.set_rotation_mode)
        self.action_deletelabels.triggered.connect(self.controller.bbox_controller.reset)
        self.action_showfloor.toggled.connect(self.set_floor_visibility)
        self.action_showorientation.toggled.connect(self.set_orientation_visibility)
        self.action_alignpcd.toggled.connect(self.controller.align_mode.change_activation)

    # Collect, filter and forward events to viewer
    def eventFilter(self, event_object, event):
        # Keyboard Events
        if (event.type() == QEvent.KeyPress) and not self.line_edited_activated():
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
        elif event.type() == QEvent.MouseButtonDblClick and (event_object == self.glWidget):
            self.controller.mouse_double_clicked(event)
            return True
        elif (event.type() == QEvent.MouseButtonPress) and (event_object == self.glWidget):
            self.controller.mouse_clicked(event)
            self.update_bbox_stats(self.controller.bbox_controller.get_active_bbox())
        elif (event.type() == QEvent.MouseButtonPress) and (event_object != self.curr_class_edit):
            self.curr_class_edit.clearFocus()
            self.update_bbox_stats(self.controller.bbox_controller.get_active_bbox())
        return False

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        print("Closing window after saving ...")
        self.controller.save()
        self.timer.stop()
        a0.accept()

    # VISUALIZATION METHODS

    def set_floor_visibility(self, state: bool) -> None:
        self.glWidget.draw_floor = state

    def set_orientation_visibility(self, state: bool) -> None:
        self.glWidget.draw_orientation = state

    def set_pcd_label(self, pcd_name: str) -> None:
        self.label_curr_pcd.setText("Current: <em>%s</em>" % pcd_name)

    def init_progress(self, min_value, max_value):
        self.progressbar_pcd.setMinimum(min_value)
        self.progressbar_pcd.setMaximum(max_value)

    def update_progress(self, value):
        self.progressbar_pcd.setValue(value)

    def update_curr_class_edit(self, force: str = None):
        if force is not None:
            self.curr_class_edit.setText(force)
        else:
            self.curr_class_edit.setText(self.controller.bbox_controller.get_active_bbox().get_classname())

    def update_bbox_stats(self, bbox):
        if bbox and not self.line_edited_activated():
            self.pos_x_edit.setText(str(round(bbox.get_center()[0], GUI.VIEWING_PRECISION)))
            self.pos_y_edit.setText(str(round(bbox.get_center()[1], GUI.VIEWING_PRECISION)))
            self.pos_z_edit.setText(str(round(bbox.get_center()[2], GUI.VIEWING_PRECISION)))

            self.length_edit.setText(str(round(bbox.get_dimensions()[0], GUI.VIEWING_PRECISION)))
            self.width_edit.setText(str(round(bbox.get_dimensions()[1], GUI.VIEWING_PRECISION)))
            self.height_edit.setText(str(round(bbox.get_dimensions()[2], GUI.VIEWING_PRECISION)))

            self.rot_x_edit.setText(str(round(bbox.get_x_rotation(), 1)))
            self.rot_y_edit.setText(str(round(bbox.get_y_rotation(), 1)))
            self.rot_z_edit.setText(str(round(bbox.get_z_rotation(), 1)))

            self.volume_label.setText(str(round(bbox.get_volume(), GUI.VIEWING_PRECISION)))

    def update_bbox_parameter(self, parameter: str):
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
            return True

        if parameter == "length":
            str_value = self.length_edit.text()
        if parameter == "width":
            str_value = self.width_edit.text()
        if parameter == "height":
            str_value = self.height_edit.text()
        if str_value and string_is_float(str_value, recect_negative=True):
            self.controller.bbox_controller.update_dimension(parameter, float(str_value))
            return True

        if parameter == "rot_x":
            str_value = self.rot_x_edit.text()
        if parameter == "rot_y":
            str_value = self.rot_y_edit.text()
        if parameter == "rot_z":
            str_value = self.rot_z_edit.text()
        if str_value and string_is_float(str_value):
            self.controller.bbox_controller.update_rotation(parameter, float(str_value))
            return True

    def save_new_length(self):
        new_length = self.length_edit.text()
        self.controller.bbox_controller.get_active_bbox().length = float(new_length)
        print(f"New length for bounding box submitted → {new_length}.")

    # Enables, disables the draw mode
    def activate_draw_modes(self, state: bool):
        self.button_activate_picking.setEnabled(state)
        self.button_activate_drag.setEnabled(state)
        self.button_activate_spanning.setEnabled(state)

    def update_status(self, message: str, mode: str = None):
        self.tmp_status.setText(message)
        if mode:
            self.update_mode_status(mode)

    def line_edited_activated(self) -> bool:
        for line_edit in self.all_line_edits:
            if line_edit.hasFocus():
                return True
        return False

    def update_mode_status(self, mode: str):
        self.action_alignpcd.setEnabled(True)
        if mode == "drawing":
            text = "Drawing Mode"
            self.action_alignpcd.setEnabled(False)
        elif mode == "correction":
            text = "Correction Mode"
        elif mode == "alignment":
            text = "Alignment Mode"
        else:
            text = "Navigation Mode"
        self.mode_status.setText(text)
