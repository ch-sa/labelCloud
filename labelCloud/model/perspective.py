from dataclasses import dataclass
from gettext import translation
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from . import PointCloud


@dataclass
class Perspective(object):
    translation: Tuple[float, float, float]
    rotation: Tuple[float, float, float]

    @classmethod
    def from_point_cloud(cls, pointcloud: "PointCloud") -> "Perspective":
        return cls(
            translation=tuple(pointcloud.get_translations()),
            rotation=tuple(pointcloud.get_rotations()),
        )
