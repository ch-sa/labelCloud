import logging
from typing import TYPE_CHECKING, Optional

import numpy as np

from . import BaseLabelingStrategy
from ..control.config_manager import config
from ..definitions import Mode, Point3D
from ..definitions.types import Point3D
from ..model import BBox
from ..utils import oglhelper as ogl

if TYPE_CHECKING:
    from ..view.gui import GUI


class PickingStrategy(BaseLabelingStrategy):
    POINTS_NEEDED = 1
    PREVIEW = True

    def __init__(self, view: "GUI") -> None:
        super().__init__(view)
        logging.info("Enabled drawing mode.")
        self.view.status_manager.update_status(
            "Please pick the location for the bounding box front center.",
            mode=Mode.DRAWING,
        )
        self.tmp_p1: Optional[Point3D] = None
        self.bbox_z_rotation: float = 0

    def register_point(self, new_point: Point3D) -> None:
        self.point_1 = new_point
        self.points_registered += 1

    def register_tmp_point(self, new_tmp_point: Point3D) -> None:
        self.tmp_p1 = new_tmp_point

    def register_scrolling(self, distance: float) -> None:
        self.bbox_z_rotation += distance // 30

    def draw_preview(self) -> None:  # TODO: Refactor
        if self.tmp_p1:
            tmp_bbox = BBox(
                *np.add(
                    self.tmp_p1,
                    [
                        0,
                        config.getfloat("LABEL", "STD_BOUNDINGBOX_WIDTH") / 2,
                        -config.getfloat("LABEL", "STD_BOUNDINGBOX_HEIGHT") / 3,
                    ],
                )
            )
            tmp_bbox.set_z_rotation(self.bbox_z_rotation)
            ogl.draw_cuboid(
                tmp_bbox.get_vertices(), draw_vertices=True, vertex_color=(1, 1, 0, 1)
            )

    # Draw bbox with fixed dimensions and rotation at x,y in world space
    def get_bbox(self) -> BBox:  # TODO: Refactor
        assert self.point_1 is not None
        final_bbox = BBox(
            *np.add(
                self.point_1,
                [
                    0,
                    config.getfloat("LABEL", "STD_BOUNDINGBOX_WIDTH") / 2,
                    -config.getfloat("LABEL", "STD_BOUNDINGBOX_HEIGHT") / 3,
                ],
            )
        )
        final_bbox.set_z_rotation(self.bbox_z_rotation)
        return final_bbox

    def reset(self) -> None:
        super().reset()
        self.tmp_p1 = None
        self.view.button_pick_bbox.setChecked(False)
