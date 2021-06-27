from typing import Tuple, List

import OpenGL.GL as GL
import numpy as np

from control.config_manager import config
from utils import math3d
from utils import oglhelper


class BBox:
    # order in which the bounding box edges are drawn
    BBOX_EDGES = [
        (0, 1),
        (0, 3),
        (0, 4),
        (2, 1),
        (2, 3),
        (2, 6),
        (5, 1),
        (5, 4),
        (5, 6),
        (7, 3),
        (7, 4),
        (7, 6),
    ]
    # vertices of each side
    BBOX_SIDES = {
        "top": [4, 5, 6, 7],
        "bottom": [0, 1, 2, 3],
        "right": [2, 3, 7, 6],
        "back": [0, 3, 7, 4],
        "left": [0, 1, 5, 4],
        "front": [1, 2, 6, 5],
    }

    MIN_DIMENSION = config.getfloat("LABEL", "MIN_BOUNDINGBOX_DIMENSION")

    def __init__(
        self,
        cx: float,
        cy: float,
        cz: float,
        length: float = None,
        width: float = None,
        height: float = None,
    ):
        self.center = cx, cy, cz
        self.length = length or config.getfloat("LABEL", "STD_BOUNDINGBOX_LENGTH")
        self.width = width or config.getfloat("LABEL", "STD_BOUNDINGBOX_WIDTH")
        self.height = height or config.getfloat("LABEL", "STD_BOUNDINGBOX_HEIGHT")
        self.x_rotation = 0
        self.y_rotation = 0
        self.z_rotation = 0
        self.classname = config.get("LABEL", "STD_OBJECT_CLASS")
        self.verticies = None
        self.set_axis_aligned_verticies()

    # GETTERS

    def get_center(self) -> Tuple[float, float, float]:
        return self.center

    def get_dimensions(self) -> Tuple[float, float, float]:
        return self.length, self.width, self.height

    def get_rotations(self) -> Tuple[float, float, float]:
        return self.x_rotation, self.y_rotation, self.z_rotation

    def get_x_rotation(self) -> float:
        return self.x_rotation

    def get_y_rotation(self) -> float:
        return self.y_rotation

    def get_z_rotation(self) -> float:
        return self.z_rotation

    def get_classname(self) -> str:
        return self.classname

    def get_vertices(self) -> np.array:
        rotated_vertices = math3d.rotate_bbox_around_center(
            self.get_axis_aligned_vertices(),
            list(self.center),
            list(self.get_rotations()),
        )
        return np.array(rotated_vertices)

    def get_axis_aligned_vertices(self) -> List[List[float]]:
        coords = []
        for vertex in self.verticies:  # Translate relative bbox to center
            coords.append(math3d.translate_point(vertex, *self.center))
        return coords

    def get_volume(self) -> float:
        return self.length * self.width * self.height

    # SETTERS

    def set_classname(self, classname):
        if classname:
            self.classname = classname

    def set_length(self, length):
        if length > 0:
            self.length = length
        else:
            print("New length is too small.")

    def set_width(self, width):
        if width > 0:
            self.width = width
        else:
            print("New width is too small.")

    def set_height(self, height):
        if height > 0:
            self.height = height
        else:
            print("New height is too small.")

    def set_dimensions(self, length, width, height):
        if (length > 0) and (width > 0) and (height > 0):
            self.length = length
            self.width = width
            self.height = height
        else:
            print("New dimensions are too small.")

    def set_x_rotation(self, angle):
        self.x_rotation = angle % 360

    def set_y_rotation(self, angle):
        self.y_rotation = angle % 360

    def set_z_rotation(self, angle):
        self.z_rotation = angle % 360

    def set_rotations(self, x_angle, y_angle, z_angle):
        self.x_rotation = x_angle
        self.y_rotation = y_angle
        self.z_rotation = z_angle

    def set_x_translation(self, x_translation):
        self.center = (x_translation, *self.center[1:])

    def set_y_translation(self, y_translation):
        self.center = (self.center[0], y_translation, self.center[2])

    def set_z_translation(self, z_translation):
        self.center = (*self.center[:2], z_translation)

    # Updates the dimension of the BBox (important after scaling!)
    def set_axis_aligned_verticies(self):
        self.verticies = np.array(
            [
                [-self.length / 2, -self.width / 2, -self.height / 2],
                [-self.length / 2, self.width / 2, -self.height / 2],
                [self.length / 2, self.width / 2, -self.height / 2],
                [self.length / 2, -self.width / 2, -self.height / 2],
                [-self.length / 2, -self.width / 2, self.height / 2],
                [-self.length / 2, self.width / 2, self.height / 2],
                [self.length / 2, self.width / 2, self.height / 2],
                [self.length / 2, -self.width / 2, self.height / 2],
            ]
        )

    # Draw the BBox using verticies
    def draw_bbox(self, highlighted=False):
        self.set_axis_aligned_verticies()

        GL.glPushMatrix()
        bbox_color = (0, 0, 1, 1)
        if highlighted:
            bbox_color = (0, 1, 0, 1)

        vertices = self.get_vertices()
        drawing_sequence = []
        for edge in BBox.BBOX_EDGES:
            for vertex_id in edge:
                drawing_sequence.append(vertices[vertex_id])

        oglhelper.draw_lines(drawing_sequence, color=bbox_color)
        GL.glPopMatrix()

    def draw_orientation(self, crossed_side: bool = True):
        # Get object coordinates for arrow
        arrow_length = self.length * 0.4
        bp2 = [arrow_length, 0, 0]
        first_edge = [
            arrow_length * 0.8,
            arrow_length * 0.3,
            0,
        ]  # TODO: Refactor to OGL helper
        second_edge = [arrow_length * 0.8, arrow_length * -0.3, 0]
        third_edge = [arrow_length * 0.8, 0, arrow_length * 0.3]

        GL.glPushMatrix()
        GL.glLineWidth(5)

        # Apply translation and rotation
        GL.glTranslate(*self.get_center())

        GL.glRotate(self.get_z_rotation(), 0.0, 0.0, 1.0)
        GL.glRotate(self.get_y_rotation(), 0.0, 1.0, 0.0)
        GL.glRotate(self.get_x_rotation(), 1.0, 0.0, 0.0)

        GL.glBegin(GL.GL_LINES)
        GL.glVertex3fv([0, 0, 0])
        GL.glVertex3fv(bp2)
        GL.glVertex3fv(bp2)
        GL.glVertex3fv(first_edge)
        GL.glVertex3fv(bp2)
        GL.glVertex3fv(second_edge)
        GL.glVertex3fv(bp2)
        GL.glVertex3fv(third_edge)
        if crossed_side:
            GL.glVertex3fv(self.verticies[BBox.BBOX_SIDES["right"][0]])
            GL.glVertex3fv(self.verticies[BBox.BBOX_SIDES["right"][2]])
            GL.glVertex3fv(self.verticies[BBox.BBOX_SIDES["right"][1]])
            GL.glVertex3fv(self.verticies[BBox.BBOX_SIDES["right"][3]])
        GL.glEnd()
        GL.glLineWidth(1)
        GL.glPopMatrix()

    # MANIPULATORS

    # Translate bbox by cx, cy, cz
    def translate_bbox(self, dx, dy, dz):
        self.center = math3d.translate_point(list(self.center), dx, dy, dz)

    # Translate bbox away from extension by half distance
    def translate_side(self, p_id_s, p_id_o, distance):
        direction = np.subtract(
            self.get_vertices()[p_id_s], self.get_vertices()[p_id_o]
        )
        translation_vector = direction / np.linalg.norm(direction) * (distance / 2)
        self.center = math3d.translate_point(self.center, *translation_vector)

    # Extend bbox side by distance
    def change_side(self, side, distance):  # ToDo: Move to controller?
        if side == "right" and self.length + distance > BBox.MIN_DIMENSION:
            self.length += distance
            self.translate_side(3, 0, distance)  # TODO: Make dependend from side list
        if side == "left" and self.length + distance > BBox.MIN_DIMENSION:
            self.length += distance
            self.translate_side(0, 3, distance)
        if side == "front" and self.width + distance > BBox.MIN_DIMENSION:
            self.width += distance
            self.translate_side(1, 0, distance)
        if side == "back" and self.width + distance > BBox.MIN_DIMENSION:
            self.width += distance
            self.translate_side(0, 1, distance)
        if side == "top" and self.height + distance > BBox.MIN_DIMENSION:
            self.height += distance
            self.translate_side(4, 0, distance)
        if side == "bottom" and self.height + distance > BBox.MIN_DIMENSION:
            self.height += distance
            self.translate_side(0, 4, distance)
