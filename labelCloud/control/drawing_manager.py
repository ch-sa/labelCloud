import logging
from typing import TYPE_CHECKING, Union

from ..labeling_strategies import BaseLabelingStrategy
from .bbox_controller import BoundingBoxController

if TYPE_CHECKING:
    from ..view.gui import GUI


class DrawingManager(object):
    def __init__(self, bbox_controller: BoundingBoxController) -> None:
        self.bbox_controller = bbox_controller
        self.view: Union["GUI", None] = None
        self.drawing_strategy: Union[BaseLabelingStrategy, None] = None

    def set_view(self, view: "GUI") -> None:
        self.view = view
        self.view.glWidget.drawing_mode = self

    def is_active(self) -> bool:
        return isinstance(self.drawing_strategy, BaseLabelingStrategy)

    def has_preview(self) -> bool:
        if self.is_active():
            return self.drawing_strategy.__class__.PREVIEW

    def set_drawing_strategy(self, strategy: BaseLabelingStrategy) -> None:
        if self.is_active() and self.drawing_strategy == strategy:
            self.reset()
            logging.info("Deactivated drawing!")
        else:
            if self.is_active():
                self.reset()
                logging.info("Resetted previous active drawing mode!")

            self.drawing_strategy = strategy

    def register_point(
        self, x, y, correction: bool = False, is_temporary: bool = False
    ) -> None:
        world_point = self.view.glWidget.get_world_coords(x, y, correction=correction)
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

    def reset(self, points_only: bool = False) -> None:
        if self.is_active():
            self.drawing_strategy.reset()
            if not points_only:
                self.drawing_strategy = None
