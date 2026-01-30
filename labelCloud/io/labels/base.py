import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Union

import numpy as np

from ...model import BBox
from .config import LabelConfig


class BaseLabelFormat(ABC):
    FILE_ENDING = ".json"

    def __init__(
        self, label_folder: Path, export_precision: int, relative_rotation: bool = False
    ) -> None:
        self.label_folder = label_folder
        logging.info("Set export strategy to %s." % self.__class__.__name__)
        self.export_precision = export_precision
        self.relative_rotation = relative_rotation
        self.file_ending = ".json"

        if relative_rotation:
            logging.info(
                "Saving rotations relatively to positve x-axis in radians (-pi..+pi)."
            )
        elif self.__class__.__name__ == "VerticesFormat":
            logging.info("Saving rotations implicitly in the vertices coordinates.")
        else:
            logging.info(
                "Saving rotations absolutely to positve x-axis in degrees (0..360°)."
            )

    def update_label_folder(self, new_label_folder: Path) -> None:
        self.label_folder = new_label_folder
        LabelConfig().load_config()
        logging.info(f"Updated label folder to {new_label_folder}.")

    def round_dec(self, x, decimal_places: Optional[int] = None) -> List[float]:
        if not decimal_places:
            decimal_places = self.export_precision
        return np.round(x, decimal_places).tolist()

    # Modified by Yiming Yang (Michigan Tech) for labelCloud-Enhanced
    # Changed: for better saving - force save and automated saving
    def save_label_to_file(
        self, 
        pcd_path: Path, 
        data: Union[dict, str], 
        force_overwrite: bool = False,  # New: Only overwrite if True
        backup: bool = True            # New: Save to backup folder if True
    ) -> Path:
        # Original file path
        label_path = self.label_folder.joinpath(pcd_path.stem + self.FILE_ENDING)
        
        # Backup folder logic
        if backup:
            autosave_dir = self.label_folder / "autosave"
            autosave_dir.mkdir(exist_ok=True)  # Create folder if missing
            backup_path = autosave_dir / f"{pcd_path.stem}_autosave{self.FILE_ENDING}"
            
            # Write to backup (silently)
            if label_path.suffix == ".json":
                with open(backup_path, "w") as f:
                    json.dump(data, f, indent="\t")
            elif label_path.suffix == ".txt" and isinstance(data, str):
                with open(backup_path, "w") as f:
                    f.write(data)
        
        # Only overwrite original if forced
        if force_overwrite:
            if label_path.is_file():
                logging.info(f"Overwriting original file: {label_path}")
            if label_path.suffix == ".json":
                with open(label_path, "w") as f:
                    json.dump(data, f, indent="\t")
            elif label_path.suffix == ".txt" and isinstance(data, str):
                with open(label_path, "w") as f:
                    f.write(data)
        
        return label_path  # Return original path (even if backup was used)

    @abstractmethod
    def import_labels(self, pcd_path: Path) -> List[BBox]:
        raise NotImplementedError

    @abstractmethod
    def export_labels(
        self, 
        bboxes: List[BBox], 
        pcd_path: Path, 
        force_overwrite: bool = False, 
        backup: bool = True
    ) -> None:
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
