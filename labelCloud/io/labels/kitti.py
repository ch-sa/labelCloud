import logging
import math
from pathlib import Path
from typing import List

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

    def import_labels(self, pcd_path: Path) -> List[BBox]:
        labels = []

        label_path = self.label_folder.joinpath(pcd_path.stem + self.FILE_ENDING)
        if label_path.is_file():
            with label_path.open("r") as read_file:
                label_lines = read_file.readlines()

            for line in label_lines:
                line_elements = line.split()
                centroid = tuple([float(v) for v in line_elements[11:14]])
                if self.transformed:
                    centroid = centroid[2], -centroid[0], centroid[1] - 2.3
                dimensions = tuple([float(v) for v in line_elements[8:11]])
                if self.transformed:
                    dimensions = dimensions[2], dimensions[1], dimensions[0]
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
