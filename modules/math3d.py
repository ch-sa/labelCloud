import math
from typing import List

import numpy as np


# LENGTH
def vector_length(point: List[float]) -> float:
    return np.linalg.norm(point)


# TRANSLATION
def translate_point(point: List[float], dx: float, dy: float, dz: float, backwards: bool = False) -> np.array:
    if backwards:
        dx, dy, dz = (-dx, -dy, -dz)
    return np.add(np.array(point), np.array([dx, dy, dz]))


# ROTATION

def degrees_to_radians(degrees: float) -> float:
    return degrees * (np.pi / 180)


def radians_to_degrees(radians: float) -> float:
    return radians * (180 / np.pi)


def rotate_around_x(point: List[float], angle: float, degrees: bool = False) -> np.array:
    if degrees:
        angle = degrees_to_radians(angle)
    r_matrix = np.array([[1, 0, 0],
                         [0, np.cos(angle), -np.sin(angle)],
                         [0, np.sin(angle), np.cos(angle)]])
    return r_matrix.dot(point)


def rotate_around_y(point: List[float], angle: float, degrees: bool = False) -> np.array:
    if degrees:
        angle = degrees_to_radians(angle)
    r_matrix = np.array([[math.cos(angle), 0, math.sin(angle)],
                         [0, 1, 0],
                         [-math.sin(angle), 0, math.cos(angle)]])
    return r_matrix.dot(point)


def rotate_around_z(point: List[float], angle: float, degrees: bool = False) -> np.array:
    if degrees:
        angle = degrees_to_radians(angle)
    r_matrix = np.array([[np.cos(angle), -np.sin(angle), 0],
                         [np.sin(angle), np.cos(angle), 0],
                         [0, 0, 1]])
    return r_matrix.dot(point)


def rotate_around_zyx(point: List[float], x_angle: float, y_angle: float, z_angle: float,
                      degrees: bool = False) -> np.array:
    return rotate_around_z(rotate_around_y(rotate_around_x(point, x_angle, degrees), y_angle, degrees),
                           z_angle, degrees)


# INTERSECTION

def get_line_perpendicular(line_start: List[float], line_end: List[float], point: List[float]):
    """Get line perpendicular to point parallel to x-y-plane

    Returns:
        List[float]: direction vector, intersection point (x, y)
    """
    # Calculate the line equation parameters
    m = (line_start[1] - line_end[1]) / (line_start[0] - line_end[0])
    b = m * -line_end[0] + line_end[1]

    # Calculate line perpendicular parallel to x-y-plane
    intersection_x = (point[0] + m * (point[1] - b)) / (1 + m ** 2)
    intersection_y = (m * point[0] + m ** 2 * point[1] + b) / (1 + m ** 2)
    dir_vector = (point[0] - intersection_x, point[1] - intersection_y, 0)  # vector from line to point
    return dir_vector, (intersection_x, intersection_y)


# Calculates intersection between vector (p0, p1) and plane (p_co, p_no)
def get_line_plane_intersection(p0: List[float], p1: List[float], p_co: List[float], p_no: List[float], epsilon=1e-6):
    """ Calculate the intersection between a point and a plane.

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
