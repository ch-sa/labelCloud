import json
import ntpath
import os
from abc import ABCMeta, abstractmethod, ABC
from typing import List

import numpy as np

from modules import math3d
from modules.control import config_parser
from modules.model.bbox import BBox


class LabelManager:
    LABEL_FORMATS = ["vertices", "centroid_rel", "centroid_abs", "kitti"]  # supported export formats
    STD_LABEL_FORMAT = config_parser.get_label_settings("LABEL_FORMAT")
    STD_LABEL_FOLDER = config_parser.get_file_settings("LABEL_FOLDER")
    EXPORT_PRECISION = int(config_parser.get_label_settings("EXPORT_PRECISION"))  # Number of decimal places

    def __init__(self, strategy: str = STD_LABEL_FORMAT, path_to_label_folder: str = STD_LABEL_FOLDER):
        self.label_folder = path_to_label_folder
        if not os.path.isdir(self.label_folder):
            os.mkdir(self.label_folder)
        if strategy == "vertices":
            self.label_strategy = VerticesFormat(self.label_folder)
        elif strategy == "centroid_abs":
            self.label_strategy = CentroidFormat(self.label_folder, relative_rotation=False)
        elif strategy == "centroid_rel":
            self.label_strategy = CentroidFormat(self.label_folder, relative_rotation=True)
        elif strategy == "kitti":
            self.label_strategy = KittiFormat(self.label_folder, relative_rotation=True)  # KITTI is always relative
        else:
            self.label_strategy = CentroidFormat(self.label_folder, relative_rotation=False)
            print("Unknown export strategy '%s'. Proceeding with default (corners)!" % strategy)

    def import_labels(self, pcd_name: str) -> List[BBox]:
        try:
            return self.label_strategy.import_labels(os.path.splitext(pcd_name)[0])
        except KeyError as key_error:
            print("Found a key error with %s in the dictionary." % key_error)
            print("Could not import labels, please check the consistency of the label format.")
            return []
        except AttributeError as attribute_error:
            print("Attribute Error: %s. Expected a dictionary." % attribute_error)
            print("Could not import labels, please check the consistency of the label format.")
            return []

    def export_labels(self, pcd_path: str, bboxes: List[BBox]):
        pcd_name = ntpath.basename(pcd_path)
        pcd_folder = os.path.dirname(pcd_path)
        self.label_strategy.export_labels(bboxes, pcd_name, pcd_folder, pcd_path)


#
#   FORMAT HELPERS
#

def save_to_label_file(path_to_file, data):
    if os.path.isfile(path_to_file):
        print("File %s already exists, replacing file ..." % path_to_file)
    if os.path.splitext(path_to_file)[1] == ".json":
        with open(path_to_file, "w") as write_file:
            json.dump(data, write_file, indent="\t")
    else:
        with open(path_to_file, "w") as write_file:
            write_file.write(data)


def round_dec(x, decimal_places: int = LabelManager.EXPORT_PRECISION):
    return np.round(x, decimal_places).tolist()


def abs2rel_rotation(abs_rotation: float) -> float:
    """ Convert absolute rotation 0..360° into -pi..+pi from x-Axis.

    :param abs_rotation: Counterclockwise rotation from x-axis around z-axis
    :return: Relative rotation from x-axis around z-axis
    """
    rel_rotation = np.deg2rad(abs_rotation)
    if rel_rotation > np.pi:
        rel_rotation = rel_rotation - 2 * np.pi
    return rel_rotation


def rel2abs_rotation(rel_rotation: float) -> float:
    """ Convert relative rotation from -pi..+pi into 0..360° from x-Axis.

    :param rel_rotation: Rotation from x-axis around z-axis
    :return: Counterclockwise rotation from x-axis around z-axis
    """
    abs_rotation = np.rad2deg(rel_rotation)
    if abs_rotation < 0:
        abs_rotation = abs_rotation + 360
    return abs_rotation


