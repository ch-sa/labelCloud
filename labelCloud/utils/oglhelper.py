from typing import TYPE_CHECKING, List, Optional, Tuple, Union

import numpy as np
import numpy.typing as npt

import OpenGL.GL as GL
from OpenGL import GLU

from . import math3d
from ..definitions import BBOX_SIDES, Color4f, Point3D

if TYPE_CHECKING:
    from ..model import BBox, PointCloud


DEVICE_PIXEL_RATIO: Optional[
    float
] = None  # is set once and for every window resize (retina display fix)


def draw_points(
    points: Union[List[Point3D], npt.NDArray],
    color: Color4f = (0, 1, 1, 1),
    point_size: int = 10,
) -> None:
    GL.glColor4d(*color)
    GL.glPointSize(point_size)
    GL.glBegin(GL.GL_POINTS)
    for point in points:
        GL.glVertex3d(*point)
    GL.glEnd()


def draw_lines(
    points: List[Point3D],
    color: Color4f = (0, 1, 1, 1),
    line_width: int = 2,
) -> None:
    GL.glColor4d(*color)
    GL.glLineWidth(line_width)
    GL.glBegin(GL.GL_LINES)
    for point in points:
        GL.glVertex3d(*point)
    GL.glEnd()


def draw_triangles(vertices: List[Point3D], color: Color4f = (0, 1, 1, 1)) -> None:
    GL.glColor4d(*color)
    GL.glBegin(GL.GL_TRIANGLES)
    for vertex in vertices:
        GL.glVertex3d(*vertex)
    GL.glEnd()


def draw_rectangles(
    vertices: Union[List[Point3D], npt.NDArray],
    color: Color4f = (0, 1, 1, 1),
    line_width: int = 2,
) -> None:
    GL.glColor4d(*color)
    GL.glLineWidth(line_width)
    GL.glBegin(GL.GL_QUADS)
    for vertex in vertices:
        GL.glVertex3d(*vertex)
    GL.glEnd()


def draw_cuboid(
    vertices: Union[List[Point3D], npt.NDArray],
    color: Color4f = (1, 1, 0, 0.5),
    draw_vertices: bool = False,
    vertex_color: Color4f = (0, 1, 1, 1),
) -> None:
    # flatten side vertices
    side_vertices = [
        index for side_indices in BBOX_SIDES.values() for index in side_indices
    ]
    rectangle_vertices = np.array(vertices)[side_vertices]
    draw_rectangles(rectangle_vertices, color=color)
    if draw_vertices:
        draw_points(vertices, color=vertex_color)


def draw_crosshair(
    cx: float, cy: float, cz: float, color: Color4f = (0, 1, 0, 1)
) -> None:
    GL.glBegin(GL.GL_LINES)
    GL.glColor4d(*color)
    GL.glVertex3d(cx + 0.1, cy, cz)  # x-line
    GL.glVertex3d(cx - 0.1, cy, cz)
    GL.glVertex3d(cx, cy + 0.1, cz)  # y-line
    GL.glVertex3d(cx, cy - 0.1, cz)
    GL.glVertex3d(cx, cy, cz + 0.1)  # z-line
    GL.glVertex3d(cx, cy, cz - 0.1)
    GL.glEnd()


def draw_xy_plane(pcd: "PointCloud") -> None:
    mins, maxs = pcd.get_mins_maxs()
    x_min, y_min = np.floor(mins[:2]).astype(int)
    x_max, y_max = np.ceil(maxs[:2]).astype(int)
    GL.glColor3d(0.5, 0.5, 0.5)
    GL.glBegin(GL.GL_LINES)
    for y in range(y_min, y_max + 1):  # x-lines
        GL.glVertex3d(x_min, y, 0)
        GL.glVertex3d(x_max, y, 0)

    for x in range(x_min, x_max + 1):  # y-lines
        GL.glVertex3d(x, y_min, 0)
        GL.glVertex3d(x, y_max, 0)
    GL.glEnd()


