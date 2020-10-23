# Create virtual buffer object with coordinates and colors
from typing import TYPE_CHECKING, Union

import numpy as np
import OpenGL.GL as gl
from OpenGL import GLU
from PyQt5 import QtOpenGL, QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from modules import oglhelper
from modules.control import config_parser
from modules.control.alignmode import AlignMode
from modules.control.bbox_controler import BoundingBoxControler
from modules.control.pcd_controler import PointCloudControler

if TYPE_CHECKING:
    from modules.control.drawing_mode import DrawingMode


# Main widget for presenting the point cloud
class GLWidget(QtOpenGL.QGLWidget):
    def __init__(self, parent=None):
        self.parent = parent
        QtOpenGL.QGLWidget.__init__(self, parent)
        self.setMouseTracking(True)  # mouseMoveEvent is called also without button pressed

        self.modelview = None
        self.projection = None

        self.pcd_controler = None
        self.bbox_controler = None

        # Objects to be drawn
        self.draw_floor = config_parser.get_app_settings("SHOW_FLOOR")
        self.draw_orientation = config_parser.get_app_settings("SHOW_ORIENTATION")
        self.crosshair_pos = None
        self.crosshair_col = (0, 1, 0, 1)
        self.selected_side_vertices = []
        self.drawing_mode: Union[DrawingMode, None] = None
        self.align_mode: Union[AlignMode, None] = None

    def set_pointcloud_controler(self, pcd_controler: PointCloudControler):
        self.pcd_controler = pcd_controler

    def set_bbox_controler(self, bbox_controler: BoundingBoxControler):
        self.bbox_controler = bbox_controler

    # QGLWIDGET METHODS

    def initializeGL(self):
        self.qglClearColor(QtGui.QColor(*config_parser.get_app_settings("BACKGROUND_COLOR")))  # screen background color
        gl.glEnable(gl.GL_DEPTH_TEST)  # for visualization of depth
        gl.glEnable(gl.GL_BLEND)  # enable transparency
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
        print("Intialized widget.")

        self.pcd_controler.get_pointcloud().write_vbo()  # Must be written again, due to buffer clearing

    def resizeGL(self, width, height):
        print("Resized widget.")
        gl.glViewport(0, 0, width, height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        aspect = width / float(height)

        GLU.gluPerspective(45.0, aspect, 0.5, 30.0)
        gl.glMatrixMode(gl.GL_MODELVIEW)

    def paintGL(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glPushMatrix()  # push the current matrix to the current stack

        # Draw point cloud
        self.pcd_controler.get_pointcloud().draw_pointcloud()

        # Get actual matrices for click unprojection
        self.modelview = gl.glGetDoublev(gl.GL_MODELVIEW_MATRIX)
        self.projection = gl.glGetDoublev(gl.GL_PROJECTION_MATRIX)

        gl.glDepthMask(gl.GL_FALSE)  # Do not write decoration and preview elements in depth buffer
        # Draw floor net
        if self.draw_floor:
            oglhelper.draw_xy_plane(self.pcd_controler.get_pointcloud())

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

        gl.glDepthMask(gl.GL_TRUE)

        # Draw active bbox
        if self.bbox_controler.has_active_bbox():
            self.bbox_controler.get_active_bbox().draw_bbox(highlighted=True)
            if self.draw_orientation:
                self.bbox_controler.get_active_bbox().draw_orientation()

        # Draw labeled bboxes
        for bbox in self.bbox_controler.get_bboxes():
            bbox.draw_bbox()

        gl.glPopMatrix()  # restore the previous modelview matrix

    # Translates the 2D cursor position from screen plane into 3D world space coordinates
    def get_world_coords(self, x: int, y: int, z: float = None, correction: bool = False):
        viewport = gl.glGetIntegerv(gl.GL_VIEWPORT)  # Stored projection matrices are taken from loop
        real_y = viewport[3] - y  # adjust for down-facing y positions

        if z is None:
            buffer_size = 21
            center = buffer_size // 2 + 1
            depths = gl.glReadPixels(x - center + 1, real_y - center + 1, buffer_size, buffer_size,
                                     gl.GL_DEPTH_COMPONENT, gl.GL_FLOAT)
            z = depths[center][center]  # Read selected pixel from depth buffer
            # print("Uncorrected z: %s" % z)

            if z > 0.99:
                z = depth_smoothing(depths, center)
                # print("Smoothed z: %s" % z)
            elif correction:
                z = depth_min(depths, center)
                # print("Corrected z: %s" % z)

        mod_x, mod_y, mod_z = GLU.gluUnProject(x, real_y, z, self.modelview, self.projection, viewport)
        # print("PROJ: %s" % np.round([mod_x, mod_y, mod_z], 2))
        # if correction:
        #     pcd_mins, pcd_maxs = self.pcd_controler.get_pointcloud().get_mins_maxs()
        #     mod_x, mod_y, mod_z = np.clip((mod_x, mod_y, mod_z), pcd_mins, pcd_maxs)
        #     print("CORR: %s" % np.round([mod_x, mod_y, mod_z], 2))
        return mod_x, mod_y, mod_z


# Returns the minimum (closest) depth for a specified radius around the center
def depth_min(depths, center, r=4):
    dx = np.arange(len(depths))
    mask = (dx[np.newaxis, :] - center) ** 2 + (dx[:, np.newaxis] - center) ** 2 < r ** 2
    selected_depths = depths[mask]
    filtered_depths = selected_depths[(0 < selected_depths) & (selected_depths < 0.99)]
    if len(filtered_depths) > 0:
        return np.min(filtered_depths)
    else:
        return 0.5


# Returns the mean depth for a specified radius around the center
def depth_smoothing(depths, center, r=15):
    dx = np.arange(len(depths))
    mask = (dx[np.newaxis, :] - center) ** 2 + (dx[:, np.newaxis] - center) ** 2 < r ** 2
    selected_depths = depths[mask]
    if 0 in depths:  # Check if cursor at widget border
        return 1
    return np.nanmedian(selected_depths[selected_depths < 0.99])