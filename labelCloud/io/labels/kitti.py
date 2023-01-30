import logging
import math
from pathlib import Path
from typing import Dict, List

import numpy as np

from ...control.config_manager import config
from ...model import BBox
from . import BaseLabelFormat, abs2rel_rotation, rel2abs_rotation


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
        self.bboxes_meta: List[Dict] = []

    def import_labels(self, pcd_path: Path) -> List[BBox]:
        bboxes = []
        self.bboxes_meta = []

        label_path = self.label_folder.joinpath(pcd_path.stem + self.FILE_ENDING)
        calib_path = self.calib_folder.joinpath(pcd_path.stem + self.FILE_ENDING)
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
                self.bboxes_meta.append(meta)
                centroid = tuple([float(v) for v in meta["location"].split()])
                dimensions = tuple([float(v) for v in meta["dimensions"].split()])
                if self.transformed:
                    if not calib_path.is_file():
                        logging.exception(
                            f"There is no calibration file for point cloud {pcd_path.name}."
                            " If you want to load labels in lidar frame without transformation"
                            " use the label format 'kitti_untransformed'."
                            " Skipping the loading of labels for this point cloud ..."
                        )
                        return []

                    self._calc_transforms(calib_path)
                    xyz1 = np.insert(np.asarray(centroid), 3, values=[1])
                    xyz1 = self.T_c2v @ xyz1
                    centroid = tuple([float(n) for n in xyz1[:-1]])
                    dimensions = dimensions[2], dimensions[1], dimensions[0]
                    centroid = (
                        centroid[0],
                        centroid[1],
                        centroid[2] + dimensions[2] / 2,
                    )  # centroid in KITTI located on bottom face of bbox
                bbox = BBox(*centroid, *dimensions)
                rotation = -float(meta["rotation_y"]) + math.pi / 2 if self.transformed else float(meta["rotation_y"])
                bbox.set_rotations(0, 0, rel2abs_rotation(rotation))
                bbox.set_classname(meta["type"])
                bboxes.append(bbox)
            logging.info("Imported %s labels from %s." % (len(label_lines), label_path))
        return bboxes

    def export_labels(self, bboxes: List[BBox], pcd_path: Path) -> None:
        data = str()

        # Labels
        for i, bbox in enumerate(bboxes):
            obj_type = bbox.get_classname()
            centroid = bbox.get_center()
            dimensions = bbox.get_dimensions()
            if self.transformed:
                centroid = (
                    centroid[0],
                    centroid[1],
                    centroid[2] - dimensions[2] / 2,
                )  # centroid in KITTI located on bottom face of bbox
                dimensions = dimensions[2], dimensions[1], dimensions[0]
                xyz1 = np.insert(np.asarray(centroid), 3, values=[1])
                xyz1 = self.T_v2c @ xyz1
                centroid = tuple([float(n) for n in xyz1[:-1]])
            location_str = " ".join([str(self.round_dec(v)) for v in centroid])
            dimensions_str = " ".join([str(self.round_dec(v)) for v in dimensions])
            rotation = bbox.get_z_rotation()
            rotation = abs2rel_rotation(rotation)
            rotation = -(rotation - math.pi / 2) if self.transformed else rotation
            rotation = str(self.round_dec(rotation))

            out_str = list(self.bboxes_meta[i].values())
            if obj_type != "DontCare":
                out_str[5] = dimensions_str
                out_str[6] = location_str
                out_str[7] = rotation

            data += (" ".join(out_str) + "\n")

        # Save to TXT
        path_to_file = self.save_label_to_file(pcd_path, data)
        logging.info(
            f"Exported {len(bboxes)} labels to {path_to_file} "
            f"in {self.__class__.__name__} formatting!"
        )

    # ---------------------------------------------------------------------------- #
    #                               Helper Functions                               #
    # ---------------------------------------------------------------------------- #

    def _read_calib(self, calib_path: Path) -> Dict[str, np.ndarray]:
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

    def _calc_transforms(self, calib_path: Path) -> None:
        calib_dict = self._read_calib(calib_path)

        T_rect = calib_dict["R0_rect"]
        T_rect = T_rect.reshape(3, 3)
        T_rect = np.insert(T_rect, 3, values=[0, 0, 0], axis=0)
        T_rect = np.insert(T_rect, 3, values=[0, 0, 0, 1], axis=1)

        T_v2c = calib_dict["Tr_velo_to_cam"]
        T_v2c = T_v2c.reshape(3, 4)
        T_v2c = np.insert(T_v2c, 3, values=[0, 0, 0, 1], axis=0)

        self.T_v2c = T_rect @ T_v2c
        self.T_c2v = np.linalg.inv(self.T_v2c)
