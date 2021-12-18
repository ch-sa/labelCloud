import ctypes
from typing import List, Tuple

import numpy as np
import OpenGL.GL as GL

from ..control.config_manager import config

# Get size of float (4 bytes) for VBOs
SIZE_OF_FLOAT = ctypes.sizeof(ctypes.c_float)


# Creates an array buffer in a VBO
def create_buffer(attributes) -> GL.glGenBuffers:
    bufferdata = (ctypes.c_float * len(attributes))(*attributes)  # float buffer
    buffersize = len(attributes) * SIZE_OF_FLOAT  # buffer size in bytes

    vbo = GL.glGenBuffers(1)
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
    GL.glBufferData(GL.GL_ARRAY_BUFFER, buffersize, bufferdata, GL.GL_STATIC_DRAW)
    GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
    return vbo


class PointCloud(object):
    def __init__(self, path) -> None:
        self.path_to_pointcloud = path
        self.points = None
        self.colors = None
        self.colorless = None
        self.vbo = None
        self.center = (0, 0, 0)
        self.pcd_mins = None
        self.pcd_maxs = None
        self.init_translation = (0, 0, 0)

        # Point cloud transformations
        self.rot_x = 0.0
        self.rot_y = 0.0
        self.rot_z = 0.0
        self.trans_x = 0.0
        self.trans_y = 0.0
        self.trans_z = 0.0

    # GETTERS AND SETTERS
    def get_no_of_points(self) -> int:
        return len(self.points)

    def get_no_of_colors(self) -> int:
        return len(self.colors)

    def get_rotations(self) -> List[float]:
        return [self.rot_x, self.rot_y, self.rot_z]

    def get_translations(self) -> List[float]:
        return [self.trans_x, self.trans_y, self.trans_z]

    def get_mins_maxs(self) -> Tuple[float, float]:
        return self.pcd_mins, self.pcd_maxs

    def get_min_max_height(self) -> Tuple[float, float]:
        return self.pcd_mins[2], self.pcd_maxs[2]

    def set_mins_maxs(self) -> None:
        self.pcd_mins = np.amin(self.points, axis=0)
        self.pcd_maxs = np.amax(self.points, axis=0)

    def set_rot_x(self, angle) -> None:
        self.rot_x = angle % 360

    def set_rot_y(self, angle) -> None:
        self.rot_y = angle % 360

    def set_rot_z(self, angle) -> None:
        self.rot_z = angle % 360

    def set_rotations(self, x: float, y: float, z: float) -> None:
        self.rot_x = x % 360
        self.rot_y = y % 360
        self.rot_z = z % 360

    def set_trans_x(self, val) -> None:
        self.trans_x = val

    def set_trans_y(self, val) -> None:
        self.trans_y = val

    def set_trans_z(self, val) -> None:
        self.trans_z = val

    def set_translations(self, x: float, y: float, z: float) -> None:
        self.trans_x = x
        self.trans_y = y
        self.trans_z = z

    # MANIPULATORS

    def transform_data(self) -> np.ndarray:
        if self.colorless:
            attributes = self.points
        else:
            # Merge coordinates and colors in alternating order
            attributes = np.concatenate((self.points, self.colors), axis=1)

        return attributes.flatten()  # flatten to single list

    def write_vbo(self) -> None:
        v_array = self.transform_data()
        self.vbo = create_buffer(v_array)

    def draw_pointcloud(self) -> None:
        GL.glTranslate(
            self.trans_x, self.trans_y, self.trans_z
        )  # third, pcd translation

        pcd_center = np.add(
            self.pcd_mins, (np.subtract(self.pcd_maxs, self.pcd_mins) / 2)
        )
        GL.glTranslate(*pcd_center)  # move point cloud back

        GL.glRotate(self.rot_x, 1.0, 0.0, 0.0)
        GL.glRotate(self.rot_y, 0.0, 1.0, 0.0)  # second, pcd rotation
        GL.glRotate(self.rot_z, 0.0, 0.0, 1.0)

        GL.glTranslate(*(pcd_center * -1))  # move point cloud to center for rotation

        GL.glPointSize(config.getfloat("POINTCLOUD", "POINT_SIZE"))
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self.vbo)

        if self.colorless:
            stride = 3 * SIZE_OF_FLOAT  # (12 bytes) : [x, y, z] * sizeof(float)
            GL.glPointSize(1)
            GL.glColor3d(
                *config.getlist("POINTCLOUD", "COLORLESS_COLOR")
            )  # IDEA: Color by (height) position
        else:
            stride = (
                6 * SIZE_OF_FLOAT
            )  # (24 bytes) : [x, y, z, r, g, b] * sizeof(float)

        GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
        GL.glVertexPointer(3, GL.GL_FLOAT, stride, None)

        if not self.colorless:
            GL.glEnableClientState(GL.GL_COLOR_ARRAY)
            offset = (
                3 * SIZE_OF_FLOAT
            )  # (12 bytes) : the rgb color starts after the 3 coordinates x, y, z
            GL.glColorPointer(3, GL.GL_FLOAT, stride, ctypes.c_void_p(offset))
        GL.glDrawArrays(GL.GL_POINTS, 0, self.get_no_of_points())  # Draw the points

        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)
        if not self.colorless:
            GL.glDisableClientState(GL.GL_COLOR_ARRAY)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)

    def reset_translation(self) -> None:
        self.trans_x, self.trans_y, self.trans_z = self.init_translation

    def print_details(self) -> None:
        print("Point Cloud Center:\t\t%s" % np.round(self.center, 2))
        print("Point Cloud Minimums:\t%s" % np.round(self.pcd_mins, 2))
        print("Point Cloud Maximums:\t%s" % np.round(self.pcd_maxs, 2))
        print("Initial Translation:\t%s" % np.round(self.init_translation, 2))