# RAY PICKING


def get_pick_ray(x: float, y: float, modelview, projection) -> Tuple[Point3D, Point3D]:
    """
    :param x: rightward screen coordinate
    :param y: downward screen coordinate
    :param modelview: modelview matrix
    :param projection: projection matrix
    :return: two points of the pick ray from the closest and furthest frustum
    """
    x *= DEVICE_PIXEL_RATIO  # type: ignore
    y *= DEVICE_PIXEL_RATIO  # type: ignore

    viewport = GL.glGetIntegerv(GL.GL_VIEWPORT)
    real_y = viewport[3] - y  # adjust for down-facing y positions

    # Unproject screen coords into world coordsdd
    p_front = GLU.gluUnProject(x, real_y, 0, modelview, projection, viewport)
    p_back = GLU.gluUnProject(x, real_y, 1, modelview, projection, viewport)
    return p_front, p_back


def get_intersected_bboxes(
    x: float, y: float, bboxes: List["BBox"], modelview, projection
) -> Union[int, None]:
    """Checks if the picking ray intersects any bounding box from bboxes.

    :param x: x screen coordinate
    :param y: y screen coordinate
    :param bboxes: list of bounding boxes
    :param modelview: modelview matrix
    :param projection: projection matrix
    :return: Id of the intersected bounding box or None if no bounding box is intersected
    """
    intersected_bboxes = {}  # bbox_index: bbox
    for index, bbox in enumerate(bboxes):
        intersection_point, _ = get_intersected_sides(x, y, bbox, modelview, projection)
        if intersection_point is not None:
            intersected_bboxes[index] = intersection_point[2]

    p0, p1 = get_pick_ray(x, y, modelview, projection)  # Calculate picking ray
    if intersected_bboxes and (
        p0[2] >= p1[2]
    ):  # Calculate which intersected bbox is closer to screen
        return max(intersected_bboxes, key=intersected_bboxes.get)  # type: ignore
    elif intersected_bboxes:
        return min(intersected_bboxes, key=intersected_bboxes.get)  # type: ignore
    else:
        return None


def get_intersected_sides(
    x: float, y: float, bbox: "BBox", modelview, projection
) -> Union[Tuple[List[int], str], Tuple[None, None]]:
    """Checks if and with which side of the given bounding box the picking ray intersects.

    :param x: x screen coordinate
    :param y: y screen coordinate:
    :param bbox: bounding box to check for intersection
    :param modelview: modelview matrix
    :param projection: projection matrix
    :return: intersection point, name of intersected side [top, bottom, right, back, left, front]
    """
    p0, p1 = get_pick_ray(x, y, modelview, projection)  # Calculate picking ray
    vertices = bbox.get_vertices()

    intersections: List[
        Tuple[list, str]
    ] = list()  # (intersection_point, bounding box side)
    for side, indices in BBOX_SIDES.items():
        # Calculate plane equation
        pl1 = vertices[indices[0]]  # point in plane
        v1 = np.subtract(vertices[indices[1]], pl1)
        v2 = np.subtract(vertices[indices[3]], pl1)
        n = np.cross(v1, v2)  # plane normal

        intersection = math3d.get_line_plane_intersection(p0, p1, pl1, tuple(n))  # type: ignore

        # Check if intersection is inside rectangle
        if intersection is not None:
            v = np.subtract(intersection, pl1)
            width = np.linalg.norm(v1)
            height = np.linalg.norm(v2)
            proj1 = np.dot(v, v1) / width
            proj2 = np.dot(v, v2) / height

            if (width > proj1 > 0) and (height > proj2 > 0):
                intersections.append((intersection.tolist(), side))

    # Calculate which intersected side is closer
    intersections = sorted(
        intersections, key=lambda element: element[0][2]
    )  # sort by z-value
    if intersections and (p0[2] >= p1[2]):
        return intersections[-1]  # intersection point: list, side: str
    elif intersections:
        return intersections[0]
    else:
        return None, None
