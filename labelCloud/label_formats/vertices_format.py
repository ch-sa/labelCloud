import json
import os
from typing import List

import numpy as np

from ..model import BBox
from ..utils import math3d
from . import BaseLabelFormat


class VerticesFormat(BaseLabelFormat):
    FILE_ENDING = ".json"

    def import_labels(self, pcd_name_stripped) -> List[BBox]:
        labels = []
        path_to_label = os.path.join(self.label_folder, pcd_name_stripped + ".json")

        if os.path.isfile(path_to_label):
            with open(path_to_label, "r") as read_file:
                data = json.load(read_file)

            for label in data["objects"]:
                vertices = label["vertices"]

                # Calculate centroid
                centroid = np.add(
                    np.subtract(vertices[4], vertices[2]) / 2, vertices[2]
                )

                # Calculate dimensions
                length = math3d.vector_length(np.subtract(vertices[0], vertices[3]))
                width = math3d.vector_length(np.subtract(vertices[0], vertices[1]))
                height = math3d.vector_length(np.subtract(vertices[0], vertices[4]))

                # Calculate rotations
                rotations = math3d.vertices2rotations(vertices, centroid)

                bbox = BBox(*centroid, length, width, height)
                bbox.set_rotations(*rotations)
                bbox.set_classname(label["name"])
                labels.append(bbox)
            print("Imported %s labels from %s." % (len(data["objects"]), path_to_label))
        return labels

    def export_labels(self, bboxes, pcd_name, pcd_folder, pcd_path) -> None:
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
            label["vertices"] = self.round_dec(
                bbox.get_vertices().tolist()
            )  # ToDo: Add option for axis-aligned vertices
            data["objects"].append(label)

        # Save to JSON
        path_to_file = self.save_label_to_file(pcd_name, data)
        print(
            f"Exported {len(bboxes)} labels to {path_to_file} "
            f"in {self.__class__.__name__} formatting!"
        )
