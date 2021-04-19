from typing import Union

import numpy as np
import OpenGL.GL as GL
from OpenGL import GLU
from PyQt5 import QtOpenGL, QtGui

from utils import oglhelper
from control import config_parser
from control.alignmode import AlignMode
from control.bbox_controller import BoundingBoxController
from control.pcd_manager import PointCloudManger
from control.drawing_manager import DrawingManager


# Main widget for presenting the point cloud
class GLWidget(QtOpenGL.QGLWidget):
    def __init__(self, parent=None):
        self.parent = parent
        QtOpenGL.QGLWidget.__init__(self, parent)
        self.setMouseTracking(True)  # mouseMoveEvent is called also without button pressed

        self.modelview = None
        self.projection = None

        self.pcd_controller = None
        self.bbox_controller = None

        # Objects to be drawn
        self.draw_floor = config_parser.get_app_settings("SHOW_FLOOR")
        self.draw_orientation = config_parser.get_app_settings("SHOW_ORIENTATION")
        self.crosshair_pos = None
        self.crosshair_col = (0, 1, 0, 1)
        self.selected_side_vertices = []
        self.drawing_mode: Union[DrawingManager, None] = None
        self.align_mode: Union[AlignMode, None] = None

    def set_pointcloud_controller(self, pcd_controller: PointCloudManger):
        self.pcd_controller = pcd_controller

    def set_bbox_controller(self, bbox_controller: BoundingBoxController):
        self.bbox_controller = bbox_controller

    # QGLWIDGET METHODS

    def initializeGL(self):
        bg_color = [int(fl_color) for fl_color in config_parser.get_app_settings("BACKGROUND_COLOR")]  # floats to ints
        self.qglClearColor(QtGui.QColor(*bg_color))  # screen background color
        GL.glEnable(GL.GL_DEPTH_TEST)  # for visualization of depth
        GL.glEnable(GL.GL_BLEND)  # enable transparency
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        print("Intialized widget.")

        self.pcd_controller.get_pointcloud().write_vbo()  # Must be written again, due to buffer clearing

    def resizeGL(self, width, height):
        print("Resized widget.")
        GL.glViewport(0, 0, width, height)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        aspect = width / float(height)

        GLU.gluPerspective(45.0, aspect, 0.5, 30.0)
        GL.glMatrixMode(GL.GL_MODELVIEW)

        oglhelper.device_pixel_ratio = self.devicePixelRatioF()

    def paintGL(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glPushMatrix()  # push the current matrix to the current stack

        # Draw point cloud
        self.pcd_controller.get_pointcloud().draw_pointcloud()

        # Get actual matrices for click unprojection
        self.modelview = GL.glGetDoublev(GL.GL_MODELVIEW_MATRIX)
        self.projection = GL.glGetDoublev(GL.GL_PROJECTION_MATRIX)

        GL.glDepthMask(GL.GL_FALSE)  # Do not write decoration and preview elements in depth buffer
        # Draw floor net
        if self.draw_floor:
            oglhelper.draw_xy_plane(self.pcd_controller.get_pointcloud())

        # Draw crosshair/ cursor in 3D world
        if self.crosshair_pos:
            cx, cy, cz = self.get_world_coords(*self.crosshair_pos, correction=True)
            oglhelper.draw_crosshair(cx, cy, cz, color=self.crosshair_col)

        if self.drawing_mode.has_preview():
            self.drawing_mode.draw_preview()

        if self.align_mode is not None:
            if self.align_mode.is_active():
                self.align_mode.draw_preview()

        # Highlight selected side with filled rectangle
        if len(self.selected_side_vertices) == 4:
            oglhelper.draw_rectangles(self.selected_side_vertices, color=(0, 1, 0, 0.3))

        GL.glDepthMask(GL.GL_TRUE)

        # Draw active bbox
        if self.bbox_controller.has_active_bbox():
            self.bbox_controller.get_active_bbox().draw_bbox(highlighted=True)
            if self.draw_orientation:
                self.bbox_controller.get_active_bbox().draw_orientation()

        # Draw labeled bboxes
        for bbox in self.bbox_controller.get_bboxes():
            bbox.draw_bbox()

        GL.glPopMatrix()  # restore the previous modelview matrix

    # Translates the 2D cursor position from screen plane into 3D world space coordinates
    def get_world_coords(self, x: int, y: int, z: float = None, correction: bool = False):
        device_pixel_ratio = self.devicePixelRatioF()  # For fixing mac retina bug
        print(f"DEBUG: Device pixel ratio is: {device_pixel_ratio}")
        x *= device_pixel_ratio
        y *= device_pixel_ratio

        viewport = GL.glGetIntegerv(GL.GL_VIEWPORT)  # Stored projection matrices are taken from loop
        real_y = viewport[3] - y  # adjust for down-facing y positions

        if z is None:
            buffer_size = 21
            center = buffer_size // 2 + 1
            depths = GL.glReadPixels(x - center + 1, real_y - center + 1, buffer_size, buffer_size,
                                     GL.GL_DEPTH_COMPONENT, GL.GL_FLOAT)
            z = depths[center][center]  # Read selected pixel from depth buffer

            if z > 0.99:
                z = depth_smoothing(depths, center)
            elif correction:
                z = depth_min(depths, center)

        mod_x, mod_y, mod_z = GLU.gluUnProject(x, real_y, z, self.modelview, self.projection, viewport)
        return mod_x, mod_y, mod_z


# Creates a circular mask with radius around center
def circular_mask(arr_length, center, radius):
    dx = np.arange(arr_length)
    return (dx[np.newaxis, :] - center) ** 2 + (dx[:, np.newaxis] - center) ** 2 < radius ** 2


# Returns the minimum (closest) depth for a specified radius around the center
def depth_min(depths, center, r=4):
    selected_depths = depths[circular_mask(len(depths), center, r)]
    filtered_depths = selected_depths[(0 < selected_depths) & (selected_depths < 0.99)]
    if 0 in depths:  # Check if cursor is at widget border
        return 1
    elif len(filtered_depths) > 0:
        return np.min(filtered_depths)
    else:
        return 0.5


# Returns the mean depth for a specified radius around the center
def depth_smoothing(depths, center, r=15):
    selected_depths = depths[circular_mask(len(depths), center, r)]
    if 0 in depths:  # Check if cursor is at widget border
        return 1
    elif np.isnan(selected_depths[selected_depths < 0.99]).all():  # prevent mean of empty slice
        return 1
    return np.nanmedian(selected_depths[selected_depths < 0.99])
