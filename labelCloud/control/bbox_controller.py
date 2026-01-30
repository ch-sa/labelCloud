"""
A class to handle all user manipulations of the bounding boxes and collect all labeling
settings in one place.
Bounding Box Management: adding, selecting updating, deleting bboxes;
Possible Active Bounding Box Manipulations: rotation, translation, scaling
"""

import logging
from functools import wraps
from typing import TYPE_CHECKING, List, Optional

import numpy as np
import math

from ..definitions import Mode
from ..model.bbox import BBox
from ..utils import oglhelper
from .config_manager import config
from .pcd_manager import PointCloudManger
import traceback 

from OpenGL import GL, GLU
import numpy as np
import math
from typing import Dict, List, Tuple, Optional
from PyQt5 import QtGui
from PyQt5.QtCore import QPoint

if TYPE_CHECKING:
    from ..view.gui import GUI
    from .controller import Controller


# DECORATORS
def has_active_bbox_decorator(func):
    """
    Only execute bounding box manipulation if there is an active bounding box.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if args[0].has_active_bbox():
            return func(*args, **kwargs)
        else:
            logging.warning("There is currently no active bounding box to manipulate.")

    return wrapper


def only_zrotation_decorator(func):
    """
    Only execute x- and y-rotation if z_rotation_only mode is not activated.
    """

    def wrapper(*args, **kwargs):
        if not config.getboolean("USER_INTERFACE", "z_rotation_only"):
            return func(*args, **kwargs)
        else:
            logging.warning(
                "Rotations around the x- or y-axis are not supported in this mode."
            )

    return wrapper


class BoundingBoxController(object):
    STD_SCALING = config.getfloat("LABEL", "std_scaling")

    def __init__(self, controller: 'Controller') -> None:
        self.view: GUI
        self.pcd_manager: PointCloudManger
        self.bboxes: List[BBox] = []
        self.active_bbox_id = -1  # -1 means zero bboxes
        self.controller = controller
        self.saved_state = set()  # Track saved boxes
        self.selected_bbox_ids = set() 

    # GETTERS
    def has_active_bbox(self) -> bool:
        return 0 <= self.active_bbox_id < len(self.bboxes)

    def get_active_bbox(self) -> Optional[BBox]:
        if self.has_active_bbox():
            return self.bboxes[self.active_bbox_id]
        else:
            return None
    def mark_as_saved(self):
        """Call this when boxes are saved (Ctrl+S)"""
        self.saved_state = {id(bbox) for bbox in self.bboxes}
        
    def has_unsaved_changes(self) -> bool:
        """Check if any boxes changed since last save"""
        return len({id(bbox) for bbox in self.bboxes} - self.saved_state) > 0

    @has_active_bbox_decorator
    def get_classname(self) -> str:
        return self.get_active_bbox().get_classname()  # type: ignore

    # SETTERS
    def set_view(self, view: "GUI") -> None:
        self.view = view

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Added: make default box car's class, size, and make the car's direction align with the current view's
    def add_bbox(self, bbox: BBox) -> None:
        logging.debug(f"Adding new bbox with dims: {bbox.get_dimensions()}")
        if isinstance(bbox, BBox):
            # Set default class to "car"
            bbox.set_classname("car")
            
            # Set default dimensions for car
            bbox.set_dimensions(
                config.getfloat("LABEL_DEFAULTS", "car_length"),
                config.getfloat("LABEL_DEFAULTS", "car_width"),
                config.getfloat("LABEL_DEFAULTS", "car_height"))
            
            # Get the current camera view yaw angle (z-rotation)
            view_direction = self.view.gl_widget.get_camera_yaw()  # (See note below)
            bbox_rotation = (view_direction - 90) % 360  # +90° offset and normalize
            
            # Align bbox rotation with the view direction
            bbox.set_z_rotation(bbox_rotation)  # Rotate bbox to face the camera
            self.bboxes.append(bbox)
            self.set_active_bbox(self.bboxes.index(bbox))
            self.selected_bbox_ids.add(self.bboxes.index(bbox))
            
            # Update UI dropdown to "car"
            self.view.current_class_dropdown.setCurrentText("car")
            self.view.status_manager.update_status(
                "Bounding Box added (aligned with view).", Mode.CORRECTION
            )

    def update_bbox(self, bbox_id: int, bbox: BBox) -> None:
        if isinstance(bbox, BBox) and (0 <= bbox_id < len(self.bboxes)):
            self.bboxes[bbox_id] = bbox
            self.update_label_list()

    def delete_bbox(self, bbox_id: int) -> None:
        if 0 <= bbox_id < len(self.bboxes):
            del self.bboxes[bbox_id]
            if bbox_id == self.active_bbox_id:
                self.set_active_bbox(len(self.bboxes) - 1)
            else:
                self.update_label_list()

    def delete_current_bbox(self) -> None:
        selected_item_id = self.view.label_list.currentRow()
        self.delete_bbox(selected_item_id)

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Changed: when selected a bbox by double-clicking, make the box size stay, not go back to default
    def set_active_bbox(self, bbox_id: int) -> None:
        if 0 <= bbox_id < len(self.bboxes):
            bbox = self.bboxes[bbox_id]
            
            # 1. SAVE the current actual dimensions
            current_dims = bbox.get_dimensions() 
            current_rot = bbox.get_rotations()

            self.active_bbox_id = bbox_id
            
            self.update_all() 
            
            bbox.set_dimensions(*current_dims)

            bbox.set_rotations(*current_rot)

            self.view.status_manager.update_status(
                "Bounding Box selected, it can now be corrected.", mode=Mode.CORRECTION
            )
        else:
            self.deselect_bbox()

    @has_active_bbox_decorator
    def set_classname(self, new_class: str) -> None:
        logging.debug(f"set_classname() called from:\n{''.join(traceback.format_stack())}")
        active_bbox = self.get_active_bbox()  # type: ignore
        
        # Update the class name first
        active_bbox.set_classname(new_class)
        
        # Resize based on class
        if new_class == "car":
            active_bbox.set_dimensions(
                config.getfloat("LABEL_DEFAULTS", "car_length"),
                config.getfloat("LABEL_DEFAULTS", "car_width"),
                config.getfloat("LABEL_DEFAULTS", "car_height")
            )
        elif new_class == "pedestrian":
            active_bbox.set_dimensions(
                config.getfloat("LABEL_DEFAULTS", "pedestrian_length"),
                config.getfloat("LABEL_DEFAULTS", "pedestrian_width"),
                config.getfloat("LABEL_DEFAULTS", "pedestrian_height")
            )
        elif new_class == "cyclist":
            active_bbox.set_dimensions(
                config.getfloat("LABEL_DEFAULTS", "cyclist_length"),
                config.getfloat("LABEL_DEFAULTS", "cyclist_width"),
                config.getfloat("LABEL_DEFAULTS", "cyclist_height")
            )
        
        # Update the UI
        self.update_label_list()
        self.view.update_bbox_stats(active_bbox)

    @has_active_bbox_decorator
    def set_center(self, cx: float, cy: float, cz: float) -> None:
        self.get_active_bbox().center = (cx, cy, cz)  # type: ignore

    def set_bboxes(self, bboxes: List[BBox]) -> None:
        self.bboxes = bboxes
        self.deselect_bbox()
        self.deselect_all_bboxes()  # Clear selection when loading new boxes
        self.update_label_list()

    def reset(self) -> None:
        self.deselect_bbox()
        self.set_bboxes([])

    def deselect_bbox(self) -> None:
        self.active_bbox_id = -1
        self.update_all()
        self.view.status_manager.set_mode(Mode.NAVIGATION)

    # MANIPULATORS
    @has_active_bbox_decorator
    def update_position(self, axis: str, value: float) -> None:
        if axis == "pos_x":
            self.get_active_bbox().set_x_translation(value)  # type: ignore
        elif axis == "pos_y":
            self.get_active_bbox().set_y_translation(value)  # type: ignore
        elif axis == "pos_z":
            self.get_active_bbox().set_z_translation(value)  # type: ignore
        else:
            raise Exception("Wrong axis describtion.")

    @has_active_bbox_decorator
    def update_dimension(self, dimension: str, value: float) -> None:
        if dimension == "length":
            self.get_active_bbox().set_length(value)  # type: ignore
        elif dimension == "width":
            self.get_active_bbox().set_width(value)  # type: ignore
        elif dimension == "height":
            self.get_active_bbox().set_height(value)  # type: ignore
        else:
            raise Exception("Wrong dimension describtion.")

    @has_active_bbox_decorator
    def update_rotation(self, axis: str, value: float) -> None:
        if axis == "rot_x":
            self.get_active_bbox().set_x_rotation(value)  # type: ignore
        elif axis == "rot_y":
            self.get_active_bbox().set_y_rotation(value)  # type: ignore
        elif axis == "rot_z":
            self.get_active_bbox().set_z_rotation(value)  # type: ignore
        else:
            raise Exception("Wrong axis describtion.")

    @only_zrotation_decorator
    @has_active_bbox_decorator
    def rotate_around_x(
        self, dangle: Optional[float] = None, clockwise: bool = False
    ) -> None:
        dangle = dangle or config.getfloat("LABEL", "std_rotation")
        if clockwise:
            dangle *= -1
        self.get_active_bbox().set_x_rotation(  # type: ignore
            self.get_active_bbox().get_x_rotation() + dangle  # type: ignore
        )

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Changed: rotate_around_y
    @only_zrotation_decorator
    @has_active_bbox_decorator
    def rotate_around_y(
        self, dangle: Optional[float] = None, clockwise: bool = False
    ) -> None:
        dangle = dangle or config.getfloat("LABEL", "std_rotation")
        if clockwise:
            dangle *= -1
        self.get_active_bbox().set_y_rotation(  # type: ignore
            self.get_active_bbox().get_y_rotation() + dangle  # type: ignore
        )
    
    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Changed: rotate_around_z for smaller z angle resolution
    @has_active_bbox_decorator
    def rotate_around_z_fine(
        self,
        dangle: Optional[float] = None,
        clockwise: bool = False,
        absolute: bool = False,
    ) -> None:
        dangle = dangle or config.getfloat("LABEL", "std_rotation_fine")
        if clockwise:
            dangle *= -1
        if absolute:
            self.get_active_bbox().set_z_rotation(dangle)  # type: ignore
        else:
            self.get_active_bbox().set_z_rotation(  # type: ignore
                self.get_active_bbox().get_z_rotation() + dangle  # type: ignore
            )
        self.update_all()

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Changed: rotate_around_z for coarse z angle resolution
    @has_active_bbox_decorator
    def rotate_around_z_coarse(
        self,
        dangle: Optional[float] = None,
        clockwise: bool = False,
        absolute: bool = False,
    ) -> None:
        dangle = dangle or config.getfloat("LABEL", "std_rotation_coarse")
        if clockwise:
            dangle *= -1
        if absolute:
            self.get_active_bbox().set_z_rotation(dangle)  # type: ignore
        else:
            self.get_active_bbox().set_z_rotation(  # type: ignore
                self.get_active_bbox().get_z_rotation() + dangle  # type: ignore
            )
        self.update_all()

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Changed: rotate_around_z for 180 degrees quickly by pressing the "u/U" key
    @has_active_bbox_decorator
    def rotate_180_degrees(self) -> None:
        """Rotate the active bounding box 180 degrees around its z-axis."""
        current_rotation = self.get_active_bbox().get_z_rotation()  # type: ignore
        new_rotation = current_rotation + 180
        self.get_active_bbox().set_z_rotation(new_rotation)  # type: ignore
        self.update_all()

    @has_active_bbox_decorator
    def rotate_with_mouse(
        self, x_angle: float, y_angle: float
    ) -> None:  # TODO: Make more intuitive
        # Get bbox perspective
        assert self.pcd_manager.pointcloud is not None
        pcd_z_rotation = self.pcd_manager.pointcloud.rot_z
        bbox_z_rotation = self.get_active_bbox().get_z_rotation()  # type: ignore
        total_z_rotation = pcd_z_rotation + bbox_z_rotation

        bbox_cosz = round(np.cos(np.deg2rad(total_z_rotation)), 0)
        bbox_sinz = -round(np.sin(np.deg2rad(total_z_rotation)), 0)

        self.rotate_around_x(y_angle * bbox_cosz)
        self.rotate_around_y(y_angle * bbox_sinz)
        self.rotate_around_z(x_angle)

    @has_active_bbox_decorator
    def translate_along_x(
        self, 
        distance: Optional[float] = None, 
        left: bool = False,
    ) -> None:
        distance = distance or config.getfloat("LABEL", "std_translation")
        if left:
            distance *= -2
        active_bbox: Bbox = self.get_active_bbox()  # type: ignore
        z_rotation_rad = math.radians(active_bbox.get_z_rotation())
        # Left/Right movement (local X-axis)
        dx = distance * math.cos(z_rotation_rad)
        dy = distance * math.sin(z_rotation_rad)

        active_bbox.set_x_translation(active_bbox.center[0] + dx)
        active_bbox.set_y_translation(active_bbox.center[1] + dy)

    @has_active_bbox_decorator
    def translate_along_y(
        self, 
        distance: Optional[float] = None, 
        forward: bool = False
    ) -> None:
        distance = distance or config.getfloat("LABEL", "std_translation")
        if forward:
            distance *= -2
        active_bbox: Bbox = self.get_active_bbox()  # type: ignore
        z_rotation_rad = math.radians(active_bbox.get_z_rotation())
        # Forward/Backward movement (local Y-axis, perpendicular to X)
        dx = -distance * math.sin(z_rotation_rad)  # Negative because +Y is "left" of +X in math convention
        dy = distance * math.cos(z_rotation_rad)

        active_bbox.set_x_translation(active_bbox.center[0] + dx)
        active_bbox.set_y_translation(active_bbox.center[1] + dy)

    @has_active_bbox_decorator
    def translate_along_z(
        self, distance: Optional[float] = None, down: bool = False
    ) -> None:
        distance = distance or config.getfloat("LABEL", "std_translation")
        if down:
            distance *= -1

        active_bbox: Bbox = self.get_active_bbox()  # type: ignore
        active_bbox.set_z_translation(active_bbox.center[2] + distance)

    @has_active_bbox_decorator
    def scale(
        self, length_increase: Optional[float] = None, decrease: bool = False
    ) -> None:
        length_increase = length_increase or config.getfloat("LABEL", "std_scaling")
        if decrease:
            length_increase *= -1
        length, width, height = self.get_active_bbox().get_dimensions()  # type: ignore
        width_length_ratio = width / length
        height_length_ratio = height / length

        new_length = length + length_increase
        new_width = new_length * width_length_ratio
        new_height = new_length * height_length_ratio

        self.get_active_bbox().set_dimensions(new_length, new_width, new_height)  # type: ignore

    @has_active_bbox_decorator
    def scale_along_length(
        self, step: Optional[float] = None, decrease: bool = False
    ) -> None:
        step = step or config.getfloat("LABEL", "std_scaling")
        if decrease:
            step *= -1

        active_bbox: Bbox = self.get_active_bbox()  # type: ignore
        length, width, height = active_bbox.get_dimensions()
        new_length = length + step
        active_bbox.set_dimensions(new_length, width, height)

    @has_active_bbox_decorator
    def scale_along_width(
        self, step: Optional[float] = None, decrease: bool = False
    ) -> None:
        step = step or config.getfloat("LABEL", "std_scaling")
        if decrease:
            step *= -1

        active_bbox: Bbox = self.get_active_bbox()  # type: ignore
        length, width, height = active_bbox.get_dimensions()
        new_width = width + step
        active_bbox.set_dimensions(length, new_width, height)

    @has_active_bbox_decorator
    def scale_along_height(
        self, step: Optional[float] = None, decrease: bool = False
    ) -> None:
        step = step or config.getfloat("LABEL", "std_scaling")
        if decrease:
            step *= -1

        active_bbox: Bbox = self.get_active_bbox()  # type: ignore
        length, width, height = active_bbox.get_dimensions()
        new_height = height + step
        active_bbox.set_dimensions(length, width, new_height)

    def select_bbox_by_ray(self, x: int, y: int) -> None:
        intersected_bbox_id = oglhelper.get_intersected_bboxes(
            x,
            y,
            self.bboxes,
            self.view.gl_widget.modelview,
            self.view.gl_widget.projection,
        )
        if intersected_bbox_id is not None:

            self.set_active_bbox(intersected_bbox_id)


    # HELPER

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Changed: Update bbox stats for active bbox (if any)
    def update_all(self) -> None:

        # Proceed with normal updates
        self.update_z_dial()
        self.update_curr_class()
        self.update_label_list()
        
        if self.has_active_bbox():
            self.view.update_bbox_stats(self.get_active_bbox())
        else:
            self.view.update_bbox_stats(None)
        
        # Force redraw to show selected boxes
        if hasattr(self.view, 'gl_widget'):
            self.view.gl_widget.update()

    @has_active_bbox_decorator
    def update_z_dial(self) -> None:
        self.view.dial_bbox_z_rotation.blockSignals(True)  # To brake signal loop
        self.view.dial_bbox_z_rotation.setValue(int(self.get_active_bbox().get_z_rotation()))  # type: ignore
        self.view.dial_bbox_z_rotation.blockSignals(False)

    def update_curr_class(self) -> None:
        if self.has_active_bbox():
            self.view.current_class_dropdown.setCurrentText(
                self.get_active_bbox().classname  # type: ignore
            )
        else:
            self.view.controller.pcd_manager.populate_class_dropdown()

    def update_label_list(self) -> None:
        """Updates the list of drawn labels and highlights the active label.

        Should be always called if the bounding boxes changed.
        :return: None
        """
        self.view.label_list.blockSignals(True)  # To brake signal loop
        self.view.label_list.clear()
        for bbox in self.bboxes:
            self.view.label_list.addItem(bbox.get_classname())
        if self.has_active_bbox():
            self.view.label_list.setCurrentRow(self.active_bbox_id)
            current_item = self.view.label_list.currentItem()
            if current_item:
                current_item.setSelected(True)
        self.view.label_list.blockSignals(False)

    def assign_point_label_in_active_box(self) -> None:
        box = self.get_active_bbox()
        if box is not None:
            self.pcd_manager.assign_point_label_in_box(box)
            if config.getboolean("USER_INTERFACE", "delete_box_after_assign"):
                self.delete_current_bbox()

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Added: for group selection
    def select_bboxes_in_rectangle(self, start_pos: QPoint, end_pos: QPoint) -> None:
        """Select all bounding boxes within the marquee rectangle."""
        self.deselect_all_bboxes()
        if not self.view or not self.view.gl_widget:
            return
        # Convert screen coordinates to normalized device coordinates
        x1, y1 = min(start_pos.x(), end_pos.x()), min(start_pos.y(), end_pos.y())
        x2, y2 = max(start_pos.x(), end_pos.x()), max(start_pos.y(), end_pos.y())
        print(f"Selection area: ({x1}, {y1}) to ({x2}, {y2})")  # Debug
        # Check each bbox if it's within the selection rectangle
        for i, bbox in enumerate(self.bboxes):
            # Get bbox center in screen coordinates
            center_3d = np.array(bbox.center)
            try:
                center_screen = self._project_3d_to_screen(center_3d)
                print(f"BBox {i} center at screen: {center_screen}")  # Debug
                
                if (x1 <= center_screen[0] <= x2 and y1 <= center_screen[1] <= y2):
                    self.selected_bbox_ids.add(i)
                    print(f"Selected bbox {i}")  # Debug
            except Exception as e:
                print(f"Error projecting bbox {i}: {e}")
                continue
        # Update visual feedback
        self.update_all()
        print(f"Selected {len(self.selected_bbox_ids)} boxes")  # Debug

    def _project_3d_to_screen(self, point_3d: np.ndarray) -> Tuple[float, float]:
        """Project a 3D point to 2D screen coordinates."""
        try:
            modelview = self.view.gl_widget.modelview
            projection = self.view.gl_widget.projection
            viewport = GL.glGetIntegerv(GL.GL_VIEWPORT)
            
            # Convert numpy array to individual components
            screen_coords = GLU.gluProject(
                point_3d[0], point_3d[1], point_3d[2],
                modelview, projection, viewport
            )
            
            # Handle retina displays and device pixel ratio
            device_ratio = self.view.gl_widget.DEVICE_PIXEL_RATIO
            return screen_coords[0] / device_ratio, screen_coords[1] / device_ratio
            
        except Exception as e:
            print(f"Projection error: {e}")
            return -1, -1

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Added: for group selection, copy, paste
    def copy_selected_bboxes(self) -> List[Dict]:
        """Copy selected bounding boxes to clipboard."""
        print(f"copy_selected_bboxes called. Selected boxes: {self.selected_bbox_ids}")
        
        copied_bboxes = []
        for bbox_id in self.selected_bbox_ids:
            if 0 <= bbox_id < len(self.bboxes):
                bbox = self.bboxes[bbox_id]
                print(f"Copying bbox {bbox_id}: {bbox.classname}")
                
                # Create a copy of bbox data - safe for tuples
                bbox_data = {
                    'center': list(bbox.center),  # Convert tuple to list (creates copy)
                    'dimensions': [bbox.length, bbox.width, bbox.height],
                    'rotation': [bbox.get_x_rotation(), bbox.get_y_rotation(), bbox.get_z_rotation()],
                    'classname': bbox.classname,
                }
                copied_bboxes.append(bbox_data)
            else:
                print(f"Invalid bbox_id: {bbox_id}")
        
        print(f"Total boxes copied: {len(copied_bboxes)}")
        return copied_bboxes

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Added: for group selection, copy, paste
    def paste_bboxes_from_clipboard(self, clipboard_data: List[Dict]) -> None:
        """Paste bounding boxes from clipboard as new instances."""
        self.deselect_all_bboxes()  # Clear current selection
        new_bbox_ids = []
        
        for bbox_data in clipboard_data:
            # Create a completely new bbox instance

            # Extract required parameters
            center = bbox_data['center']
            dimensions = bbox_data['dimensions']
            
            # Create BBox with required positional arguments
            new_bbox = BBox(
                cx=center[0],
                cy=center[1], 
                cz=center[2],
                length=dimensions[0],
                width=dimensions[1],
                height=dimensions[2]
            )

            new_bbox.set_dimensions(*bbox_data['dimensions'])
            new_bbox.set_x_rotation(bbox_data['rotation'][0])
            new_bbox.set_y_rotation(bbox_data['rotation'][1])
            new_bbox.set_z_rotation(bbox_data['rotation'][2])
            new_bbox.set_classname(bbox_data['classname'])
            
            self.bboxes.append(new_bbox)
            new_bbox_ids.append(len(self.bboxes) - 1)
        
        # Select the newly pasted bboxes
        self.selected_bbox_ids = set(new_bbox_ids)
        if new_bbox_ids:
            self.active_bbox_id = new_bbox_ids[0]  # Set first as active
        self.update_all()

    def deselect_all_bboxes(self) -> None:
        """Deselect all bounding boxes."""
        self.selected_bbox_ids.clear()
        self.active_bbox_id = -1
        self.update_all()

    def select_bbox_by_ray(self, x: int, y: int) -> None:
        """Select a single bbox by ray casting"""
        intersected_bbox_id = oglhelper.get_intersected_bboxes(
            x,
            y,
            self.bboxes,
            self.view.gl_widget.modelview,
            self.view.gl_widget.projection,
        )
        if intersected_bbox_id is not None:
            self.set_active_bbox(intersected_bbox_id)
            self.selected_bbox_ids.add(intersected_bbox_id)
            #print(f"Selected single bbox {intersected_bbox_id}")

    def delete_selected_bboxes(self) -> None:
        """Delete all selected bounding boxes."""
        # Delete in reverse order to avoid index issues
        for bbox_id in sorted(self.selected_bbox_ids, reverse=True):
            if 0 <= bbox_id < len(self.bboxes):
                del self.bboxes[bbox_id]
        
        # Adjust active_bbox_id if it was among the deleted boxes
        if self.active_bbox_id in self.selected_bbox_ids:
            if self.bboxes:
                self.active_bbox_id = 0
            else:
                self.active_bbox_id = -1
        
        self.selected_bbox_ids = set()
        self.update_all()

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Added: for group translate along x
    def translate_group_along_separate_x(self, left: bool = False) -> None:
        """Translate all selected bboxes along X axis."""
        direction = -1 if left else 1
        distance = config.getfloat("LABEL", "std_translation")
        
        for bbox_id in self.selected_bbox_ids:
            if 0 <= bbox_id < len(self.bboxes):
                bbox = self.bboxes[bbox_id]
                z_rotation_rad = math.radians(bbox.get_z_rotation())
                # Left/Right movement (local X-axis)
                dx = direction * distance * math.cos(z_rotation_rad)
                dy = direction * distance * math.sin(z_rotation_rad)
                
                bbox.set_x_translation(bbox.center[0] + dx)
                bbox.set_y_translation(bbox.center[1] + dy)
        
        self.update_all()

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Added: for group translate along y
    def translate_group_along_separate_y(self, forward: bool = False) -> None:
        """Translate all selected bboxes along Y axis."""
        direction = 1 if forward else -1
        distance = config.getfloat("LABEL", "std_translation")
        
        for bbox_id in self.selected_bbox_ids:
            if 0 <= bbox_id < len(self.bboxes):
                bbox = self.bboxes[bbox_id]
                z_rotation_rad = math.radians(bbox.get_z_rotation())
                # Forward/Backward movement (local Y-axis)
                dx = -direction * distance * math.sin(z_rotation_rad)
                dy = direction * distance * math.cos(z_rotation_rad)
                
                bbox.set_x_translation(bbox.center[0] + dx)
                bbox.set_y_translation(bbox.center[1] + dy)
        
        self.update_all()

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Added: for group translate along z
    def translate_group_along_separate_z(self, down: bool = False) -> None:
        """Translate all selected bboxes along Z axis."""
        direction = -1 if down else 1
        distance = config.getfloat("LABEL", "std_translation")
        
        for bbox_id in self.selected_bbox_ids:
            if 0 <= bbox_id < len(self.bboxes):
                bbox = self.bboxes[bbox_id]
                bbox.set_z_translation(bbox.center[2] + direction * distance)
        
        self.update_all()

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Added: for group translate along x
    def translate_group_along_x(self, left: bool = False) -> None:
        """Translate bboxes along X axis - local for single, global for multiple"""
        direction = -1 if left else 1
        distance = config.getfloat("LABEL", "std_translation")
        
        if len(self.selected_bbox_ids) == 1:
            # Single selection - use local coordinates (follow bbox rotation)
            bbox_id = next(iter(self.selected_bbox_ids))
            if 0 <= bbox_id < len(self.bboxes):
                bbox = self.bboxes[bbox_id]
                z_rotation_rad = math.radians(bbox.get_z_rotation())
                # Left/Right movement (local X-axis)
                dx = direction * distance * math.cos(z_rotation_rad)
                dy = direction * distance * math.sin(z_rotation_rad)
                
                bbox.set_x_translation(bbox.center[0] + dx)
                bbox.set_y_translation(bbox.center[1] + dy)
        else:
            # Multiple selections - use global coordinates
            for bbox_id in self.selected_bbox_ids:
                if 0 <= bbox_id < len(self.bboxes):
                    bbox = self.bboxes[bbox_id]
                    # Global X movement (ignore bbox rotation)
                    bbox.set_x_translation(bbox.center[0] + direction * distance)
        
        self.update_all()

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Added: for group translate along y
    def translate_group_along_y(self, forward: bool = False) -> None:
        """Translate bboxes along Y axis - local for single, global for multiple"""
        direction = -1 if forward else 1
        distance = config.getfloat("LABEL", "std_translation")
        
        if len(self.selected_bbox_ids) == 1:
            # Single selection - use local coordinates (follow bbox rotation)
            bbox_id = next(iter(self.selected_bbox_ids))
            if 0 <= bbox_id < len(self.bboxes):
                bbox = self.bboxes[bbox_id]
                z_rotation_rad = math.radians(bbox.get_z_rotation())
                # Forward/Backward movement (local Y-axis)
                dx = -direction * distance * math.sin(z_rotation_rad)
                dy = direction * distance * math.cos(z_rotation_rad)
                
                bbox.set_x_translation(bbox.center[0] + dx)
                bbox.set_y_translation(bbox.center[1] + dy)
        else:
            # Multiple selections - use global coordinates
            for bbox_id in self.selected_bbox_ids:
                if 0 <= bbox_id < len(self.bboxes):
                    bbox = self.bboxes[bbox_id]
                    # Global Y movement (ignore bbox rotation)
                    bbox.set_y_translation(bbox.center[1] + direction * distance)
        
        self.update_all()

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Added: for group translate along z
    def translate_group_along_z(self, down: bool = False) -> None:
        """Translate bboxes along Z axis - always global (up/down)"""
        direction = -1 if down else 1
        distance = config.getfloat("LABEL", "std_translation")
        
        # Z movement is always global (up/down in world coordinates)
        for bbox_id in self.selected_bbox_ids:
            if 0 <= bbox_id < len(self.bboxes):
                bbox = self.bboxes[bbox_id]
                bbox.set_z_translation(bbox.center[2] + direction * distance)
        
        self.update_all()

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Added: for group rotation
    def rotate_group_around_z(self, fine: bool = False, clockwise: bool = False) -> None:
        """Rotate all selected bboxes around Z axis."""
        angle = config.getfloat("LABEL", "std_rotation_fine" if fine else "std_rotation")
        if clockwise:
            angle = -angle
        
        for bbox_id in self.selected_bbox_ids:
            if 0 <= bbox_id < len(self.bboxes):
                bbox = self.bboxes[bbox_id]
                bbox.set_z_rotation(bbox.get_z_rotation() + angle)
        
        self.update_all()

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Added: for group 180 degrees rotation
    def rotate_group_180_degrees(self) -> None:
        """Rotate all selected bboxes by 180 degrees around Z axis."""
        for bbox_id in self.selected_bbox_ids:
            if 0 <= bbox_id < len(self.bboxes):
                bbox = self.bboxes[bbox_id]
                bbox.set_z_rotation(bbox.get_z_rotation() + 180)
        
        self.update_all()

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Added: for group length change
    def scale_group_along_length(self, decrease: bool = False) -> None:
        """Scale all selected bboxes along length dimension."""
        factor = 0.95 if decrease else 1.05
        
        for bbox_id in self.selected_bbox_ids:
            if 0 <= bbox_id < len(self.bboxes):
                bbox = self.bboxes[bbox_id]
                length, width, height = bbox.get_dimensions()
                bbox.set_dimensions(length * factor, width, height)
        
        self.update_all()

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Added: for group width change
    def scale_group_along_width(self, decrease: bool = False) -> None:
        """Scale all selected bboxes along width dimension."""
        factor = 0.95 if decrease else 1.05
        
        for bbox_id in self.selected_bbox_ids:
            if 0 <= bbox_id < len(self.bboxes):
                bbox = self.bboxes[bbox_id]
                length, width, height = bbox.get_dimensions()
                bbox.set_dimensions(length, width * factor, height)
        
        self.update_all()

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Added: for group height change
    def scale_group_along_height(self, decrease: bool = False) -> None:
        """Scale all selected bboxes along height dimension."""
        factor = 0.95 if decrease else 1.05
        
        for bbox_id in self.selected_bbox_ids:
            if 0 <= bbox_id < len(self.bboxes):
                bbox = self.bboxes[bbox_id]
                length, width, height = bbox.get_dimensions()
                bbox.set_dimensions(length, width, height * factor)
        
        self.update_all()