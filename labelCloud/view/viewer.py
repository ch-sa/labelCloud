import logging
from contextlib import contextmanager
from typing import Optional, Tuple, Union

import numpy as np
import numpy.typing as npt
import OpenGL.GL as GL
from OpenGL import GLU
from PyQt5 import QtGui, QtOpenGL
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5.QtCore import Qt, QPoint, QEvent

from ..control.alignmode import AlignMode
from ..control.bbox_controller import BoundingBoxController
from ..control.config_manager import config
from ..control.drawing_manager import DrawingManager
from ..control.pcd_manager import PointCloudManger
from ..definitions.types import Color4f, Point2D
from ..utils import oglhelper
import math
from PyQt5.QtGui import QQuaternion, QVector3D

# Yiming added
from OpenGL.GL import (
    glGetIntegerv, glGetDoublev, GL_VIEWPORT, glReadPixels, 
    GL_MODELVIEW_MATRIX, GL_PROJECTION_MATRIX,
    GL_DEPTH_COMPONENT, GL_FLOAT
)
from OpenGL.GLU import gluUnProject

@contextmanager
def ignore_depth_mask():
    GL.glDepthMask(GL.GL_FALSE)
    try:
        yield
    finally:
        GL.glDepthMask(GL.GL_TRUE)

# Main widget for presenting the point cloud
class GLWidget(QtOpenGL.QGLWidget):
    NEAR_PLANE = config.getfloat("USER_INTERFACE", "near_plane")
    FAR_PLANE = config.getfloat("USER_INTERFACE", "far_plane")

    def __init__(self, parent=None) -> None:
        QtOpenGL.QGLWidget.__init__(self, parent)
        self.setMouseTracking(
            True
        )  # mouseMoveEvent is called also without button pressed

        self.modelview: Optional[npt.NDArray] = None
        self.projection: Optional[npt.NDArray] = None
        self.DEVICE_PIXEL_RATIO: float = (
            self.devicePixelRatioF()
        )  # 1 = normal; 2 = retina display
        oglhelper.DEVICE_PIXEL_RATIO = (
            self.DEVICE_PIXEL_RATIO
        )  # set for helper functions

        self.pcd_manager: PointCloudManger = None  # type: ignore
        self.bbox_controller: BoundingBoxController = None  # type: ignore
        self.controller = None

        # Objects to be drawn
        self.crosshair_pos: Point2D = (0, 0)
        self.crosshair_col: Color4f = (0, 1, 0, 1)
        self.selected_side_vertices: npt.NDArray = np.array([])
        self.drawing_mode: DrawingManager = None  # type: ignore
        self.align_mode: Union[AlignMode, None] = None

        # Yiming added
        # Camera control parameters
        self.camera_distance = 150.0
        self.camera_target = np.array([0, 0, 0])
        self.camera_pan = np.array([0.0, 0.0])
        self.camera_rot_x = 60   # Pitch (similar to working example)
        self.camera_rot_y = 0  # Yaw
        self.camera_rot_z = 0    # Not used for basic view control
        self.last_pos = QPoint()

        # View mode control
        self.view_cycle = ["3D", "top", "front", "back", "left", "right"]
        self.current_view_index = 0
        self.original_view_state = None

        # --- New: Marquee selection state --- 
        self.main_window = parent
        self.shift_pressed = False
        self.is_marquee_active = False
        self.marquee_start_pos = None
        self.marquee_end_pos = None

    def set_pointcloud_controller(self, pcd_manager: "PointCloudManger") -> None:
        self.pcd_manager = pcd_manager

    def set_bbox_controller(self, bbox_controller: "BoundingBoxController") -> None:
        self.bbox_controller = bbox_controller

    def set_controller(self, controller) -> None:
        """Set the controller reference for event forwarding"""
        self.controller = controller
        print(f"Controller set in GLWidget: {controller is not None}")  # Better debug
        
        # Test if we can call methods on the controller
        if hasattr(self.controller, 'mouse_clicked'):
            print("Controller has mouse_clicked method")

    def get_camera_yaw(self) -> float:
        return self.camera_rot_y % 360

    # --- New: Helper function to draw 2D overlays ---
    def _draw_2d_overlay(self):
        """Switches to 2D projection to draw UI elements like the marquee."""
        if not self.is_marquee_active:
            return

        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glPushMatrix()
        GL.glLoadIdentity()
        GLU.gluOrtho2D(0, self.width(), self.height(), 0) # Set ortho for 2D drawing
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glPushMatrix()
        GL.glLoadIdentity()
        GL.glDisable(GL.GL_DEPTH_TEST) # Draw on top of everything

        # Draw the marquee rectangle
        if self.marquee_start_pos and self.marquee_end_pos:
            x0 = self.marquee_start_pos.x()
            y0 = self.marquee_start_pos.y()
            x1 = self.marquee_end_pos.x()
            y1 = self.marquee_end_pos.y()
            # Set color for the rectangle (semi-transparent blue)
            GL.glColor4f(0.3, 0.5, 1.0, 0.3)
            GL.glBegin(GL.GL_QUADS)
            GL.glVertex2f(x0, y0)
            GL.glVertex2f(x1, y0)
            GL.glVertex2f(x1, y1)
            GL.glVertex2f(x0, y1)
            GL.glEnd()
            # Set color for the border (opaque blue)
            GL.glColor4f(0.5, 0.7, 1.0, 0.9)
            GL.glBegin(GL.GL_LINE_LOOP)
            GL.glVertex2f(x0, y0)
            GL.glVertex2f(x1, y0)
            GL.glVertex2f(x1, y1)
            GL.glVertex2f(x0, y1)
            GL.glEnd()
        # Restore previous state
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glPopMatrix()
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glPopMatrix()

    # QGLWIDGET METHODS
    def initializeGL(self) -> None:
        bg_color = [
            int(fl_color)
            for fl_color in config.getlist("USER_INTERFACE", "BACKGROUND_COLOR")
        ]  # floats to ints
        self.qglClearColor(QtGui.QColor(*bg_color))  # screen background color
        GL.glEnable(GL.GL_DEPTH_TEST)  # for visualization of depth
        GL.glEnable(GL.GL_BLEND)  # enable transparency
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        logging.info("Intialized widget.")

        # Must be written again, due to buffer clearing
        self.pcd_manager.pointcloud.create_buffers()  # type: ignore

    def resizeGL(self, width, height) -> None:
        logging.info("Resized widget.")
        GL.glViewport(0, 0, width, height)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        aspect = width / float(height)
        GLU.gluPerspective(45.0, aspect, GLWidget.NEAR_PLANE, GLWidget.FAR_PLANE)
        GL.glMatrixMode(GL.GL_MODELVIEW)

    # Original paintGL function
    def paintGL(self) -> None:
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glPushMatrix()
        # Apply camera transformations
        self._apply_pointcloud_transformations()
        # Draw point cloud
        self.pcd_manager.pointcloud.draw_pointcloud()  # type: ignore
        # Get actual matrices for click unprojection
        self.modelview = GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX)
        self.projection = GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)
        with ignore_depth_mask():
            if config.getboolean("USER_INTERFACE", "show_floor"):
                oglhelper.draw_xy_plane(self.pcd_manager.pointcloud)  # type: ignore
            if self.crosshair_pos:
                cx, cy, cz = self.get_world_coords(*self.crosshair_pos, correction=True)
                oglhelper.draw_crosshair(cx, cy, cz, color=self.crosshair_col)
            if self.drawing_mode.has_preview():
                self.drawing_mode.draw_preview()
            if self.align_mode is not None and self.align_mode.is_active:
                self.align_mode.draw_preview()
            if len(self.selected_side_vertices) == 4:
                oglhelper.draw_rectangles(self.selected_side_vertices, color=(0, 1, 0, 0.3))
        # Draw active bbox
        if self.bbox_controller.has_active_bbox():
            self.bbox_controller.get_active_bbox().draw_bbox(highlighted=True)  # type: ignore
            if config.getboolean("USER_INTERFACE", "show_orientation"):
                self.bbox_controller.get_active_bbox().draw_orientation()  # type: ignore
        # Draw labeled bboxes
        # Draw labeled bboxes with proper selection highlighting
        for i, bbox in enumerate(self.bbox_controller.bboxes):
            is_active = (i == self.bbox_controller.active_bbox_id)
            is_selected = (i in self.bbox_controller.selected_bbox_ids)
            bbox.draw_bbox(highlighted=is_active, selected=is_selected)
        GL.glPopMatrix()
        
        # Draw 2D overlays (like marquee selection) - ALWAYS call this
        self._draw_2d_overlay()

    # Translates the 2D cursor position from screen plane into 3D world space coordinates
    def get_world_coords(
        self, x: float, y: float, z: Optional[float] = None, correction: bool = False
    ) -> Tuple[float, float, float]:
        x *= self.DEVICE_PIXEL_RATIO  # For fixing mac retina bug
        y *= self.DEVICE_PIXEL_RATIO

        # Stored projection matrices are taken from loop
        viewport = GL.glGetIntegerv(GL.GL_VIEWPORT)
        real_y = viewport[3] - y  # adjust for down-facing y positions

        if z is None:
            buffer_size = 21
            center = buffer_size // 2 + 1
            depths = GL.glReadPixels(
                x - center + 1,
                real_y - center + 1,
                buffer_size,
                buffer_size,
                GL.GL_DEPTH_COMPONENT,
                GL.GL_FLOAT,
            )
            z = depths[center][center]  # Read selected pixel from depth buffer

            if z == 1:
                z = depth_smoothing(depths, center)
            elif correction:
                z = depth_min(depths, center)

        mod_x, mod_y, mod_z = GLU.gluUnProject(
            x, real_y, z, self.modelview, self.projection, viewport
        )
        return mod_x, mod_y, mod_z

    # added for rotation
    def _apply_pointcloud_transformations(self):
        GL.glTranslatef(0, 0, -self.camera_distance)  # Zoom first
        GL.glRotatef(self.camera_rot_x, 1.0, 0.0, 0.0)  # Pitch (X rotation)
        GL.glRotatef(self.camera_rot_y, 0.0, 1.0, 0.0)  # Yaw (Y rotation)
        # Add this to set up Z-up coordinate system:
        GL.glRotatef(-90, 1.0, 0.0, 0.0)  # Make Z point up
        GL.glTranslatef(-self.camera_target[0] + self.camera_pan[0],
                    -self.camera_target[1] + self.camera_pan[1],
                    -self.camera_target[2])  # Positio


    def _apply_bbox_view(self, view_type):
        """Apply bbox-aligned view using quaternion-based calculations"""
        if view_type == "3D":
            if self.original_view_state:
                # Restore original view
                self.camera_distance = self.original_view_state['distance']
                self.camera_rot_x = self.original_view_state['rot_x']
                self.camera_rot_y = self.original_view_state['rot_y']
                self.camera_target = self.original_view_state['target']
                self.camera_pan = np.array([0.0, 0.0])
            return
        
        print("current view: ", view_type)

        if not self.bbox_controller or not self.bbox_controller.has_active_bbox():
            return
            
        bbox = self.bbox_controller.get_active_bbox()
        center = np.array(bbox.center)

        # Get bbox rotations (assuming these methods exist)
        z_rot = QQuaternion.fromAxisAndAngle(0, 0, 1, bbox.get_z_rotation())  # Yaw (Z)
        y_rot = QQuaternion.fromAxisAndAngle(0, 1, 0, bbox.get_y_rotation())  # Roll (Y)
        x_rot = QQuaternion.fromAxisAndAngle(1, 0, 0, bbox.get_x_rotation())  # Pitch (X)
        
        # Combine in ZYX order
        bbox_rotation = z_rot * y_rot * x_rot

        # Calculate view distance based on bbox size
        bbox_size = max(bbox.length, bbox.width, bbox.height)
        view_distance = bbox_size * 2.5
        
        # Store original view if not already stored
        if self.original_view_state is None:
            self.original_view_state = {
                'distance': self.camera_distance,
                'rot_x': self.camera_rot_x,
                'rot_y': self.camera_rot_y,
                'target': self.camera_target.copy()
            }
        
        # Base view directions
        if view_type == 'left':
            view_dir = QVector3D(0, -1, 0)  # -Y
        elif view_type == 'right':
            view_dir = QVector3D(0, 1, 0)   # +Y
        elif view_type == 'top':
            view_dir = QVector3D(0, 0, -1)  # -Z
        elif view_type == 'bottom':
            view_dir = QVector3D(0, 0, 1)   # +Z
        elif view_type == 'back':
            view_dir = QVector3D(1, 0, 0)   # +X
        elif view_type == 'front':
            view_dir = QVector3D(-1, 0, 0)  # -X
        else:  # perspective/3D
            view_dir = QVector3D(-1, -1, -1).normalized()
        
        # Rotate the view direction using the quaternion
        adjusted_dir = bbox_rotation.rotatedVector(view_dir)
        
        # Convert direction to Euler angles
        self.camera_rot_y = math.degrees(math.atan2(adjusted_dir.x(), adjusted_dir.y()))
        self.camera_rot_x = math.degrees(math.atan2(-adjusted_dir.z(), 
                                math.sqrt(adjusted_dir.x()**2 + adjusted_dir.y()**2)))
        
        self.camera_distance = view_distance
        self.camera_target = center
        self.camera_pan = np.array([0.0, 0.0])
        
        self.update()

    # Keep only these minimal methods:
    def start_marquee(self, pos: QPoint) -> None:
        """Only handle visual marquee start"""
        print("GLWidget: start_marquee called")
        self.is_marquee_active = True
        self.marquee_start_pos = pos
        self.marquee_end_pos = pos
        self.update()

    def update_marquee(self, pos: QPoint) -> None:
        """Only handle visual marquee update"""
        print("GLWidget: update_marquee called")
        if self.is_marquee_active:
            self.marquee_end_pos = pos
            self.update()

    def end_marquee(self) -> None:
        """Only handle visual marquee end"""
        print("GLWidget: end_marquee called")
        self.is_marquee_active = False
        self.update()
        print("GLWidget: marquee ended and update() called")

    def mousePressEvent(self, event):
        """Handle mouse press - forward to controller AND store position for view manipulation"""
        # Forward to controller first
        if hasattr(self, 'controller') and self.controller:
            self.controller.mouse_clicked(event)

            # If controller handled the event (marquee selection), stop here
            if self.controller.is_marquee_selecting:
                print("Marquee selection active - skipping view manipulation")
                self.last_pos = event.pos()  # Still update position
                return  # Don't proceed to view manipulation

        # Store position for view manipulation (keep your original code)
        self.last_pos = event.pos()
        
        # Call parent implementation
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse movement - forward to controller AND handle view manipulation"""
        # Forward to controller first
        if hasattr(self, 'controller') and self.controller:
            self.controller.mouse_move_event(event)

            # If controller handled the event (marquee selection), stop here
            if self.controller.is_marquee_selecting:
                print("Marquee selection active - skipping view manipulation")
                self.last_pos = event.pos()  # Still update position
                return  # Don't proceed to view manipulation

        # KEEP YOUR ORIGINAL VIEW MANIPULATION CODE
        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()

        # Base speeds (adjust these to your preference)
        BASE_ROT_SPEED = 0.2
        BASE_PAN_SPEED = 0.4
        
        # Adaptive speed factor (0.1-1.0 range)
        zoom_ratio = np.clip(self.camera_distance / 150, 0.1, 1.0)
        adaptive_factor = 0.2 + (0.8 * zoom_ratio)  # Scales from 0.2 to 1.0

        if event.buttons() == Qt.LeftButton:
            # Orbit rotation - now using X (pitch) and Y (yaw) rotations
            rot_speed = BASE_ROT_SPEED * adaptive_factor
            self.camera_rot_y += dx * rot_speed  # Yaw (left/right movement)
            self.camera_rot_x += dy * rot_speed  # Pitch (up/down movement)
            
        elif event.buttons() == Qt.MiddleButton:
            pan_speed = BASE_PAN_SPEED * adaptive_factor * 0.2
            rot_x, rot_y = np.radians(self.camera_rot_x), np.radians(self.camera_rot_y)
            
            # Calculate right and up vectors in one step
            right_x, right_y = np.cos(rot_y), np.sin(rot_y)
            up_x, up_y = -np.sin(rot_y)*np.sin(rot_x), np.cos(rot_y)*np.sin(rot_x)
            
            # Apply panning (with vertical sign flip)
            self.camera_pan[0] += (dx * right_x + dy * up_x) * pan_speed
            self.camera_pan[1] -= (dx * right_y + dy * up_y) * pan_speed

        self.last_pos = event.pos()
        self.update()
        
        # Call parent implementation
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release - forward to controller"""
        if hasattr(self, 'controller') and self.controller:
            self.controller.mouse_released(event)
        
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        """Handle wheel events with priority to controller"""
        # First, give controller a chance to handle the event
        # if hasattr(self, 'controller') and self.controller:
        #     # Create a temporary event to avoid modifying original
        #     temp_event = QtGui.QWheelEvent(event)
        #     self.controller.mouse_scroll_event(temp_event)
            
        #     # If controller accepted the event, stop here
        #     if temp_event.isAccepted():
        #         print("Controller handled scroll event")
        #         return
        
        # If controller didn't handle it, do normal zoom
        #print("GLWidget handling normal zoom")
        self.handle_normal_zoom(event.angleDelta().y())
        event.accept()

    def handle_normal_zoom(self, delta_y):
        """Original zoom logic from your GLWidget"""
        zoom_ratio = np.clip(self.camera_distance / 100, 0.1, 1.0)
        adaptive_factor = 0.3 + (0.7 * zoom_ratio)
        zoom_step = delta_y * 0.1 * adaptive_factor
        self.camera_distance = np.clip(self.camera_distance - zoom_step, -200, 150)
        self.update()

# Creates a circular mask with radius around center
def circular_mask(arr_length, center, radius) -> np.ndarray:
    dx = np.arange(arr_length)
    return (dx[np.newaxis, :] - center) ** 2 + (
        dx[:, np.newaxis] - center
    ) ** 2 < radius**2

# Returns the minimum (closest) depth for a specified radius around the center
def depth_min(depths, center, r=4) -> float:
    selected_depths = depths[circular_mask(len(depths), center, r)]
    filtered_depths = selected_depths[(0 < selected_depths) & (selected_depths < 1)]
    if 0 in depths:  # Check if cursor is at widget border
        return 1
    elif len(filtered_depths) > 0:
        return np.min(filtered_depths)
    else:
        return 0.5

# Returns the mean depth for a specified radius around the center
def depth_smoothing(depths, center, r=15) -> float:
    selected_depths = depths[circular_mask(len(depths), center, r)]
    if 0 in depths:  # Check if cursor is at widget border
        return 1
    elif np.isnan(
        selected_depths[selected_depths < 1]
    ).all():  # prevent mean of empty slice
        return 1
    return np.nanmedian(selected_depths[selected_depths < 1])


