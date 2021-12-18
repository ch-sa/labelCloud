import json
import os
from abc import ABC, abstractmethod
from typing import List, Optional, Union

import numpy as np

from ..model import BBox


class BaseLabelFormat(ABC):
    FILE_ENDING = ".json"

    def __init__(self, label_folder, export_precision, relative_rotation=False) -> None:
        self.label_folder = label_folder
        print("Set export strategy to %s." % self.__class__.__name__)
        self.export_precision = export_precision
        self.relative_rotation = relative_rotation
        self.file_ending = ".json"
        if relative_rotation:
            print(
                "Saving rotations relatively to positve x-axis in radians (-pi..+pi)."
            )
        elif self.__class__.__name__ == "VerticesFormat":
            print("Saving rotations implicitly in the vertices coordinates.")
        else:
            print("Saving rotations absolutely to positve x-axis in degrees (0..360°).")

    def update_label_folder(self, new_label_folder) -> None:
        self.label_folder = new_label_folder

    def round_dec(self, x, decimal_places: Optional[int] = None) -> List[float]:
        if not decimal_places:
            decimal_places = self.export_precision
        return np.round(x, decimal_places).tolist()

    def save_label_to_file(self, pcd_name: str, data: Union[dict, str]) -> str:
        path_to_file = os.path.join(
            self.label_folder, os.path.splitext(pcd_name)[0] + self.FILE_ENDING
        )

        if os.path.isfile(path_to_file):
            print("File %s already exists, replacing file ..." % path_to_file)
        if os.path.splitext(path_to_file)[1] == ".json":
            with open(path_to_file, "w") as write_file:
                json.dump(data, write_file, indent="\t")
        else:
            with open(path_to_file, "w") as write_file:
                write_file.write(data)
        return path_to_file

    @abstractmethod
    def import_labels(self, pcd_name_stripped) -> List[BBox]:
        raise NotImplementedError

    @abstractmethod
    def export_labels(self, bboxes, pcd_name, pcd_folder, pcd_path) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------- #
#                               Helper Functions                               #
# ---------------------------------------------------------------------------- #


def abs2rel_rotation(abs_rotation: float) -> float:
    """Convert absolute rotation 0..360° into -pi..+pi from x-Axis.

    :param abs_rotation: Counterclockwise rotation from x-axis around z-axis
    :return: Relative rotation from x-axis around z-axis
    """
    rel_rotation = np.deg2rad(abs_rotation)
    if rel_rotation > np.pi:
        rel_rotation = rel_rotation - 2 * np.pi
    return rel_rotation


def rel2abs_rotation(rel_rotation: float) -> float:
    """Convert relative rotation from -pi..+pi into 0..360° from x-Axis.

    :param rel_rotation: Rotation from x-axis around z-axis
    :return: Counterclockwise rotation from x-axis around z-axis
    """
    abs_rotation = np.rad2deg(rel_rotation)
    if abs_rotation < 0:
        abs_rotation = abs_rotation + 360
    return abs_rotation
