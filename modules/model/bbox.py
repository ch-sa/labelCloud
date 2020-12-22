import OpenGL.GL as GL
import numpy as np

from modules.control import config_parser
from modules.math3d import translate_point, rotate_around_zyx


class BBox:
    # Defines the order in which the BBox edges are drawn
    BBOX_EDGES = [(0, 1), (0, 3), (0, 4), (2, 1), (2, 3), (2, 6),  # lines to draw the bbox
                  (5, 1), (5, 4), (5, 6), (7, 3), (7, 4), (7, 6)]

    BBOX_SIDES = {"top": [4, 5, 6, 7], "bottom": [0, 1, 2, 3], "right": [2, 3, 7, 6],  # vertices of each side
                  "back": [0, 3, 7, 4], "left": [0, 1, 5, 4], "front": [1, 2, 6, 5]}

    MIN_DIMENSION = config_parser.get_label_settings("MIN_BOUNDINGBOX_DIMENSION")
    STD_LENGTH = config_parser.get_label_settings("STD_BOUNDINGBOX_LENGTH")
    STD_WIDTH = config_parser.get_label_settings("STD_BOUNDINGBOX_WIDTH")
    STD_HEIGHT = config_parser.get_label_settings("STD_BOUNDINGBOX_HEIGHT")

    LIST_OF_CLASSES = set(config_parser.get_label_settings("OBJECT_CLASSES"))
    STD_OBJECT_CLASS = config_parser.get_label_settings("STD_OBJECT_CLASS")

    def __init__(self, cx, cy, cz, length=STD_LENGTH, width=STD_WIDTH, height=STD_HEIGHT):
        self.center = cx, cy, cz
        self._length = length
        self._width = width
        self._height = height
        self.x_rotation = 0
        self.y_rotation = 0
        self.z_rotation = 0
        self._verticies = None
        self._classname = BBox.STD_OBJECT_CLASS
        self.set_axis_aligned_verticies()

    # GETTERS

    def get_classname(self):
        return self._classname

    def get_center(self):
        return self.center

    def get_dimensions(self):
        return self._length, self._width, self._height

    def get_x_rotation(self):
        return self.x_rotation

    def get_y_rotation(self):
        return self.y_rotation

    def get_z_rotation(self):
        return self.z_rotation

    def get_rotations(self):
        return self.x_rotation, self.y_rotation, self.z_rotation

    def get_axis_aligned_vertices(self):
        coords = []
        for vertex in self._verticies:  # Translate relative bbox to center
            coords.append(translate_point(vertex, *self.center))
        return coords

    def get_vertices(self) -> np.array:
        points = self.get_axis_aligned_vertices()
        rotated_points = []
        for p in points:  # ToDo: Replace by matrix multiplication
            p_centered = translate_point(p, *self.center, backwards=True)
            p_rotated = rotate_around_zyx(p_centered, self.x_rotation, self.y_rotation, self.z_rotation, degrees=True)
            rotated_points.append(translate_point(p_rotated, *self.center))
        return np.array(rotated_points)

    def get_volume(self):
        return self._length * self._width * self._height

    # SETTERS

    def set_classname(self, classname):
        if classname:
            self._classname = classname

    def set_dimensions(self, length, width, height):
        if (length > 0) and (width > 0) and (height > 0):
            self._length = length
            self._width = width
            self._height = height
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
        self._verticies = np.array([[-self._length / 2, -self._width / 2, -self._height / 2],
                                    [-self._length / 2, self._width / 2, -self._height / 2],
                                    [self._length / 2, self._width / 2, -self._height / 2],
                                    [self._length / 2, -self._width / 2, -self._height / 2],
                                    [-self._length / 2, -self._width / 2, self._height / 2],
                                    [-self._length / 2, self._width / 2, self._height / 2],
                                    [self._length / 2, self._width / 2, self._height / 2],
                                    [self._length / 2, -self._width / 2, self._height / 2]])

    # Draw the BBox using verticies
    def draw_bbox(self, highlighted=False):
        self.set_axis_aligned_verticies()

        GL.glPushMatrix()

        GL.glTranslate(*self.get_center())
        
        GL.glRotate(self.get_z_rotation(), 0.0, 0.0, 1.0)
        GL.glRotate(self.get_y_rotation(), 0.0, 1.0, 0.0)
        GL.glRotate(self.get_x_rotation(), 1.0, 0.0, 0.0)
        
        GL.glBegin(GL.GL_LINES)  # ToDo: Update to modern OpenGL

        if highlighted:
            GL.glColor3f(0, 1, 0)
        else:
            GL.glColor3f(0, 0, 1)

        for edge in BBox.BBOX_EDGES:  # TODO: Use OGL helper function
            for vertex in edge:
                GL.glVertex3fv(self._verticies[vertex])
        GL.glEnd()

        GL.glPopMatrix()

    def draw_orientation(self, crossed_side: bool = True):
        # Get object coordinates for arrow
        arrow_length = self._length * 0.4
        bp2 = [arrow_length, 0, 0]
        first_edge = [arrow_length * 0.8, arrow_length * 0.3, 0]  # TODO: Refactor to OGL helper
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
            GL.glVertex3fv(self._verticies[BBox.BBOX_SIDES["right"][0]])
            GL.glVertex3fv(self._verticies[BBox.BBOX_SIDES["right"][2]])
            GL.glVertex3fv(self._verticies[BBox.BBOX_SIDES["right"][1]])
            GL.glVertex3fv(self._verticies[BBox.BBOX_SIDES["right"][3]])
        GL.glEnd()
        GL.glLineWidth(1)
        GL.glPopMatrix()

    # MANIPULATORS

    # Translate bbox by cx, cy, cz
    def translate_bbox(self, dx, dy, dz):
        self.center = translate_point(list(self.center), dx, dy, dz)

    # Translate bbox away from extension by half distance
    def translate_side(self, p_id_s, p_id_o, distance):
        direction = np.subtract(self.get_vertices()[p_id_s], self.get_vertices()[p_id_o])
        translation_vector = direction / np.linalg.norm(direction) * (distance / 2)
        self.center = translate_point(self.center, *translation_vector)

    # Extend bbox side by distance
    def change_side(self, side, distance):  # ToDo: Move to controler?
        if side == "right" and self._length + distance > BBox.MIN_DIMENSION:
            self._length += distance
            self.translate_side(3, 0, distance)  # TODO: Make dependen from side list
        if side == "left" and self._length + distance > BBox.MIN_DIMENSION:
            self._length += distance
            self.translate_side(0, 3, distance)
        if side == "front" and self._width + distance > BBox.MIN_DIMENSION:
            self._width += distance
            self.translate_side(1, 0, distance)
        if side == "back" and self._width + distance > BBox.MIN_DIMENSION:
            self._width += distance
            self.translate_side(0, 1, distance)
        if side == "top" and self._height + distance > BBox.MIN_DIMENSION:
            self._height += distance
            self.translate_side(4, 0, distance)
        if side == "bottom" and self._height + distance > BBox.MIN_DIMENSION:
            self._height += distance
            self.translate_side(0, 4, distance)
