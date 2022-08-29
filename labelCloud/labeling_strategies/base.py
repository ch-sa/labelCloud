from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from ..definitions import Point3D

if TYPE_CHECKING:
    from ..model import BBox
    from ..view.gui import GUI


class BaseLabelingStrategy(ABC):
    POINTS_NEEDED: int
    PREVIEW: bool = False

    def __init__(self, view: "GUI") -> None:
        self.view = view
        self.points_registered = 0
        self.point_1: Optional[Point3D] = None

    def is_bbox_finished(self) -> bool:
        return self.points_registered >= self.__class__.POINTS_NEEDED

    @abstractmethod
    def register_point(self, new_point: Point3D) -> None:
        raise NotImplementedError

    def register_tmp_point(self, new_tmp_point: Point3D) -> None:
        pass

    def register_scrolling(self, distance: float) -> None:
        pass

    @abstractmethod
    def get_bbox(self) -> "BBox":
        raise NotImplementedError

    def draw_preview(self) -> None:
        pass

    def reset(self) -> None:
        self.points_registered = 0
        self.point_1 = None
