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

    def import_labels(self, pcd_path: Path) -> List[BBox]:
        labels = []

        label_path = self.label_folder.joinpath(pcd_path.stem + self.FILE_ENDING)
        calib_path = self.calib_folder.joinpath(pcd_path.stem + self.FILE_ENDING)
        if label_path.is_file():

            with label_path.open("r") as read_file:
                label_lines = read_file.readlines()

            for line in label_lines:
                line_elements = line.split()
                centroid = tuple([float(v) for v in line_elements[11:14]])
                dimensions = tuple([float(v) for v in line_elements[8:11]])
                if self.transformed:

                    if not calib_path.is_file():
                        logging.exception(
                            f"There is no calibration file for point cloud {pcd_path.name}."
                            " If you want to load labels in lidar frame without transformation"
                            " use the label format 'kitti_untransformed'."
                            " Skipping the loading of labels for this point cloud ..."
                        )
                        return []

                    T_c2l = self.calc_cam2lidar(calib_path)
                    xyz1 = np.insert(np.asarray(centroid), 3, values=[1])
                    xyz1 = T_c2l @ xyz1
                    centroid = tuple([float(n) for n in xyz1[:-1]])
                    dimensions = dimensions[2], dimensions[1], dimensions[0]
                    centroid = (
                        centroid[0],
                        centroid[1],
                        centroid[2] + dimensions[2] / 2,
                    )  # centroid in KITTI located on bottom face of bbox
                bbox = BBox(*centroid, *dimensions)
                if self.transformed:
                    bbox.set_rotations(
                        0, 0, rel2abs_rotation(-float(line_elements[14]) + math.pi / 2)
                    )
                else:
                    bbox.set_rotations(0, 0, rel2abs_rotation(float(line_elements[14])))
                bbox.set_classname(line_elements[0])
                labels.append(bbox)
            logging.info("Imported %s labels from %s." % (len(label_lines), label_path))
        return labels

    def export_labels(self, bboxes: List[BBox], pcd_path: Path) -> None:
        data = str()

        # Labels
        for bbox in bboxes:
            obj_type = bbox.get_classname()
            centroid = bbox.get_center()
            if self.transformed:
                centroid = (-centroid[1], centroid[2] + 2.3, centroid[0])
            location = " ".join([str(self.round_dec(v)) for v in centroid])
            dimensions = bbox.get_dimensions()
            if self.transformed:
                dimensions = (dimensions[2], dimensions[1], dimensions[0])
            dimensions_str = " ".join([str(self.round_dec(v)) for v in dimensions])
            rotation_z = bbox.get_z_rotation()
            if self.transformed:
                rotation_y = self.round_dec(
                    -(abs2rel_rotation(rotation_z) - math.pi / 2)
                )
            else:
                rotation_y = self.round_dec(abs2rel_rotation(rotation_z))

            data += (
                " ".join(
                    [
                        obj_type,
                        "0 0 0 0 0 0 0",
                        dimensions_str,
                        location,
                        str(rotation_y),
                    ]
                )
                + "\n"
            )

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

    def calc_cam2lidar(self, calib_path: Path):
        calib_dict = self._read_calib(calib_path)

        T_rect = calib_dict["R0_rect"]
        T_rect = T_rect.reshape(3, 3)
        T_rect = np.insert(T_rect, 3, values=[0, 0, 0], axis=0)
        T_rect = np.insert(T_rect, 3, values=[0, 0, 0, 1], axis=1)

        T_v2c = calib_dict["Tr_velo_to_cam"]
        T_v2c = T_v2c.reshape(3, 4)
        T_v2c = np.insert(T_v2c, 3, values=[0, 0, 0, 1], axis=0)

        T_c2v = np.linalg.inv(T_rect @ T_v2c)
        return T_c2v
