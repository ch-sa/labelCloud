import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from . import BaseLabelFormat
from ...definitions import Point3D
from ...model import BBox
from ...utils import math3d


class VerticesFormat(BaseLabelFormat):
    FILE_ENDING = ".json"

    def import_labels(self, pcd_path: Path) -> List[BBox]:
        labels = []

        label_path = self.label_folder.joinpath(pcd_path.stem + self.FILE_ENDING)
        if label_path.is_file():
            with label_path.open("r") as read_file:
                data = json.load(read_file)

            for label in data["objects"]:
                vertices = label["vertices"]

                # Calculate centroid
                centroid: Point3D = tuple(  # type: ignore
                    np.add(np.subtract(vertices[4], vertices[2]) / 2, vertices[2])
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
            logging.info(
                "Imported %s labels from %s." % (len(data["objects"]), label_path)
            )
        return labels

    def export_labels(self, bboxes: List[BBox], pcd_path: Path) -> None:
        data: Dict[str, Any] = dict()
        # Header
        data["folder"] = pcd_path.parent.name
        data["filename"] = pcd_path.name
        data["path"] = str(pcd_path)

        # Labels
        data["objects"] = []
        for bbox in bboxes:
            label: Dict[str, Any] = dict()
            label["name"] = bbox.get_classname()
            label["vertices"] = self.round_dec(
                bbox.get_vertices().tolist()
            )  # TODO: Add option for axis-aligned vertices
            data["objects"].append(label)

        # Save to JSON
        label_path = self.save_label_to_file(pcd_path, data)
        logging.info(
            f"Exported {len(bboxes)} labels to {label_path} "
            f"in {self.__class__.__name__} formatting!"
        )
