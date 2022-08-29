import logging
from typing import TYPE_CHECKING, List, Optional, cast

import numpy as np

from . import BaseLabelingStrategy
from ..control.config_manager import config
from ..definitions import Mode, Point3D
from ..model import BBox
from ..utils import math3d as math3d
from ..utils import oglhelper as ogl

if TYPE_CHECKING:
    from ..view.gui import GUI


class SpanningStrategy(BaseLabelingStrategy):
    POINTS_NEEDED = 4
    PREVIEW = True
    CORRECTION = False  # Increases dimensions after drawing

    def __init__(self, view: "GUI") -> None:
        super().__init__(view)
        logging.info("Enabled spanning mode.")
        self.view.status_manager.update_status(
            "Begin by selecting a vertex of the bounding box.", mode=Mode.DRAWING
        )
        self.preview_color = (1, 1, 0, 1)
        self.point_2: Optional[Point3D] = None  # second edge
        self.point_3: Optional[Point3D] = None  # width
        self.point_4: Optional[Point3D] = None  # height
        self.tmp_p2: Optional[Point3D] = None  # tmp points for preview
        self.tmp_p3: Optional[Point3D] = None
        self.tmp_p4: Optional[Point3D] = None
        self.p1_w: Optional[Point3D] = None  # p1 + dir_vector
        self.p2_w: Optional[Point3D] = None  # p2 + dir_vector
        self.dir_vector: Optional[Point3D] = None  # p1 + dir_vector

    def reset(self) -> None:
        super().reset()
        self.point_2, self.point_3, self.point_4 = (None, None, None)
        self.tmp_p2, self.tmp_p3, self.tmp_p4, self.p1_w, self.p2_w = (
            None,
            None,
            None,
            None,
            None,
        )
        self.view.button_span_bbox.setChecked(False)

    def register_point(self, new_point: Point3D) -> None:
        if self.point_1 is None:
            self.point_1 = new_point
            self.view.status_manager.set_message(
                "Select a point representing the length of the bounding box."
            )
        elif not self.point_2:
            self.point_2 = new_point
            self.view.status_manager.set_message(
                "Select any point for the depth of the bounding box."
            )
        elif not self.point_3:
            self.point_3 = new_point
            self.view.status_manager.set_message(
                "Select any point for the height of the bounding box."
            )
        elif not self.point_4:
            self.point_4 = new_point
        else:
            logging.warning("Cannot register point.")
        self.points_registered += 1

    def register_tmp_point(self, new_tmp_point: Point3D) -> None:
        if self.point_1 and (not self.point_2):
            self.tmp_p2 = new_tmp_point
        elif self.point_2 and (not self.point_3):
            self.tmp_p3 = new_tmp_point
        elif self.point_3:
            self.tmp_p4 = new_tmp_point

    def get_bbox(self) -> BBox:
        assert self.point_1 is not None and self.point_2 is not None
        length = math3d.vector_length(np.subtract(self.point_1, self.point_2))

        assert self.dir_vector is not None
        width = math3d.vector_length(self.dir_vector)

        assert self.point_4 is not None
        height = self.point_4[2] - self.point_1[2]  # can also be negative

        line_center = np.add(self.point_1, self.point_2) / 2
        area_center = np.add(line_center * 2, self.dir_vector) / 2
        center = np.add(area_center, [0, 0, height / 2])

        # Calculating z-rotation
        len_vec_2d = np.subtract(self.point_1, self.point_2)
        z_angle = np.arctan(len_vec_2d[1] / len_vec_2d[0])

        if SpanningStrategy.CORRECTION:
            length *= 1.1
            width *= 1.1
            height *= 1.1

        bbox = BBox(*center, length=length, width=width, height=abs(height))  # type: ignore
        bbox.set_z_rotation(math3d.radians_to_degrees(z_angle))

        if not config.getboolean("USER_INTERFACE", "z_rotation_only"):
            # Also calculate y_angle
            y_angle = np.arctan(len_vec_2d[2] / len_vec_2d[0])
            bbox.set_y_rotation(-math3d.radians_to_degrees(y_angle))
        return bbox

    def draw_preview(self) -> None:
        if not self.tmp_p4:
            if self.point_1:
                ogl.draw_points([self.point_1], color=self.preview_color)

            if self.point_1 and (self.point_2 or self.tmp_p2):
                if self.point_2:
                    self.tmp_p2 = self.point_2
                assert self.tmp_p2 is not None
                ogl.draw_points([self.tmp_p2], color=(1, 1, 0, 1))
                ogl.draw_lines([self.point_1, self.tmp_p2], color=self.preview_color)

            if self.point_1 and self.point_2 and (self.tmp_p3 or self.point_3):
                if self.point_3:
                    self.tmp_p3 = self.point_3
                assert self.tmp_p3 is not None
                # Get x-y-aligned vector from line to point with intersection
                self.dir_vector, _ = math3d.get_line_perpendicular(
                    self.point_1, self.point_2, self.tmp_p3
                )
                # Calculate projected vertices
                assert (
                    self.point_1 is not None
                    and self.point_2 is not None
                    and self.dir_vector is not None
                )
                self.p1_w = cast(Point3D, np.add(self.point_1, self.dir_vector))
                self.p2_w = cast(Point3D, np.add(self.point_2, self.dir_vector))
                ogl.draw_points([self.p1_w, self.p2_w], color=self.preview_color)
                ogl.draw_rectangles(
                    [self.point_1, self.point_2, self.p2_w, self.p1_w],
                    color=(1, 1, 0, 0.5),
                )

        elif (
            self.point_1
            and self.point_2
            and self.point_3
            and self.tmp_p4
            and (not self.point_4)
        ):
            assert self.p1_w is not None and self.p2_w is not None
            height1 = self.tmp_p4[2] - self.point_1[2]
            p1_t = cast(Point3D, np.add(self.point_1, [0, 0, height1]))
            p2_t = cast(Point3D, np.add(self.point_2, [0, 0, height1]))
            p1_wt = cast(Point3D, np.add(self.p1_w, [0, 0, height1]))
            p2_wt = cast(Point3D, np.add(self.p2_w, [0, 0, height1]))

            ogl.draw_cuboid(
                [
                    self.p1_w,
                    self.point_1,
                    self.point_2,
                    self.p2_w,
                    p1_wt,
                    p1_t,
                    p2_t,
                    p2_wt,
                ],
                color=(1, 1, 0, 0.5),
                draw_vertices=True,
                vertex_color=self.preview_color,
            )
