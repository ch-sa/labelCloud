from abc import ABCMeta, abstractmethod, ABC
from typing import Union, List, TYPE_CHECKING

import numpy as np

import utils.math3d as math3d
import utils.oglhelper as ogl
from model.bbox import BBox
from .bbox_controller import BoundingBoxController
from .config_manager import config

if TYPE_CHECKING:
    from view.gui import GUI


class DrawingManager:
    def __init__(self, bbox_controller: BoundingBoxController):
        self.bbox_controller = bbox_controller
        self.view: Union["GUI", None] = None
        self.drawing_strategy: Union[IDrawingStrategy, None] = None

    def set_view(self, view: "GUI"):
        self.view = view
        self.view.glWidget.drawing_mode = self

    def is_active(self) -> bool:
        return isinstance(self.drawing_strategy, IDrawingStrategy)

    def is_mode(self, mode: str = None) -> bool:
        if self.is_active():
            return self.drawing_strategy.__class__.__name__ == mode
        else:
            return False

    def has_preview(self) -> bool:
        if self.is_active():
            return self.drawing_strategy.__class__.PREVIEW

    def set_drawing_strategy(self, strategy: str) -> None:
        if self.is_active() and self.is_mode(strategy):
            self.reset()
            print("Deactivated drawing!")
        else:
            if self.is_active():
                self.reset()
                print("Resetted previous active drawing mode!")

            if strategy == "PickingStrategy":
                self.drawing_strategy = PickingStrategy(self.view)
                self.view.update_status(
                    "Please pick the location for the bounding box front center.",
                    mode="drawing",
                )
            elif strategy == "RectangleStrategy":
                self.drawing_strategy = RectangleStrategy(self.view)
                self.view.update_status(
                    "Please select a corner for the 2D bounding box.", mode="drawing"
                )
            elif strategy == "SpanStrategy":
                self.drawing_strategy = SpanStrategy(self.view)
                self.view.update_status(
                    "Begin by selecting a vertex of the bounding box.", mode="drawing"
                )

    def register_point(
        self, x, y, correction: bool = False, is_temporary: bool = False
    ) -> None:
        if self.is_mode("RectangleStrategy"):
            world_point = self.view.glWidget.get_world_coords(x, y, z=0)
        else:
            world_point = self.view.glWidget.get_world_coords(
                x, y, correction=correction
            )
        if is_temporary:
            self.drawing_strategy.register_tmp_point(world_point)
        else:
            self.drawing_strategy.register_point(world_point)
            if (
                self.drawing_strategy.is_bbox_finished()
            ):  # Register bbox to bbox controller when finished
                self.bbox_controller.add_bbox(self.drawing_strategy.get_bbox())
                self.drawing_strategy.reset()
                self.drawing_strategy = None

    def draw_preview(self) -> None:
        self.drawing_strategy.draw_preview()

    def reset(self, points_only: bool = False):
        if self.is_active():
            self.drawing_strategy.reset()
            if not points_only:
                self.drawing_strategy = None


class IDrawingStrategy:
    __metaclass__ = ABCMeta
    POINTS_NEEDED: int
    PREVIEW: bool = False

    def __init__(self, view: "GUI"):
        self.view = view
        self.points_registered = 0
        self.point_1 = None

    def is_bbox_finished(self) -> bool:
        return self.points_registered >= self.__class__.POINTS_NEEDED

    @abstractmethod
    def register_point(self, new_point: List[float]) -> None:
        raise NotImplementedError

    def register_tmp_point(self, new_tmp_point: List[float]) -> None:
        pass

    def register_scrolling(self, distance: float) -> None:
        pass

    @abstractmethod
    def get_bbox(self) -> BBox:
        raise NotImplementedError

    def draw_preview(self) -> None:
        pass

    def reset(self) -> None:
        self.points_registered = 0
        self.point_1 = None


class PickingStrategy(IDrawingStrategy, ABC):
    POINTS_NEEDED = 1
    PREVIEW = True

    def __init__(self, view: "GUI"):
        super().__init__(view)
        print("Enabled drawing mode.")
        self.tmp_p1 = None
        self.bbox_z_rotation = 0

    def register_point(self, new_point: List[float]) -> None:
        self.point_1 = new_point
        print("registered point " + str(self.point_1))
        self.points_registered += 1

    def register_tmp_point(self, new_tmp_point: List[float]) -> None:
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
        self.view.button_activate_picking.setChecked(False)


