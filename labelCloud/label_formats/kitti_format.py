import os
from typing import List

from model import BBox

from . import BaseLabelFormat, abs2rel_rotation, rel2abs_rotation


class KittiFormat(BaseLabelFormat):
    FILE_ENDING = ".txt"

    def import_labels(self, pcd_name_stripped) -> List[BBox]:
        labels = []
        path_to_label = os.path.join(self.label_folder, pcd_name_stripped + ".txt")
        if os.path.isfile(path_to_label):
            with open(path_to_label, "r") as read_file:
                label_lines = read_file.readlines()

            for line in label_lines:
                line_elements = line.split()
                centroid = [float(v) for v in line_elements[11:14]]
                dimensions = [float(v) for v in line_elements[8:11]]
                bbox = BBox(*centroid, *dimensions)
                bbox.set_rotations(0, 0, rel2abs_rotation(float(line_elements[14])))
                bbox.set_classname(line_elements[0])
                labels.append(bbox)
            print("Imported %s labels from %s." % (len(label_lines), path_to_label))
        return labels

    def export_labels(
        self, bboxes: List[BBox], pcd_name: str, pcd_folder: str, pcd_path: str
    ) -> None:
        data = str()

        # Labels
        for bbox in bboxes:
            obj_type = bbox.get_classname()
            location = " ".join([str(self.round_dec(v)) for v in bbox.get_center()])
            dimensions = " ".join(
                [str(self.round_dec(v)) for v in bbox.get_dimensions()]
            )
            rotation_y = self.round_dec(abs2rel_rotation(bbox.get_z_rotation()))

            data += (
                " ".join(
                    [obj_type, "0 0 0 0 0 0 0", dimensions, location, str(rotation_y)]
                )
                + "\n"
            )

        # Save to TXT
        path_to_file = self.save_label_to_file(pcd_name, data)
        print(
            f"Exported {len(bboxes)} labels to {path_to_file} "
            f"in {self.__class__.__name__} formatting!"
        )
