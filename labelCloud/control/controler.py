from typing import TYPE_CHECKING, Union

from PyQt5 import QtGui, QtCore

from control.alignmode import AlignMode
from control.drawing_manager import DrawingManager
from control.pcd_manager import PointCloudManger
from model.bbox import BBox
from control.bbox_controler import BoundingBoxControler

if TYPE_CHECKING:
    from view.gui import GUI
from utils import oglhelper


class Controler:

    # PREPARATION
    def __init__(self):
        self.view: Union['GUI', None] = None
        self.pcd_controler = PointCloudManger()
        self.bbox_controler = BoundingBoxControler()

        # Drawing states
        self.drawing_mode = DrawingManager(self.bbox_controler)
        self.align_mode = AlignMode(self.pcd_controler)

        # Control states
        self.curr_cursor_pos = None  # updated by mouse movement
        self.last_cursor_pos = None  # updated by mouse click
        self.ctrl_pressed = False
        self.scroll_mode = False

        # Correction states
        self.side_mode = False
        self.selected_side = None

    def set_view(self, view: 'GUI'):
        self.view = view
        self.bbox_controler.set_view(self.view)
        self.pcd_controler.set_view(self.view)
        self.drawing_mode.set_view(self.view)
        self.align_mode.set_view(self.view)
        self.view.glWidget.set_bbox_controler(self.bbox_controler)
        self.bbox_controler.pcdc = self.pcd_controler
        self.bbox_controler.set_bboxes(self.pcd_controler.get_labels_from_file())  # Load labels for first pcd

    # EVENT CYCLE
    def loop_gui(self):
        # OpenGL part
        self.set_crosshair()
        self.set_selected_side()
        self.view.glWidget.updateGL()

    # POINT CLOUD METHODS
    def next_pcd(self):
        self.save()
        if self.pcd_controler.pcds_left():
            self.pcd_controler.get_next_pcd()
            self.reset()
            self.bbox_controler.set_bboxes(self.pcd_controler.get_labels_from_file())
        else:
            self.view.update_progress(self.pcd_controler.no_of_pcds)
            self.view.button_next_pcd.setEnabled(False)

    def prev_pcd(self):
        self.save()
        if self.pcd_controler.current_id > 0:
            self.pcd_controler.get_prev_pcd()
            self.reset()
            self.bbox_controler.set_bboxes(self.pcd_controler.get_labels_from_file())

    # CONTROL METHODS
    # Saves all labels
    def save(self):
        self.pcd_controler.save_labels_into_file(self.bbox_controler.get_bboxes())

    # Resets the controls and bboxes from the current screen
    def reset(self):
        self.bbox_controler.reset()
        self.drawing_mode.reset()
        self.align_mode.reset()

    # CORRECTION METHODS
    # Draw Objects in Point Cloud Viewer
    def set_crosshair(self):
        if self.curr_cursor_pos:
            self.view.glWidget.crosshair_col = [0, 1, 0]
            self.view.glWidget.crosshair_pos = (self.curr_cursor_pos.x(), self.curr_cursor_pos.y())

    def set_selected_side(self):
        if (not self.side_mode) and self.curr_cursor_pos and self.bbox_controler.has_active_bbox() \
                and (not self.scroll_mode):
            self.selected_side = oglhelper.get_intersected_sides(self.curr_cursor_pos.x(), self.curr_cursor_pos.y(),
                                                                 self.bbox_controler.get_active_bbox().get_vertices(),
                                                                 self.view.glWidget.modelview,
                                                                 self.view.glWidget.projection)
        if self.selected_side and (not self.ctrl_pressed) and self.bbox_controler.has_active_bbox():
            self.view.glWidget.crosshair_col = [1, 0, 0]
            side_vertices = self.bbox_controler.get_active_bbox().get_vertices()
            self.view.glWidget.selected_side_vertices = side_vertices[BBox.BBOX_SIDES[self.selected_side]]
        else:
            self.view.glWidget.selected_side_vertices = []

    # EVENT PROCESSING
    def mouse_clicked(self, a0: QtGui.QMouseEvent):
        self.last_cursor_pos = a0.pos()

        if self.drawing_mode.is_active() and (a0.buttons() & QtCore.Qt.LeftButton) and (not self.ctrl_pressed):
            self.drawing_mode.register_point(a0.x(), a0.y(), correction=True)

        elif self.align_mode.is_active() and (not self.ctrl_pressed):
            self.align_mode.register_point(self.view.glWidget.get_world_coords(a0.x(), a0.y(), correction=False))

        elif self.selected_side:
            self.side_mode = True

    def mouse_double_clicked(self, a0: QtGui.QMouseEvent):
        self.bbox_controler.select_bbox_by_ray(a0.x(), a0.y())

    def mouse_move_event(self, a0: QtGui.QMouseEvent):
        # Methods that use relative cursor movement
        self.curr_cursor_pos = a0.pos()

        # Methods that use absolute cursor position
        if self.drawing_mode.is_active() and (not self.ctrl_pressed):
            self.drawing_mode.register_point(a0.x(), a0.y(), correction=True, is_temporary=True)

        elif self.align_mode.is_active() and (not self.ctrl_pressed):
            self.align_mode.register_tmp_point(self.view.glWidget.get_world_coords(a0.x(), a0.y(), correction=False))

        if self.last_cursor_pos:
            dx = (self.last_cursor_pos.x() - a0.x()) / 5  # Calculate relative movement from last click position
            dy = (self.last_cursor_pos.y() - a0.y()) / 5

            if self.ctrl_pressed and (not self.drawing_mode.is_active()) and (not self.align_mode.is_active()):
                if a0.buttons() & QtCore.Qt.LeftButton:  # bbox rotation
                    # self.bbox_controler.rotate_around_x(-dy)
                    # self.bbox_controler.rotate_around_y(-dx)
                    self.bbox_controler.rotate_with_mouse(-dx, -dy)
                elif a0.buttons() & QtCore.Qt.RightButton:  # bbox translation
                    # self.bbox_controler.translate_along_x(-dx / 30)
                    # self.bbox_controler.translate_along_y(dy / 30)
                    new_center = self.view.glWidget.get_world_coords(a0.x(), a0.y(), correction=True)
                    self.bbox_controler.set_center(*new_center)  # absolute positioning
            else:
                if a0.buttons() & QtCore.Qt.LeftButton:  # pcd rotation
                    self.pcd_controler.rotate_around_x(dy)
                    self.pcd_controler.rotate_around_z(dx)
                elif a0.buttons() & QtCore.Qt.RightButton:  # pcd translation
                    self.pcd_controler.translate_along_x(dx)
                    self.pcd_controler.translate_along_y(dy)

            if dx > 0.1 or dy > 0.1:  # Reset scroll locks if significant cursor movements
                if self.side_mode:
                    self.side_mode = False
                else:
                    self.scroll_mode = False
        self.last_cursor_pos = a0.pos()

    def mouse_scroll_event(self, a0: QtGui.QWheelEvent):
        if self.selected_side:
            self.side_mode = True

        if self.drawing_mode.is_active() and (not self.ctrl_pressed):
            self.drawing_mode.drawing_strategy.register_scrolling(a0.angleDelta().y())
        elif self.side_mode and self.bbox_controler.has_active_bbox():
            self.bbox_controler.get_active_bbox().change_side(self.selected_side,
                                                              -a0.angleDelta().y() / 4000)  # ToDo implement method
        else:
            self.pcd_controler.zoom_into(a0.angleDelta().y())
            self.scroll_mode = True

    def key_press_event(self, a0: QtGui.QKeyEvent):
        # Reset position to intial value
        if a0.key() == QtCore.Qt.Key_Control:
            self.ctrl_pressed = True

        # Reset point cloud pose to intial rotation and translation
        elif (a0.key() == QtCore.Qt.Key_R) or (a0.key() == QtCore.Qt.Key_Home):
            self.pcd_controler.reset_transformations()
            print("Reseted position to default.")

        elif a0.key() == QtCore.Qt.Key_Delete:  # Delete active bbox
            self.bbox_controler.delete_current_bbox()

        # Save labels to file
        elif (a0.key() == QtCore.Qt.Key_S) and self.ctrl_pressed:
            self.save()

        elif a0.key() == QtCore.Qt.Key_Escape:
            if self.drawing_mode.is_active():
                self.drawing_mode.reset()
                print("Resetted drawn points!")
            elif self.align_mode.is_active():
                self.align_mode.reset()
                print("Resetted selected points!")

        # BBOX MANIPULATION
        elif (a0.key() == QtCore.Qt.Key_Y) or (a0.key() == QtCore.Qt.Key_Comma):  # z rotate counterclockwise
            self.bbox_controler.rotate_around_z()
        elif (a0.key() == QtCore.Qt.Key_X) or (a0.key() == QtCore.Qt.Key_Period):  # z rotate clockwise
            self.bbox_controler.rotate_around_z(clockwise=True)
        elif a0.key() == QtCore.Qt.Key_C:  # y rotate counterclockwise
            self.bbox_controler.rotate_around_y()
        elif a0.key() == QtCore.Qt.Key_V:  # y rotate clockwise
            self.bbox_controler.rotate_around_y(clockwise=True)
        elif a0.key() == QtCore.Qt.Key_B:  # x rotate counterclockwise
            self.bbox_controler.rotate_around_x()
        elif a0.key() == QtCore.Qt.Key_N:  # x rotate clockwise
            self.bbox_controler.rotate_around_x(clockwise=True)
        elif (a0.key() == QtCore.Qt.Key_W) or (a0.key() == QtCore.Qt.Key_Up):  # move backward
            self.bbox_controler.translate_along_y()
        elif (a0.key() == QtCore.Qt.Key_S) or (a0.key() == QtCore.Qt.Key_Down):  # move forward
            self.bbox_controler.translate_along_y(forward=True)
        elif (a0.key() == QtCore.Qt.Key_A) or (a0.key() == QtCore.Qt.Key_Left):  # move left
            self.bbox_controler.translate_along_x(left=True)
        elif (a0.key() == QtCore.Qt.Key_D) or (a0.key() == QtCore.Qt.Key_Right):  # move right
            self.bbox_controler.translate_along_x()
        elif (a0.key() == QtCore.Qt.Key_Q) or (a0.key() == QtCore.Qt.Key_PageUp):  # move up
            self.bbox_controler.translate_along_z()
        elif (a0.key() == QtCore.Qt.Key_E) or (a0.key() == QtCore.Qt.Key_PageDown):  # move down
            self.bbox_controler.translate_along_z(down=True)

    def key_release_event(self, a0: QtGui.QKeyEvent):
        if a0.key() == QtCore.Qt.Key_Control:
            self.ctrl_pressed = False
