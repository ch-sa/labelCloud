import logging
from typing import List, Optional

import numpy as np
import numpy.typing as npt

import OpenGL.GL as GL

from ..control.config_manager import config
from ..definitions import (
    BBOX_EDGES,
    BBOX_SIDES,
    Color3f,
    Dimensions3D,
    Point3D,
    Rotations3D,
)
from ..io.labels.config import LabelConfig
from ..utils import math3d, oglhelper


class BBox(object):
    MIN_DIMENSION: float = config.getfloat("LABEL", "MIN_BOUNDINGBOX_DIMENSION")
    HIGHLIGHTED_COLOR: Color3f = Color3f(0, 1, 0)

    def __init__(
        self,
        cx: float,
        cy: float,
        cz: float,
        length: Optional[float] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
    ) -> None:
        self.center: Point3D = (cx, cy, cz)
        self.length: float = length or config.getfloat(
            "LABEL", "STD_BOUNDINGBOX_LENGTH"
        )
        self.width: float = width or config.getfloat("LABEL", "STD_BOUNDINGBOX_WIDTH")
        self.height: float = height or config.getfloat(
            "LABEL", "STD_BOUNDINGBOX_HEIGHT"
        )
        self.x_rotation: float = 0
        self.y_rotation: float = 0
        self.z_rotation: float = 0
        self.classname: str = LabelConfig().get_default_class_name()
        self.verticies: npt.NDArray = np.zeros((8, 3))
        self.set_axis_aligned_verticies()

    # GETTERS

    def get_center(self) -> Point3D:
        return self.center

    def get_dimensions(self) -> Dimensions3D:
        return self.length, self.width, self.height

    def get_rotations(self) -> Rotations3D:
        return self.x_rotation, self.y_rotation, self.z_rotation

    def get_x_rotation(self) -> float:
        return self.x_rotation

    def get_y_rotation(self) -> float:
        return self.y_rotation

    def get_z_rotation(self) -> float:
        return self.z_rotation

    def get_classname(self) -> str:
        return self.classname

    def get_vertices(self) -> npt.NDArray:
        rotated_vertices = math3d.rotate_bbox_around_center(
            self.get_axis_aligned_vertices(),
            self.center,
            self.get_rotations(),
        )
        return np.array(rotated_vertices)

    def get_axis_aligned_vertices(self) -> List[Point3D]:
        coords = []
        for vertex in self.verticies:  # Translate relative bbox to center
            coords.append(math3d.translate_point(vertex, *self.center))
        return coords

    def get_volume(self) -> float:
        return self.length * self.width * self.height

    # SETTERS

    def set_classname(self, classname: str) -> None:
        if classname:
            self.classname = classname

    def set_length(self, length: float) -> None:
        if length > 0:
            self.length = length
        else:
            logging.warning("New length is too small.")

    def set_width(self, width: float) -> None:
        if width > 0:
            self.width = width
        else:
            logging.warning("New width is too small.")

    def set_height(self, height: float) -> None:
        if height > 0:
            self.height = height
        else:
            logging.warning("New height is too small.")

    def set_dimensions(self, length: float, width: float, height: float) -> None:
        if (length > 0) and (width > 0) and (height > 0):
            self.length = length
            self.width = width
            self.height = height
        else:
            logging.warning("New dimensions are too small.")

    def set_x_rotation(self, angle: float) -> None:
        self.x_rotation = angle % 360

    def set_y_rotation(self, angle: float) -> None:
        self.y_rotation = angle % 360

    def set_z_rotation(self, angle: float) -> None:
        self.z_rotation = angle % 360

    def set_rotations(self, x_angle: float, y_angle: float, z_angle: float):
        self.x_rotation = x_angle
        self.y_rotation = y_angle
        self.z_rotation = z_angle

    def set_x_translation(self, x_translation: float) -> None:
        self.center = (x_translation, *self.center[1:])

    def set_y_translation(self, y_translation: float) -> None:
        self.center = (self.center[0], y_translation, self.center[2])

    def set_z_translation(self, z_translation: float) -> None:
        self.center = (*self.center[:2], z_translation)

    # Updates the dimension of the BBox (important after scaling!)
    def set_axis_aligned_verticies(self) -> None:
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
    def draw_bbox(self, highlighted: bool = False) -> None:
        self.set_axis_aligned_verticies()

        GL.glPushMatrix()
        bbox_color = LabelConfig().get_class_color(self.classname)
        if highlighted:
            bbox_color = self.HIGHLIGHTED_COLOR

        vertices = self.get_vertices()
        drawing_sequence = []
        for edge in BBOX_EDGES:
            for vertex_id in edge:
                drawing_sequence.append(vertices[vertex_id])

        oglhelper.draw_lines(drawing_sequence, color=Color3f.to_rgba(bbox_color))
        GL.glPopMatrix()

    def draw_orientation(self, crossed_side: bool = True) -> None:
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
            GL.glVertex3fv(self.verticies[BBOX_SIDES["right"][0]])
            GL.glVertex3fv(self.verticies[BBOX_SIDES["right"][2]])
            GL.glVertex3fv(self.verticies[BBOX_SIDES["right"][1]])
            GL.glVertex3fv(self.verticies[BBOX_SIDES["right"][3]])
        GL.glEnd()
        GL.glLineWidth(1)
        GL.glPopMatrix()

    # MANIPULATORS

    # Translate bbox by cx, cy, cz
    def translate_bbox(self, dx: float, dy: float, dz: float) -> None:
        self.center = math3d.translate_point(self.center, dx, dy, dz)

    # Translate bbox away from extension by half distance
    def translate_side(self, p_id_s: int, p_id_o: int, distance: float) -> None:
        # TODO: add doc string
        direction = np.subtract(
            self.get_vertices()[p_id_s], self.get_vertices()[p_id_o]
        )
        translation_vector = direction / np.linalg.norm(direction) * (distance / 2)
        self.center = math3d.translate_point(self.center, *translation_vector)

    # Extend bbox side by distance
    def change_side(
        self, side: str, distance: float
    ) -> None:  # ToDo: Move to controller?
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

    def is_inside(self, points: npt.NDArray[np.float32]) -> npt.NDArray[np.bool_]:
        vertices = self.get_vertices().copy()

        #        .------------.
        #       /|           /|
        #      / |          / |
        # (p1).------------.  |
        #     |  |         |  |
        #     |  |         |  |
        #     |  .(p2)_____|__.
        #     | /          | /
        #     ./___________./
        #   (p0)           (p3)

        p0 = vertices[0]
        p1 = vertices[3]
        p2 = vertices[1]
        p3 = vertices[4]

        # p0 as origin
        v1 = p1 - p0
        v2 = p2 - p0
        v3 = p3 - p0

        u = points - p0
        u_dot_v1 = u.dot(v1)
        u_dot_v2 = u.dot(v2)
        u_dot_v3 = u.dot(v3)

        inside_v1 = np.logical_and(np.sum(v1**2) > u_dot_v1, u_dot_v1 > 0)
        inside_v2 = np.logical_and(np.sum(v2**2) > u_dot_v2, u_dot_v2 > 0)
        inside_v3 = np.logical_and(np.sum(v3**2) > u_dot_v3, u_dot_v3 > 0)

        points_inside: npt.NDArray[np.bool_] = np.logical_and(
            np.logical_and(inside_v1, inside_v2), inside_v3
        )
        return points_inside
