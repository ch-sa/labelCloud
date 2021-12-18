import json
import os
from typing import List

from ..model import BBox
from . import BaseLabelFormat, abs2rel_rotation, rel2abs_rotation


class CentroidFormat(BaseLabelFormat):
    FILE_ENDING = ".json"

    def import_labels(self, pcd_name_stripped) -> List[BBox]:
        labels = []
        path_to_label = os.path.join(self.label_folder, pcd_name_stripped + ".json")
        if os.path.isfile(path_to_label):
            with open(path_to_label, "r") as read_file:
                data = json.load(read_file)

            for label in data["objects"]:
                bbox = BBox(*label["centroid"].values(), *label["dimensions"].values())
                rotations = label["rotations"].values()
                if self.relative_rotation:
                    rotations = map(rel2abs_rotation, rotations)
                bbox.set_rotations(*rotations)
                bbox.set_classname(label["name"])
                labels.append(bbox)
            print("Imported %s labels from %s." % (len(data["objects"]), path_to_label))
        return labels

    def export_labels(
        self, bboxes: List[BBox], pcd_name: str, pcd_folder: str, pcd_path: str
    ) -> None:
        data = dict()
        # Header
        data["folder"] = pcd_folder
        data["filename"] = pcd_name
        data["path"] = pcd_path

        # Labels
        data["objects"] = []
        for bbox in bboxes:
            label = dict()
            label["name"] = bbox.get_classname()
            label["centroid"] = {
                str(axis): self.round_dec(val)
                for axis, val in zip(["x", "y", "z"], bbox.get_center())
            }
            label["dimensions"] = {
                str(dim): self.round_dec(val)
                for dim, val in zip(
                    ["length", "width", "height"], bbox.get_dimensions()
                )
            }
            conv_rotations = bbox.get_rotations()
            if self.relative_rotation:
                conv_rotations = map(abs2rel_rotation, conv_rotations)

            label["rotations"] = {
                str(axis): self.round_dec(angle)
                for axis, angle in zip(["x", "y", "z"], conv_rotations)
            }
            data["objects"].append(label)

        # Save to JSON
        path_to_file = self.save_label_to_file(pcd_name, data)
        print(
            f"Exported {len(bboxes)} labels to {path_to_file} "
            f"in {self.__class__.__name__} formatting!"
        )
