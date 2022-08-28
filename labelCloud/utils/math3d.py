import logging
import math
from typing import List, Optional, Tuple, Union

import numpy as np
import numpy.typing as npt

from ..definitions import Point3D, Rotations3D


# LENGTH
def vector_length(point: Union[Point3D, npt.ArrayLike]) -> float:
    return float(np.linalg.norm(point))


# TRANSLATION
def translate_point(
    point: Union[Point3D, npt.NDArray],
    dx: float,
    dy: float,
    dz: float,
    backwards: bool = False,
) -> Point3D:
    if backwards:
        dx, dy, dz = (-dx, -dy, -dz)
    return tuple(np.add(np.array(point), np.array([dx, dy, dz])))  # type: ignore


# ROTATION


def degrees_to_radians(degrees: float) -> float:
    return degrees * (np.pi / 180)


def radians_to_degrees(radians: float) -> float:
    return radians * (180 / np.pi)


def rotate_around_x(point: Point3D, angle: float, degrees: bool = False) -> npt.NDArray:
    if degrees:
        angle = degrees_to_radians(angle)
    r_matrix = np.array(
        [
            [1, 0, 0],
            [0, np.cos(angle), -np.sin(angle)],
            [0, np.sin(angle), np.cos(angle)],
        ]
    )
    return r_matrix.dot(point)


def rotate_around_y(
    point: npt.NDArray, angle: float, degrees: bool = False
) -> npt.NDArray:
    if degrees:
        angle = degrees_to_radians(angle)
    r_matrix = np.array(
        [
            [math.cos(angle), 0, math.sin(angle)],
            [0, 1, 0],
            [-math.sin(angle), 0, math.cos(angle)],
        ]
    )
    return r_matrix.dot(point)


def rotate_around_z(
    point: npt.NDArray, angle: float, degrees: bool = False
) -> npt.NDArray:
    if degrees:
        angle = degrees_to_radians(angle)
    r_matrix = np.array(
        [
            [np.cos(angle), -np.sin(angle), 0],
            [np.sin(angle), np.cos(angle), 0],
            [0, 0, 1],
        ]
    )
    return r_matrix.dot(point)


def rotate_around_zyx(
    point: Point3D,
    x_angle: float,
    y_angle: float,
    z_angle: float,
    degrees: bool = False,
) -> npt.NDArray:  # TODO: Return Point3D?
    return rotate_around_z(
        rotate_around_y(rotate_around_x(point, x_angle, degrees), y_angle, degrees),
        z_angle,
        degrees,
    )


def rotate_bbox_around_center(
    vertices: List[Point3D], center: Point3D, rotations: Rotations3D
) -> List[Point3D]:
    rotated_vertices = []
    for vertex in vertices:
        centered_vertex = translate_point(vertex, *center, backwards=True)
        rotated_vertex = rotate_around_zyx(centered_vertex, *rotations, degrees=True)
        rotated_vertices.append(translate_point(rotated_vertex, *center))
    return rotated_vertices


#  CONVERSION


def vertices2rotations(
    vertices: List[Point3D], centroid: Point3D
) -> Tuple[float, float, float]:
    x_rotation, y_rotation, z_rotation = (0.0, 0.0, 0.0)

    vertices_trans = np.subtract(
        vertices, centroid
    )  # translate bbox to origin # TODO: Translation necessary?

    # Calculate z_rotation
    x_vec = vertices_trans[3] - vertices_trans[0]  # length vector
    z_rotation = radians_to_degrees(np.arctan2(x_vec[1], x_vec[0])) % 360

    # Calculate y_rotation
    if vertices[3][2] != vertices[0][2]:
        logging.info("Bounding box is y-rotated!")
        x_vec_rot = rotate_around_z(
            x_vec, -z_rotation, degrees=True
        )  # apply z-rotation
        y_rotation = -radians_to_degrees(np.arctan2(x_vec_rot[2], x_vec_rot[0])) % 360

    # Calculate x_rotation
    if vertices[0][2] != vertices[1][2]:
        logging.info("Bounding box is x-rotated!")
        y_vec = np.subtract(vertices_trans[1], vertices_trans[0])  # width vector
        y_vec_rot = rotate_around_z(
            y_vec, -z_rotation, degrees=True
        )  # apply z- & y-rotation
        y_vec_rot = rotate_around_y(y_vec_rot, -y_rotation, degrees=True)
        x_rotation = radians_to_degrees(np.arctan2(y_vec_rot[2], y_vec_rot[1])) % 360
        logging.info("x-Rotation: %s" % x_rotation)

    logging.info(
        "Loaded bounding box has rotation (x, y, z): %s, %s, %s"
        % (x_rotation, y_rotation, z_rotation)
    )
    return x_rotation, y_rotation, z_rotation


# INTERSECTION


def get_line_perpendicular(
    line_start: Point3D, line_end: Point3D, point: Point3D
) -> Tuple[Point3D, tuple]:
    """Get line perpendicular to point parallel to x-y-plane

    Returns:
        List[float]: direction vector, intersection point (x, y)
    """
    # Calculate the line equation parameters
    m = (line_start[1] - line_end[1]) / (line_start[0] - line_end[0])
    b = m * -line_end[0] + line_end[1]

    # Calculate line perpendicular parallel to x-y-plane
    intersection_x = (point[0] + m * (point[1] - b)) / (1 + m**2)
    intersection_y = (m * point[0] + m**2 * point[1] + b) / (1 + m**2)
    dir_vector = (
        point[0] - intersection_x,
        point[1] - intersection_y,
        0,
    )  # vector from line to point
    return dir_vector, (intersection_x, intersection_y)


# Calculates intersection between vector (p0, p1) and plane (p_co, p_no)
def get_line_plane_intersection(
    p0: Point3D, p1: Point3D, p_co: Point3D, p_no: Point3D, epsilon=1e-6
) -> Optional[np.ndarray]:
    """Calculate the intersection between a point and a plane.

    :param p0: Point on the line
    :param p1: Point on the line
    :param p_co: Point on the plane
    :param p_no: Normal to the plane
    :param epsilon: Threshold for parallelity
    :return: Intesection point or None (when the intersection can't be found).
    """
    u = np.subtract(p1, p0)
    dot = np.dot(p_no, u)

    if abs(dot) > epsilon:
        # The factor of the point between p0 -> p1 (0 - 1)
        # if 'fac' is between (0 - 1) the point intersects with the segment.
        # Otherwise:
        #  < 0.0: behind p0.
        #  > 1.0: infront of p1.
        w = np.subtract(p0, p_co)
        fac = -np.dot(p_no, w) / dot
        u = np.array(u) * fac
        return np.add(p0, u)
    else:
        return None  # The segment is parallel to plane.