class SpanStrategy(IDrawingStrategy, ABC):
    POINTS_NEEDED = 4
    PREVIEW = True
    CORRECTION = False  # Increases dimensions after drawing

    def __init__(self, view: "GUI"):
        super().__init__(view)
        print("Enabled spanning mode.")
        self.preview_color = (1, 1, 0, 1)
        self.point_2 = None  # second edge
        self.point_3 = None  # width
        self.point_4 = None  # height
        self.tmp_p2 = None  # tmp points for preview
        self.tmp_p3 = None
        self.tmp_p4 = None
        self.p1_w = None  # p1 + dir_vector
        self.p2_w = None  # p2 + dir_vector
        self.dir_vector = None  # p1 + dir_vector

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
        self.view.button_activate_spanning.setChecked(False)

    def register_point(self, new_point: List[float]) -> None:
        if self.point_1 is None:
            self.point_1 = new_point
            self.view.update_status(
                "Select a point representing the length of the bounding box."
            )
        elif not self.point_2:
            self.point_2 = new_point
            self.view.update_status(
                "Select any point for the depth of the bounding box."
            )
        elif not self.point_3:
            self.point_3 = new_point
            self.view.update_status(
                "Select any point for the height of the bounding box."
            )
        elif not self.point_4:
            self.point_4 = new_point
        else:
            print("Cannot register point.")
        self.points_registered += 1

    def register_tmp_point(self, new_tmp_point: List[float]) -> None:
        if self.point_1 and (not self.point_2):
            self.tmp_p2 = new_tmp_point
        elif self.point_2 and (not self.point_3):
            self.tmp_p3 = new_tmp_point
        elif self.point_3:
            self.tmp_p4 = new_tmp_point

    def get_bbox(self) -> BBox:
        length = math3d.vector_length(np.subtract(self.point_1, self.point_2))
        width = math3d.vector_length(self.dir_vector)
        height = self.point_4[2] - self.point_1[2]  # can also be negative

        line_center = np.add(self.point_1, self.point_2) / 2
        area_center = np.add(line_center * 2, self.dir_vector) / 2
        center = np.add(area_center, [0, 0, height / 2])

        # Calculating z-rotation
        len_vec_2d = np.subtract(self.point_1, self.point_2)
        z_angle = np.arctan(len_vec_2d[1] / len_vec_2d[0])

        if SpanStrategy.CORRECTION:
            length *= 1.1
            width *= 1.1
            height *= 1.1

        bbox = BBox(*center, length=length, width=width, height=abs(height))
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
                ogl.draw_points([self.tmp_p2], color=(1, 1, 0, 1))
                ogl.draw_lines([self.point_1, self.tmp_p2], color=self.preview_color)

            if self.point_1 and self.point_2 and (self.tmp_p3 or self.point_3):
                if self.point_3:
                    self.tmp_p3 = self.point_3
                # Get x-y-aligned vector from line to point with intersection
                self.dir_vector, intersection = math3d.get_line_perpendicular(
                    self.point_1, self.point_2, self.tmp_p3
                )
                # Calculate projected vertices
                self.p1_w = np.add(self.point_1, self.dir_vector)
                self.p2_w = np.add(self.point_2, self.dir_vector)
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
            height1 = self.tmp_p4[2] - self.point_1[2]
            p1_t = np.add(self.point_1, [0, 0, height1])
            p2_t = np.add(self.point_2, [0, 0, height1])
            p1_wt = np.add(self.p1_w, [0, 0, height1])
            p2_wt = np.add(self.p2_w, [0, 0, height1])

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


class RectangleStrategy(IDrawingStrategy, ABC):
    POINTS_NEEDED = 3
    PREVIEW = True

    def __init__(self, view: "GUI"):
        super().__init__(view)
        self.point_2 = None
        self.tmp_p2 = None

    def register_point(self, new_point: List[float]):
        if self.point_1 is None:
            self.point_1 = new_point
            self.view.update_status("Select the opposing point of the 2D bounding box.")
        elif not self.point_2:
            self.point_2 = new_point
        else:
            print("Cannot register point.")
        self.points_registered += 1

    def register_tmp_point(self, new_tmp_point: List[float]):
        if self.point_1 and (not self.point_2):
            self.tmp_p2 = new_tmp_point

    def get_bbox(self):
        # self.view.controller.pcd_manager.
        pass

    def draw_preview(self):
        if self.point_1:
            ogl.draw_points([self.point_1])
        if self.point_2 or self.tmp_p2:
            if self.point_2:
                self.tmp_p2 = self.point_2
            bottom_left = [self.point_1[0], self.tmp_p2[1], self.point_1[2]]
            top_right = [self.tmp_p2[0], self.point_1[1], self.tmp_p2[2]]

            ogl.draw_rectangles([self.point_1, bottom_left, self.tmp_p2, top_right])

    def reset(self) -> None:
        super().reset()
        self.point_2, self.tmp_p2 = (None, None)
        self.view.button_activate_drag.setChecked(False)
