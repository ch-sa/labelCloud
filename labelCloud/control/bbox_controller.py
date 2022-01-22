"""
A class to handle all user manipulations of the bounding boxes and collect all labeling
settings in one place.
Bounding Box Management: adding, selecting updating, deleting bboxes;
Possible Active Bounding Box Manipulations: rotation, translation, scaling
"""
import logging
from typing import TYPE_CHECKING, List, Optional

import numpy as np

from ..model.bbox import BBox
from ..utils import oglhelper
from .config_manager import config

if TYPE_CHECKING:
    from ..view.gui import GUI


# DECORATORS
def has_active_bbox_decorator(func):
    """
    Only execute bounding box manipulation if there is an active bounding box.
    """

    def wrapper(*args, **kwargs):
        if args[0].has_active_bbox():
            return func(*args, **kwargs)
        else:
            logging.warning("There is currently no active bounding box to manipulate.")

    return wrapper


def only_zrotation_decorator(func):
    """
    Only execute x- and y-rotation if z_rotation_only mode is not activated.
    """

    def wrapper(*args, **kwargs):
        if not config.getboolean("USER_INTERFACE", "z_rotation_only"):
            return func(*args, **kwargs)
        else:
            logging.warning(
                "Rotations around the x- or y-axis are not supported in this mode."
            )

    return wrapper


