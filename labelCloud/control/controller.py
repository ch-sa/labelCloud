import logging
from typing import Optional

import numpy as np
import numpy.random as random
from PyQt5 import QtGui
from PyQt5.QtCore import QPoint
from PyQt5.QtCore import Qt as Keys
from PyQt5.QtCore import Qt, QPoint
from ..definitions import BBOX_SIDES, Colors, Context, LabelingMode
from ..io.labels.config import LabelConfig
from ..utils import oglhelper
from ..view.gui import GUI
from .alignmode import AlignMode
from .bbox_controller import BoundingBoxController
from .config_manager import config
from .drawing_manager import DrawingManager
from .pcd_manager import PointCloudManger


class Controller:
    MOVEMENT_THRESHOLD = 0.1

    def __init__(self) -> None:
        """Initializes all controllers and managers."""
        self.view: "GUI"
        self.pcd_manager = PointCloudManger()
        self.bbox_controller = BoundingBoxController(self)

        # Drawing states
        self.drawing_mode = DrawingManager(self.bbox_controller)
        self.align_mode = AlignMode(self.pcd_manager)

        # Control states
        self.curr_cursor_pos: Optional[QPoint] = None  # updated by mouse movement
        self.last_cursor_pos: Optional[QPoint] = None  # updated by mouse click
        self.ctrl_pressed = False
        self.alt_pressed = False
        self.scroll_mode = False  # to enable the side-pulling

        # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
        # Added: for group selection, copy, paste, State for new features
        self.shift_pressed = False
        self.is_marquee_selecting = False
        self.marquee_start_pos = None
        self.bbox_clipboard = [] # To store copied bounding boxes

        # Correction states
        self.side_mode = False
        self.selected_side: Optional[str] = None

        # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
        # Added: for camera state / view change
        self.camera_distance = 10.0  # Initial zoom level
        self.camera_rotation = [0.0, 0.0]  # X and Z rotations
        self.camera_translation = [0.0, 0.0, 0.0]

        # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
        # Added: for tracking last saved time camera state / view change
        self._last_save_time = None  # Track last save time

    def startup(self, view: "GUI") -> None:
        """Sets the view in all controllers and dependent modules; Loads labels from file."""
        self.view = view
        self.bbox_controller.set_view(self.view)
        self.pcd_manager.set_view(self.view)
        self.drawing_mode.set_view(self.view)
        self.align_mode.set_view(self.view)
        self.view.gl_widget.set_bbox_controller(self.bbox_controller)

        print("About to set controller in GLWidget")
        self.view.gl_widget.set_controller(self)
        print("Controller set completed")

        self.bbox_controller.pcd_manager = self.pcd_manager

        # Read labels from folders
        self.pcd_manager.read_pointcloud_folder()
        self.next_pcd(save=False)

    def loop_gui(self) -> None:
        """Function collection called during each event loop iteration."""
        self.set_crosshair()
        self.set_selected_side()
        self.view.gl_widget.updateGL()

    def next_pcd(self, save: bool = True) -> None:
        if save:
            self.save()
        if self.pcd_manager.pcds_left():
            previous_bboxes = self.bbox_controller.bboxes
            self.pcd_manager.get_next_pcd()
            self.reset()

            # Clear selection when changing frames
            self.bbox_controller.deselect_all_bboxes()  # Add this line

            # Check if propagation is enabled
            should_propagate = config.getboolean("LABEL", "propagate_labels")
            
            # Propagate labels if enabled (regardless of next frame's labels)
            if should_propagate:
                self.bbox_controller.set_bboxes(previous_bboxes)
                # Uncheck the box in the UI and update config
                self.view.act_propagate_labels.setChecked(False)
                config.set("LABEL", "propagate_labels", "False")
            else:
                # Load existing labels if no propagation
                self.bbox_controller.set_bboxes(self.pcd_manager.get_labels_from_file())

            self.bbox_controller.set_active_bbox(0)
        else:
            self.view.update_progress(len(self.pcd_manager.pcds))
            self.view.button_next_pcd.setEnabled(False)

    def prev_pcd(self) -> None:
        self.save()
        if self.pcd_manager.current_id > 0:
            self.pcd_manager.get_prev_pcd()
            self.reset()
            # Clear selection when changing frames
            self.bbox_controller.deselect_all_bboxes()  # Add this line
            self.bbox_controller.set_bboxes(self.pcd_manager.get_labels_from_file())
            self.bbox_controller.set_active_bbox(0)

    def custom_pcd(self, custom: int) -> None:
        self.save()
        self.pcd_manager.get_custom_pcd(custom)
        self.reset()
        # Clear selection when changing frames
        self.bbox_controller.deselect_all_bboxes()  # Add this line
        self.bbox_controller.set_bboxes(self.pcd_manager.get_labels_from_file())

    def save(self, force_overwrite=False, backup=True) -> None:
        """Save and update tracking"""
        self.pcd_manager.save_labels_into_file(
            self.bbox_controller.bboxes,
            force_overwrite=force_overwrite,
            backup=backup
        )
        # Always update saved state when saving (whether backup or overwrite)
        self.bbox_controller.mark_as_saved()  
        self._unsaved_changes = False  # Explicitly mark as saved
        if LabelConfig().type == LabelingMode.SEMANTIC_SEGMENTATION:
            assert self.pcd_manager.pointcloud is not None
            self.pcd_manager.pointcloud.save_segmentation_labels()
                
    def has_unsaved_changes(self) -> bool:
        """Check both boxes and point cloud changes"""
        return self.bbox_controller.has_unsaved_changes()

    def reset(self) -> None:
        """Resets the controllers and bounding boxes from the current screen."""
        self.bbox_controller.reset()
        self.drawing_mode.reset()
        self.align_mode.reset()
        # Also clear selection
        self.bbox_controller.deselect_all_bboxes()  # Add this line

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

    def mouse_double_clicked(self, a0: QtGui.QMouseEvent) -> None:
        """Handle double click - select single bbox or deselect all"""
        # Try to select bbox under cursor first
        intersected_bbox_id = oglhelper.get_intersected_bboxes(
            a0.x(),
            a0.y(),
            self.bbox_controller.bboxes,
            self.view.gl_widget.modelview,
            self.view.gl_widget.projection,
        )
        
        if intersected_bbox_id is not None:
            # Double-clicked on a bbox - select only this one (clear others)
            print(f"Double-clicked on bbox {intersected_bbox_id} - clearing other selections")
            self.bbox_controller.deselect_all_bboxes()
            self.bbox_controller.set_active_bbox(intersected_bbox_id)
            self.bbox_controller.selected_bbox_ids.add(intersected_bbox_id)
        else:
            # Double-clicked on empty space - deselect everything
            print("Double-clicked on empty space - deselecting all boxes")
            self.bbox_controller.deselect_all_bboxes()
        
        a0.accept()  # Prevent further processing

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Added: for group selection, copy, and paste
    def mouse_clicked(self, a0: QtGui.QMouseEvent) -> None:
        """Handle mouse clicks - only consume events we actually handle"""
        self.last_cursor_pos = a0.pos()
        
        # Check for specific marquee selection combination
        left_click = bool(a0.buttons() & Qt.LeftButton)
        
        # ONLY handle Shift + Left click for marquee selection
        if self.shift_pressed and left_click:
            self.is_marquee_selecting = True
            self.marquee_start_pos = a0.pos()
            self.view.gl_widget.start_marquee(self.marquee_start_pos)
            a0.accept()  # Consume ONLY this specific combination
            return

        # Existing functionality - unchanged
        if (
            self.drawing_mode.is_active()
            and (a0.buttons() & Keys.LeftButton)
            and (not self.ctrl_pressed)
        ):
            self.drawing_mode.register_point(a0.x(), a0.y(), correction=True)
            return  # Skip other handling when in drawing mode

        elif self.align_mode.is_active and (not self.ctrl_pressed):
            self.align_mode.register_point(
                self.view.gl_widget.get_world_coords(a0.x(), a0.y(), correction=False))
            return  # Skip other handling when in alignment mode

        elif self.selected_side:
            self.side_mode = True
            return  # Skip other handling when correcting sides
        
            
    def mouse_move_event(self, a0: QtGui.QMouseEvent) -> None:
        """Handle mouse movement - including marquee updates"""
        self.curr_cursor_pos = a0.pos()
        
        # Marquee selection update
        if self.is_marquee_selecting:
            if self.shift_pressed:
                self.view.gl_widget.update_marquee(a0.pos())
            else:
                self.is_marquee_selecting = False
                self.view.gl_widget.end_marquee()
            a0.accept()

        # In your mouse move event handler:
        try:
            wx, wy, wz = self.view.gl_widget.get_world_coords(a0.x(), a0.y(), correction=True)
            self.pcd_manager.view.status_manager.set_coordinates(wx, wy, wz)
            
            # Send camera rotation data
            rot_x = self.view.gl_widget.camera_rot_x
            rot_y = self.view.gl_widget.camera_rot_y
            self.pcd_manager.view.status_manager.set_camera_rotation(rot_x, rot_y)
        except Exception as e:
            if self.view.coord_label:
                self.view.coord_label.setText(f"Cursor: (Invalid)")
            if hasattr(self.view, 'rotation_label'):
                self.view.rotation_label.setText(f"Camera: (Invalid)")

        # Methods that use absolute cursor position
        if self.drawing_mode.is_active() and (not self.ctrl_pressed):
            self.drawing_mode.register_point(
                a0.x(), a0.y(), correction=True, is_temporary=True
            )
        elif self.align_mode.is_active and (not self.ctrl_pressed):
            self.align_mode.register_tmp_point(
                self.view.gl_widget.get_world_coords(a0.x(), a0.y(), correction=False)
            )

    def mouse_released(self, a0: QtGui.QMouseEvent) -> None:
        """Handle mouse release - including marquee finalization"""
        # Marquee selection finalization
        if self.is_marquee_selecting and a0.button() == Keys.LeftButton:
            self.is_marquee_selecting = False
            marquee_end_pos = a0.pos()
            self.view.gl_widget.end_marquee()
            
            # Perform the actual box selection
            self.bbox_controller.select_bboxes_in_rectangle(
                self.marquee_start_pos, marquee_end_pos
            )
            a0.accept()
        elif self.is_marquee_selecting:
            self.is_marquee_selecting = False
            self.view.gl_widget.end_marquee()
            a0.accept()


    # In controller.py
    def mouse_scroll_event(self, a0: QtGui.QWheelEvent) -> None:
        """Handle scroll events with proper filtering"""
        # Only handle special modes in controller
        if self.selected_side or self.drawing_mode.is_active():
            a0.accept()  # Consume the event - don't propagate
        else:
            # Don't accept - let the event propagate to GLWidget's normal handling
            a0.ignore()

    def key_press_event(self, a0: QtGui.QKeyEvent) -> None:
        """Triggers actions when the user presses a key."""

        if a0.key() == Keys.Key_Control:
            self.ctrl_pressed = True
            self.view.status_manager.set_message(
                "Ctrl pressed.",
                context=Context.CONTROL_PRESSED,
            )

        if a0.key() == Keys.Key_Shift:  # Add this
            self.shift_pressed = True
            self.view.status_manager.set_message(
                "Shift pressed.",
                context=Context.SHIFT_PRESSED,
            )

        if a0.key() == Keys.Key_Alt:
            self.alt_pressed = True
            
        # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
        # Added: for copy, and paste
        if self.ctrl_pressed and a0.key() == Keys.Key_C:
            self.bbox_clipboard = self.bbox_controller.copy_selected_bboxes()
            logging.info(f"Copied {len(self.bbox_clipboard)} bounding boxes to clipboard.")
            return

        if self.ctrl_pressed and a0.key() == Keys.Key_V:
            if not self.bbox_clipboard:
                logging.warning("Clipboard is empty. Nothing to paste.")
                return
            self.bbox_controller.paste_bboxes_from_clipboard(self.bbox_clipboard)
            logging.info(f"Pasted {len(self.bbox_clipboard)} bounding boxes.")
            return
            
        if a0.key() in [Keys.Key_P, Keys.Key_Home]:
            self.pcd_manager.reset_transformations()
            logging.info("Reseted position to default.")

        elif a0.key() == Keys.Key_Delete:
            self.bbox_controller.delete_selected_bboxes() # Changed to handle multiple

        elif a0.key() == Keys.Key_S and self.ctrl_pressed:
            self.save(force_overwrite=True)  

        elif a0.key() == Keys.Key_Escape:
            if self.drawing_mode.is_active():
                self.drawing_mode.reset()
                logging.info("Resetted drawn points!")
            elif self.align_mode.is_active:
                self.align_mode.reset()
                logging.info("Resetted selected points!")
            else:
                self.bbox_controller.deselect_all_bboxes() # New function to clear selection

        # BBOX MANIPULATION (Now calls "group" methods)
        elif a0.key() == Keys.Key_Z:
            self.bbox_controller.rotate_group_around_z(fine=not self.ctrl_pressed)
        elif a0.key() == Keys.Key_X:
            self.bbox_controller.rotate_group_around_z(fine=not self.ctrl_pressed, clockwise=True)

        elif a0.key() == Keys.Key_D:
            self.bbox_controller.translate_group_along_y(forward=True)
        elif a0.key() == Keys.Key_A:
            self.bbox_controller.translate_group_along_y()
        elif a0.key() == Keys.Key_W:
            self.bbox_controller.translate_group_along_x()
        elif a0.key() == Keys.Key_S:
            self.bbox_controller.translate_group_along_x(left=True)

        elif a0.key() == Keys.Key_Q:
            self.bbox_controller.translate_group_along_z()
        elif a0.key() == Keys.Key_E:
            self.bbox_controller.translate_group_along_z(down=True)

        elif a0.key() == Keys.Key_I:
            self.bbox_controller.scale_group_along_length()
        elif a0.key() == Keys.Key_O:
            self.bbox_controller.scale_group_along_length(decrease=True)
        elif a0.key() == Keys.Key_K:
            self.bbox_controller.scale_group_along_width()
        elif a0.key() == Keys.Key_L:
            self.bbox_controller.scale_group_along_width(decrease=True)
        elif a0.key() == Keys.Key_Comma:
            self.bbox_controller.scale_group_along_height()
        elif a0.key() == Keys.Key_Period:
            self.bbox_controller.scale_group_along_height(decrease=True)

        elif a0.key() in [Keys.Key_R, Keys.Key_Left]:
            self.prev_pcd()
        elif a0.key() in [Keys.Key_F, Keys.Key_Right]:
            self.next_pcd()
        elif a0.key() in [Keys.Key_T, Keys.Key_Up]:
            self.select_relative_bbox(-1)
        elif a0.key() in [Keys.Key_G, Keys.Key_Down]:
            self.select_relative_bbox(1)
        elif a0.key() == Keys.Key_Y:
            self.select_relative_class(-1)
        elif a0.key() == Keys.Key_H:
            self.select_relative_class(1)
        elif a0.key() in list(range(49, 58)):
            self.bbox_controller.set_active_bbox(int(a0.key()) - 49)

        elif a0.key() == Keys.Key_V:
            self.pcd_manager.view.gl_widget.cycle_view_mode()

        elif a0.key() == Keys.Key_U:
            self.bbox_controller.rotate_group_180_degrees() # Changed to handle group

    def key_release_event(self, a0: QtGui.QKeyEvent) -> None:
        """Triggers actions when the user releases a key."""
        if a0.key() == Keys.Key_Control:
            self.ctrl_pressed = False
            self.view.status_manager.clear_message(context=Context.CONTROL_PRESSED)

        if a0.key() == Keys.Key_Shift:  # Add this
            self.shift_pressed = False
            self.view.status_manager.clear_message(context=Context.SHIFT_PRESSED)

            # CANCEL MARQUEE IMMEDIATELY when Shift is released
            if self.is_marquee_selecting:
                print("Shift released - immediately cancelling marquee")
                self.is_marquee_selecting = False
                self.view.gl_widget.end_marquee()

        if a0.key() == Keys.Key_Alt:
            self.alt_pressed = False

    def select_relative_class(self, step: int):
        if step == 0:
            return
        curr_class = self.bbox_controller.get_active_bbox().get_classname()  # type: ignore
        new_class = LabelConfig().get_relative_class(curr_class, step)
        self.bbox_controller.get_active_bbox().set_classname(new_class)  # type: ignore
        self.bbox_controller.update_all()  # updates UI in SelectBox

    def select_relative_bbox(self, step: int):
        if step == 0:
            return
        max_id = len(self.bbox_controller.bboxes) - 1
        curr_id = self.bbox_controller.active_bbox_id
        new_id = curr_id + step
        corner_case_id = 0 if step > 0 else max_id
        new_id = new_id if new_id in range(max_id + 1) else corner_case_id
        self.bbox_controller.set_active_bbox(new_id)


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
