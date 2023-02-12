from typing import Tuple

from PyQt5.QtGui import QColor

Point2D = Tuple[float, float]
Point3D = Tuple[float, float, float]

Rotations3D = Tuple[float, float, float]  # euler angles in degrees

Translation3D = Point3D

Dimensions3D = Tuple[float, float, float]  # length, width, height in meters

Color4f = Tuple[float, float, float, float]  # type alias for type hinting


class Color3f(tuple):
    def __new__(cls, r, g, b):
        return super(Color3f, cls).__new__(cls, (r, g, b))

    def __repr__(self):
        return "ColorRGB(r={}, g={}, b={})".format(*self)

    @classmethod
    def from_qcolor(cls, color: QColor):
        return cls(color.red() / 255, color.green() / 255, color.blue() / 255)

    @staticmethod
    def to_rgba(color: "Color3f", alpha: float = 1.0) -> Color4f:
        return (*color, alpha)  # type: ignore
