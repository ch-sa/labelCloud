from typing import TYPE_CHECKING, Dict

import numpy as np
from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtCore import QEvent, Qt

if TYPE_CHECKING:
    from modules.control.controler import Controler
from modules.view.viewer import GLWidget


class GUI(QtWidgets.QMainWindow):

    def __init__(self, control: 'Controler'):
        super(GUI, self).__init__()
        uic.loadUi("ressources/interface.ui", self)
        self.resize(1500, 900)
        self.setWindowTitle('labelCloud')

        # MENU BAR
        # File
        self.action_setpcdfolder = self.findChild(QtWidgets.QAction, "action_setpcdfolder").setEnabled(False)
        self.action_setlabelfolder = self.findChild(QtWidgets.QAction, "action_setlabelfolder").setEnabled(False)
        self.action_loadsinglepcd = self.findChild(QtWidgets.QAction, "action_loadsinglepcd").setEnabled(False)

        # Labels
        self.action_zrotation = self.findChild(QtWidgets.QAction, "action_zrotationonly")
        self.action_deletelabels = self.findChild(QtWidgets.QAction, "action_deletealllabels")
        self.action_setclasslist = self.findChild(QtWidgets.QAction, "action_setclasslist").setEnabled(False)
        self.action_setstddimensions = self.findChild(QtWidgets.QAction, "action_setstddimensions").setEnabled(False)
        self.action_setstdtransformations = self.findChild(QtWidgets.QAction,
                                                           "action_setstdtransformations").setEnabled(False)

        # Settings
        self.action_pointsize = self.findChild(QtWidgets.QAction, "action_pointsize").setEnabled(False)
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
        self.curr_bbox_stats = self.findChild(QtWidgets.QLabel, "current_bbox_stats")
        self.button_deselect_label = self.findChild(QtWidgets.QPushButton, "button_label_deselect")
        self.button_delete_label = self.findChild(QtWidgets.QPushButton, "button_label_delete")

        # Non-GUI variables
        self.controler = control
        self.controler.set_view(self)
        self.last_was_scroll = False  # ToDo: Necessary?

        # Connect all events to functions
        self.connect_events()

        # Start event cycle
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(20)  # period, in milliseconds
        self.timer.timeout.connect(self.controler.loop_gui)
        self.timer.start()

    # Event connectors
    def connect_events(self):
        # POINTCLOUD CONTROL
        self.button_next_pcd.clicked.connect(self.controler.next_pcd)
        self.button_prev_pcd.clicked.connect(self.controler.prev_pcd)

        # BBOX CONTROL
        self.button_up.pressed.connect(lambda: self.controler.bbox_controler.translate_along_z())
        self.button_down.pressed.connect(lambda: self.controler.bbox_controler.translate_along_z(down=True))
        # self.button_left.pressed.connect(lambda: self.controler.bbox_controler.translate_along_x(left=True))
        self.button_left.pressed.connect(self.translate)
        self.button_right.pressed.connect(self.controler.bbox_controler.translate_along_x)
        self.button_forward.pressed.connect(lambda: self.controler.bbox_controler.translate_along_y(forward=True))
        self.button_backward.pressed.connect(lambda: self.controler.bbox_controler.translate_along_y())

        self.dial_zrotation.valueChanged.connect(lambda x: self.controler.bbox_controler.rotate_around_z(x,
                                                                                                         absolute=True))
        self.button_decr_dim.clicked.connect(lambda: self.controler.bbox_controler.scale(decrease=True))
        self.button_incr_dim.clicked.connect(lambda: self.controler.bbox_controler.scale())

        # LABELING CONTROL
        self.curr_class_edit.textChanged.connect(self.controler.bbox_controler.set_classname)
        self.button_deselect_label.clicked.connect(self.controler.bbox_controler.deselect_bbox)
        self.button_delete_label.clicked.connect(self.controler.bbox_controler.delete_current_bbox)
        self.label_list.currentRowChanged.connect(self.controler.bbox_controler.set_active_bbox)

        # LABEL CONTROL
        # Activate drawing modes: picking, spanning, ?
        self.button_activate_picking.clicked.connect(lambda: self.controler.drawing_mode.
                                                     set_drawing_strategy("PickingStrategy"))
        self.button_activate_spanning.clicked.connect(lambda: self.controler.drawing_mode.
                                                      set_drawing_strategy("SpanStrategy"))
        self.button_activate_drag.clicked.connect(lambda: self.controler.drawing_mode.
                                                  set_drawing_strategy("RectangleStrategy"))

        # Save current point cloud labels to json
        self.button_save_labels.clicked.connect(self.controler.save)

        # MENU BAR
        self.action_zrotation.toggled.connect(self.controler.bbox_controler.set_rotation_mode)
        self.action_deletelabels.triggered.connect(self.controler.bbox_controler.reset)
        self.action_showfloor.toggled.connect(self.set_floor_visibility)
        self.action_showorientation.toggled.connect(self.set_orientation_visibility)
        self.action_alignpcd.toggled.connect(self.controler.align_mode.change_activation)

    def translate(self):
        self.controler.bbox_controler.translate_along_x(left=True)

    # Collect, filter and forward events to viewer
    def eventFilter(self, event_object, event):
        # Keyboard Events
        if (event.type() == QEvent.KeyPress) and (not self.curr_class_edit.hasFocus()):
            self.controler.key_press_event(event)
            self.update_bbox_stats(self.controler.bbox_controler.get_active_bbox())
            return True
        elif event.type() == QEvent.KeyRelease:
            self.controler.key_release_event(event)
        # Mouse Events
        elif (event.type() == QEvent.MouseMove) and (event_object == self.glWidget):
            self.controler.mouse_move_event(event)
            self.update_bbox_stats(self.controler.bbox_controler.get_active_bbox())
            self.last_was_scroll = False
        elif (event.type() == QEvent.Wheel) and (event_object == self.glWidget):
            self.controler.mouse_scroll_event(event)
            self.update_bbox_stats(self.controler.bbox_controler.get_active_bbox())
        elif event.type() == QEvent.MouseButtonDblClick and (event_object == self.glWidget):
            self.controler.mouse_double_clicked(event)
            return True
        elif (event.type() == QEvent.MouseButtonPress) and (event_object == self.glWidget):
            self.controler.mouse_clicked(event)
            self.update_bbox_stats(self.controler.bbox_controler.get_active_bbox())
        elif (event.type() == QEvent.MouseButtonPress) and (event_object != self.curr_class_edit):
            self.curr_class_edit.clearFocus()
            self.update_bbox_stats(self.controler.bbox_controler.get_active_bbox())

        return False

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        print("Closing window after saving ...")
        self.controler.save()
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
            self.curr_class_edit.setText(self.controler.bbox_controler.get_active_bbox().get_classname())

    def update_bbox_stats(self, bbox):
        if bbox:
            tmp_data = {"Center": np.round(bbox.get_center(), 2), "Dimension": np.round(bbox.get_dimensions(), 2),
                        "Rotation": np.round(bbox.get_rotations(), 1), "Volume": [bbox.get_volume()]}
            self.curr_bbox_stats.setText(create_html_table(tmp_data))
        else:
            self.curr_class_edit.clear()
            self.curr_bbox_stats.setText("No active bbox.")

    # Enables, disables the draw mode
    def activate_draw_modes(self, state: bool):
        self.button_activate_picking.setEnabled(state)
        self.button_activate_drag.setEnabled(state)
        self.button_activate_spanning.setEnabled(state)

    def update_status(self, message: str, mode: str = None):
        self.tmp_status.setText(message)
        if mode:
            self.update_mode_status(mode)

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


def create_html_table(data: Dict):
    style = """<style>     
            th {
                text-align: left;
                text-transform: uppercase;
                font-weight: normal;
                background-color: #EFEFEF;
            }
            td {
                text-align: right;
            }</style>"""

    table = "<table width='100%'>"
    for heading, cells in data.items():
        table += "<tr> <th>%s</th>" % heading
        for cell in cells:
            if heading == "Rotation":
                table += "<td style='width: 100%'>{:4.1f}</td>".format(cell)
            else:
                table += "<td style='width: 100%'>{:4.2f}</td>".format(cell)
        table += "</tr>"
    table += "</table>"
    return style + table