class IFormattingInterface:
    __metaclass__ = ABCMeta

    def __init__(self, label_folder, relative_rotation=False):
        self.label_folder = label_folder
        print("Set export strategy to %s." % self.__class__.__name__)
        self.relative_rotation = relative_rotation
        if relative_rotation:
            print("Saving rotations relatively to positve x-axis in radians (-pi..+pi).")
        elif self.__class__.__name__ == "VerticesFormat":
            print("Saving rotations implicitly in the vertices coordinates.")
        else:
            print("Saving rotations absolutely to positve x-axis in degrees (0..360°).")

    @abstractmethod
    def import_labels(self, pcd_name_stripped):
        raise NotImplementedError

    @abstractmethod
    def export_labels(self, bboxes, pcd_name, pcd_folder, pcd_path):
        raise NotImplementedError


class VerticesFormat(IFormattingInterface, ABC):

    def import_labels(self, pcd_name_stripped):
        labels = []
        path_to_label = os.path.join(self.label_folder, pcd_name_stripped + ".json")

        if os.path.isfile(path_to_label):
            with open(path_to_label, "r") as read_file:
                data = json.load(read_file)

            for label in data["objects"]:
                vertices = label["vertices"]

                # Calculate centroid
                centroid = np.add(np.subtract(vertices[4], vertices[2]) / 2, vertices[2])

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

    def export_labels(self, bboxes, pcd_name, pcd_folder, pcd_path):
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
            label["vertices"] = bbox.get_vertices().tolist()  # ToDo: Add option for axis-aligned vertices
            data["objects"].append(label)

        path_to_json = os.path.join(self.label_folder, os.path.splitext(pcd_name)[0] + ".json")
        save_to_label_file(path_to_json, data)
        print("Exported %s labels to %s in %s formatting!" % (len(bboxes), path_to_json, self.__class__.__name__))


class CentroidFormat(IFormattingInterface, ABC):

    def import_labels(self, pcd_name_stripped):
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

    def export_labels(self, bboxes: List[BBox], pcd_name: str, pcd_folder: str, pcd_path: str):
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
            label["centroid"] = {str(axis): round_dec(val) for axis, val in zip(["x", "y", "z"], bbox.get_center())}
            label["dimensions"] = {str(dim): round_dec(val) for dim, val in zip(["length", "width", "height"],
                                                                                bbox.get_dimensions())}
            conv_rotations = bbox.get_rotations()
            if self.relative_rotation:
                conv_rotations = map(abs2rel_rotation, conv_rotations)

            label["rotations"] = {str(axis): round_dec(angle) for axis, angle in zip(["x", "y", "z"], conv_rotations)}
            data["objects"].append(label)

        # Save to JSON
        path_to_json = os.path.join(self.label_folder, os.path.splitext(pcd_name)[0] + ".json")
        save_to_label_file(path_to_json, data)
        print("Exported %s labels to %s in %s formatting!" % (len(bboxes), path_to_json, self.__class__.__name__))


class KittiFormat(IFormattingInterface, ABC):

    def import_labels(self, pcd_name_stripped):
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

    def export_labels(self, bboxes: List[BBox], pcd_name: str, pcd_folder: str, pcd_path: str):
        data = str()

        # Labels
        for bbox in bboxes:
            obj_type = bbox.get_classname()
            location = " ".join([str(v) for v in bbox.get_center()])
            dimensions = " ".join([str(v) for v in bbox.get_dimensions()])
            rotation_y = abs2rel_rotation(bbox.get_z_rotation())

            data += " ".join([obj_type, "0 0 0 0 0 0 0", dimensions, location, str(rotation_y)]) + "\n"

        # Save to TXT
        path_to_txt = os.path.join(self.label_folder, os.path.splitext(pcd_name)[0] + ".txt")
        save_to_label_file(path_to_txt, data)
        print("Exported %s labels to %s in %s formatting!" % (len(bboxes), path_to_txt, self.__class__.__name__))
