import ntpath
import os
from typing import List

from ..label_formats import BaseLabelFormat, CentroidFormat, KittiFormat, VerticesFormat
from ..model.bbox import BBox
from .config_manager import config


def get_label_strategy(export_format: str, label_folder: str) -> "BaseLabelFormat":
    if export_format == "vertices":
        return VerticesFormat(label_folder, LabelManager.EXPORT_PRECISION)
    elif export_format == "centroid_rel":
        return CentroidFormat(
            label_folder, LabelManager.EXPORT_PRECISION, relative_rotation=True
        )
    elif export_format == "kitti":
        return KittiFormat(
            label_folder, LabelManager.EXPORT_PRECISION, relative_rotation=True
        )
    elif export_format == "kitti_untransformed":
        return KittiFormat(
            label_folder,
            LabelManager.EXPORT_PRECISION,
            relative_rotation=True,
            transformed=False,
        )
    elif export_format != "centroid_abs":
        print(
            f"Unknown export strategy '{export_format}'. Proceeding with default (centroid_abs)!"
        )
    return CentroidFormat(
        label_folder, LabelManager.EXPORT_PRECISION, relative_rotation=False
    )


class LabelManager(object):
    LABEL_FORMATS = [
        "vertices",
        "centroid_rel",
        "centroid_abs",
        "kitti",
    ]
    STD_LABEL_FORMAT = config.get("LABEL", "label_format")
    EXPORT_PRECISION = config.getint("LABEL", "export_precision")

    def __init__(
        self, strategy: str = STD_LABEL_FORMAT, path_to_label_folder: str = None
    ) -> None:
        self.label_folder = path_to_label_folder or config.get("FILE", "label_folder")
        if not os.path.isdir(self.label_folder):
            os.mkdir(self.label_folder)

        self.label_strategy = get_label_strategy(strategy, self.label_folder)

    def import_labels(self, pcd_name: str) -> List[BBox]:
        try:
            return self.label_strategy.import_labels(os.path.splitext(pcd_name)[0])
        except KeyError as key_error:
            print("Found a key error with %s in the dictionary." % key_error)
            print(
                "Could not import labels, please check the consistency of the label format."
            )
            return []
        except AttributeError as attribute_error:
            print("Attribute Error: %s. Expected a dictionary." % attribute_error)
            print(
                "Could not import labels, please check the consistency of the label format."
            )
            return []

    def export_labels(self, pcd_path: str, bboxes: List[BBox]) -> None:
        pcd_name = ntpath.basename(pcd_path)
        pcd_folder = os.path.dirname(pcd_path)
        self.label_strategy.export_labels(bboxes, pcd_name, pcd_folder, pcd_path)