class BoundingBoxController(object):
    STD_SCALING = config.getfloat("LABEL", "std_scaling")

    def __init__(self) -> None:
        self.view = None
        self.bboxes = []
        self.active_bbox_id = -1  # -1 means zero bboxes
        self.pcdc = None

    # GETTERS
    def has_active_bbox(self) -> bool:
        return 0 <= self.active_bbox_id < len(self.bboxes)

    def get_active_bbox(self) -> Optional[BBox]:
        if self.has_active_bbox():
            return self.bboxes[self.active_bbox_id]
        else:
            return None

    @has_active_bbox_decorator
    def get_classname(self) -> str:
        return self.get_active_bbox().get_classname()

    # SETTERS

    def set_view(self, view: "GUI") -> None:
        self.view = view

    def add_bbox(self, bbox: BBox) -> None:
        if isinstance(bbox, BBox):
            self.bboxes.append(bbox)
            self.set_active_bbox(self.bboxes.index(bbox))
            self.view.update_status(
                "Bounding Box added, it can now be corrected.", mode="correction"
            )

    def update_bbox(self, bbox_id: int, bbox: BBox) -> None:
        if isinstance(bbox, BBox) and (0 <= bbox_id < len(self.bboxes)):
            self.bboxes[bbox_id] = bbox
            self.update_label_list()

    def delete_bbox(self, bbox_id: int) -> None:
        if 0 <= bbox_id < len(self.bboxes):
            del self.bboxes[bbox_id]
            if bbox_id == self.active_bbox_id:
                self.set_active_bbox(len(self.bboxes) - 1)
            else:
                self.update_label_list()

    def delete_current_bbox(self) -> None:
        selected_item_id = self.view.label_list.currentRow()
        self.delete_bbox(selected_item_id)

    def set_active_bbox(self, bbox_id: int) -> None:
        if 0 <= bbox_id < len(self.bboxes):
            self.active_bbox_id = bbox_id
            self.update_all()
            self.view.update_status(
                "Bounding Box selected, it can now be corrected.", mode="correction"
            )
        else:
            self.deselect_bbox()

    @has_active_bbox_decorator
    def set_classname(self, new_class: str) -> None:
        self.get_active_bbox().set_classname(new_class)
        self.update_label_list()

    @has_active_bbox_decorator
    def set_center(self, cx: float, cy: float, cz: float) -> None:
        self.get_active_bbox().center = (cx, cy, cz)

    def set_bboxes(self, bboxes: List[BBox]) -> None:
        self.bboxes = bboxes
        self.deselect_bbox()
        self.update_label_list()

    def reset(self) -> None:
        self.deselect_bbox()
        self.set_bboxes([])

    def deselect_bbox(self) -> None:
        self.active_bbox_id = -1
        self.update_all()
        self.view.update_status("", mode="navigation")

    # MANIPULATORS
    @has_active_bbox_decorator
    def update_position(self, axis: str, value: float) -> None:
        if axis == "pos_x":
            self.get_active_bbox().set_x_translation(value)
        elif axis == "pos_y":
            self.get_active_bbox().set_y_translation(value)
        elif axis == "pos_z":
            self.get_active_bbox().set_z_translation(value)
        else:
            raise Exception("Wrong axis describtion.")

    @has_active_bbox_decorator
    def update_dimension(self, dimension: str, value: float) -> None:
        if dimension == "length":
            self.get_active_bbox().set_length(value)
        elif dimension == "width":
            self.get_active_bbox().set_width(value)
        elif dimension == "height":
            self.get_active_bbox().set_height(value)
        else:
            raise Exception("Wrong dimension describtion.")

    @has_active_bbox_decorator
    def update_rotation(self, axis: str, value: float) -> None:
        if axis == "rot_x":
            self.get_active_bbox().set_x_rotation(value)
        elif axis == "rot_y":
            self.get_active_bbox().set_y_rotation(value)
        elif axis == "rot_z":
            self.get_active_bbox().set_z_rotation(value)
        else:
            raise Exception("Wrong axis describtion.")

    @only_zrotation_decorator
    @has_active_bbox_decorator
    def rotate_around_x(self, dangle: float = None, clockwise: bool = False) -> None:
        dangle = dangle or config.getfloat("LABEL", "std_rotation")
        if clockwise:
            dangle *= -1
        self.get_active_bbox().set_x_rotation(
            self.get_active_bbox().get_x_rotation() + dangle
        )

    @only_zrotation_decorator
    @has_active_bbox_decorator
    def rotate_around_y(self, dangle: float = None, clockwise: bool = False) -> None:
        dangle = dangle or config.getfloat("LABEL", "std_rotation")
        if clockwise:
            dangle *= -1
        self.get_active_bbox().set_y_rotation(
            self.get_active_bbox().get_y_rotation() + dangle
        )

    @has_active_bbox_decorator
    def rotate_around_z(
        self, dangle: float = None, clockwise: bool = False, absolute: bool = False
    ) -> None:
        dangle = dangle or config.getfloat("LABEL", "std_rotation")
        if clockwise:
            dangle *= -1
        if absolute:
            self.get_active_bbox().set_z_rotation(dangle)
        else:
            self.get_active_bbox().set_z_rotation(
                self.get_active_bbox().get_z_rotation() + dangle
            )
        self.update_all()

    @has_active_bbox_decorator
    def rotate_with_mouse(
        self, x_angle: float, y_angle: float
    ) -> None:  # TODO: Make more intuitive
        # Get bbox perspective
        pcd_z_rotation = self.pcdc.get_pointcloud().rot_z
        bbox_z_rotation = self.get_active_bbox().get_z_rotation()
        total_z_rotation = pcd_z_rotation + bbox_z_rotation

        bbox_cosz = round(np.cos(np.deg2rad(total_z_rotation)), 0)
        bbox_sinz = -round(np.sin(np.deg2rad(total_z_rotation)), 0)

        self.rotate_around_x(y_angle * bbox_cosz)
        self.rotate_around_y(y_angle * bbox_sinz)
        self.rotate_around_z(x_angle)

    @has_active_bbox_decorator
    def translate_along_x(self, distance: float = None, left: bool = False) -> None:
        distance = distance or config.getfloat("LABEL", "std_translation")
        if left:
            distance *= -1
        cosz, sinz, bu = self.pcdc.get_perspective()
        self.get_active_bbox().set_x_translation(
            self.get_active_bbox().center[0] + distance * cosz
        )
        self.get_active_bbox().set_y_translation(
            self.get_active_bbox().center[1] + distance * sinz
        )

    @has_active_bbox_decorator
    def translate_along_y(self, distance: float = None, forward: bool = False) -> None:
        distance = distance or config.getfloat("LABEL", "std_translation")
        if forward:
            distance *= -1
        cosz, sinz, bu = self.pcdc.get_perspective()
        self.get_active_bbox().set_x_translation(
            self.get_active_bbox().center[0] + distance * bu * -sinz
        )
        self.get_active_bbox().set_y_translation(
            self.get_active_bbox().center[1] + distance * bu * cosz
        )

    @has_active_bbox_decorator
    def translate_along_z(self, distance: float = None, down: bool = False) -> None:
        distance = distance or config.getfloat("LABEL", "std_translation")
        if down:
            distance *= -1
        self.get_active_bbox().set_z_translation(
            self.get_active_bbox().center[2] + distance
        )

    @has_active_bbox_decorator
    def scale(self, length_increase: float = None, decrease: bool = False) -> None:
        """Scales a bounding box while keeping the previous aspect ratio.

        :param length_increase: factor by which the length should be increased
        :param decrease: if True, reverses the length_increasee (* -1)
        :return: None
        """
        length_increase = length_increase or config.getfloat("LABEL", "std_scaling")
        if decrease:
            length_increase *= -1
        length, width, height = self.get_active_bbox().get_dimensions()
        width_length_ratio = width / length
        height_length_ratio = height / length

        new_length = length + length_increase
        new_width = new_length * width_length_ratio
        new_height = new_length * height_length_ratio

        self.get_active_bbox().set_dimensions(new_length, new_width, new_height)

    def select_bbox_by_ray(self, x: int, y: int) -> None:
        intersected_bbox_id = oglhelper.get_intersected_bboxes(
            x,
            y,
            self.bboxes,
            self.view.glWidget.modelview,
            self.view.glWidget.projection,
        )
        if intersected_bbox_id is not None:
            self.set_active_bbox(intersected_bbox_id)
            logging.info("Selected bounding box %s." % intersected_bbox_id)

    # HELPER

    def update_all(self) -> None:
        self.update_z_dial()
        self.update_curr_class()
        self.update_label_list()
        self.view.update_bbox_stats(self.get_active_bbox())

    @has_active_bbox_decorator
    def update_z_dial(self) -> None:
        self.view.dial_zrotation.blockSignals(True)  # To brake signal loop
        self.view.dial_zrotation.setValue(int(self.get_active_bbox().get_z_rotation()))
        self.view.dial_zrotation.blockSignals(False)

    def update_curr_class(self) -> None:
        if self.has_active_bbox():
            self.view.update_curr_class_edit()
        else:
            self.view.update_curr_class_edit(force="")

    def update_label_list(self) -> None:
        """Updates the list of drawn labels and highlights the active label.

        Should be always called if the bounding boxes changed.
        :return: None
        """
        self.view.label_list.blockSignals(True)  # To brake signal loop
        self.view.label_list.clear()
        for bbox in self.bboxes:
            self.view.label_list.addItem(bbox.get_classname())
        if self.has_active_bbox():
            self.view.label_list.setCurrentRow(self.active_bbox_id)
            self.view.label_list.currentItem().setSelected(True)
        self.view.label_list.blockSignals(False)
