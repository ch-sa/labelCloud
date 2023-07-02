#
# Implementation according to:
# https://github.com/bostondiditeam/kitti/blob/master/resources/devkit_object/readme.txt
#


import logging
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import numpy.typing as npt

from ...control.config_manager import config
from ...model import BBox
from . import BaseLabelFormat, abs2rel_rotation, rel2abs_rotation


def _read_calibration_file(calib_path: Path) -> Dict[str, np.ndarray]:
    lines = []
    with open(calib_path, "r") as f:
        lines = f.readlines()
    calib_dict = {}
    for line in lines:
        vals = line.split()
        if not vals:
            continue
        calib_dict[vals[0][:-1]] = np.array(vals[1:]).astype(np.float64)
    return calib_dict


class CalibrationFileNotFound(Exception):
    def __init__(self, calib_path: Path, pcd_name: str) -> None:
        self.calib_path = calib_path
        self.pcd_name = pcd_name
        super().__init__(
            f"There is no calibration file at {self.calib_path.name} for point cloud"
            f" {self.pcd_name}. If you want to load labels in lidar frame without"
            " transformation use the label format 'kitti_untransformed'."
        )


TEMPLATE_META = {
    "type": "",
    "truncated": "0",
    "occluded": "0",
    "alpha": "0",
    "bbox": "0 0 0 0",
    "dimensions": "0 0 0",
    "location": "0 0 0",
    "rotation_y": "0",
}


class KittiFormat(BaseLabelFormat):
    FILE_ENDING = ".txt"

    def __init__(
        self,
        label_folder: Path,
        export_precision: int,
        relative_rotation: bool = False,
        transformed: bool = True,
    ) -> None:
        super().__init__(label_folder, export_precision, relative_rotation)
        self.transformed = transformed

        self.calib_folder = config.getpath("FILE", "calib_folder")
        self.T_v2c: Optional[npt.ArrayLike] = None
        self.T_c2v: Optional[npt.ArrayLike] = None

        self.bboxes_meta: Dict[int, Dict] = defaultdict(
            lambda: TEMPLATE_META
        )  # id: meta

    def import_labels(self, pcd_path: Path) -> List[BBox]:
        bboxes = []

        label_path = self.label_folder.joinpath(pcd_path.stem + self.FILE_ENDING)
        if label_path.is_file():
            with label_path.open("r") as read_file:
                label_lines = read_file.readlines()

            for line in label_lines:
                line_elements = line.split()
                meta = {
                    "type": line_elements[0],
                    "truncated": line_elements[1],
                    "occluded": line_elements[2],
                    "alpha": line_elements[3],
                    "bbox": " ".join(line_elements[4:8]),
                    "dimensions": " ".join(line_elements[8:11]),
                    "location": " ".join(line_elements[11:14]),
                    "rotation_y": line_elements[14],
                }

                centroid = tuple([float(v) for v in meta["location"].split()])

                height, width, length = tuple(
                    [float(v) for v in meta["dimensions"].split()]
                )

                if self.transformed:
                    try:
                        self._get_transforms(pcd_path)
                    except CalibrationFileNotFound as exc:
                        logging.exception("Calibration file not found")
                        logging.warning(
                            "Skipping loading of labels for this point cloud"
                        )
                        return []

                    xyz1 = np.insert(np.asarray(centroid), 3, values=[1])
                    xyz1 = self.T_c2v @ xyz1
                    centroid = tuple([float(n) for n in xyz1[:-1]])
                    centroid = (
                        centroid[0],
                        centroid[1],
                        centroid[2] + height / 2,
                    )  # centroid in KITTI located on bottom face of bbox

                bbox = BBox(*centroid, length, width, height)  # type: ignore
                self.bboxes_meta[id(bbox)] = meta

                rotation = (
                    -float(meta["rotation_y"]) + math.pi / 2
                    if self.transformed
                    else float(meta["rotation_y"])
                )

                bbox.set_rotations(0, 0, rel2abs_rotation(rotation))
                bbox.set_classname(meta["type"])
                bboxes.append(bbox)

            logging.info("Imported %s labels from %s." % (len(label_lines), label_path))
        return bboxes

    def export_labels(self, bboxes: List[BBox], pcd_path: Path) -> None:
        data = str()

        # Labels
        for bbox in bboxes:
            obj_type = bbox.get_classname()
            centroid = bbox.get_center()
            dimensions = bbox.get_dimensions()

            # invert sequence to height, width, length
            dimensions = dimensions[2], dimensions[1], dimensions[0]

            if self.transformed:
                try:
                    self._get_transforms(pcd_path)
                except CalibrationFileNotFound as exc:
                    logging.exception("Calibration file not found")
                    logging.warning("Skipping writing of labels for this point cloud")
                    return

                centroid = (
                    centroid[0],
                    centroid[1],
                    centroid[2] - dimensions[2] / 2,
                )  # centroid in KITTI located on bottom face of bbox
                xyz1 = np.insert(np.asarray(centroid), 3, values=[1])
                xyz1 = self.T_v2c @ xyz1
                centroid = tuple([float(n) for n in xyz1[:-1]])  # type: ignore

            rotation = bbox.get_z_rotation()
            rotation = abs2rel_rotation(rotation)
            rotation = -(rotation - math.pi / 2) if self.transformed else rotation
            rotation = str(self.round_dec(rotation))  # type: ignore

            location_str = " ".join([str(self.round_dec(v)) for v in centroid])
            dimensions_str = " ".join([str(self.round_dec(v)) for v in dimensions])

            out_str = list(self.bboxes_meta[id(bbox)].values())
            if obj_type != "DontCare":
                out_str[0] = obj_type
                out_str[5] = dimensions_str
                out_str[6] = location_str
                out_str[7] = rotation

            data += " ".join(out_str) + "\n"

        # Save to TXT
        path_to_file = self.save_label_to_file(pcd_path, data)
        logging.info(
            f"Exported {len(bboxes)} labels to {path_to_file} "
            f"in {self.__class__.__name__} formatting!"
        )
        self.T_v2c = None
        self.T_c2v = None

    # ---------------------------------------------------------------------------- #
    #                               Helper Functions                               #
    # ---------------------------------------------------------------------------- #

    def _get_transforms(self, pcd_path: Path) -> None:
        if self.T_v2c is None or self.T_c2v is None:
            calib_path = self.calib_folder.joinpath(pcd_path.stem + self.FILE_ENDING)

            if not calib_path.is_file():
                logging.exception(
                    " Skipping the loading of labels for this point cloud ..."
                )
                raise CalibrationFileNotFound(calib_path, pcd_path.name)

            calib_dict = _read_calibration_file(calib_path)

            T_rect = calib_dict["R0_rect"]
            T_rect = T_rect.reshape(3, 3)
            T_rect = np.insert(T_rect, 3, values=[0, 0, 0], axis=0)
            T_rect = np.insert(T_rect, 3, values=[0, 0, 0, 1], axis=1)

            T_v2c = calib_dict["Tr_velo_to_cam"]
            T_v2c = T_v2c.reshape(3, 4)
            T_v2c = np.insert(T_v2c, 3, values=[0, 0, 0, 1], axis=0)

            self.T_v2c = T_rect @ T_v2c
            self.T_c2v = np.linalg.inv(self.T_v2c)  # type: ignore
