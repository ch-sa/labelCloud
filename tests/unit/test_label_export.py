# Testing the correct processing of labels for the export in different formats
import json
import os
import pytest

from model.bbox import BBox
from control.label_manager import LabelManager


@pytest.fixture
def bounding_box():
    test_bbox = BBox(0, 0, 0, 1, 1, 1)
    test_bbox.set_classname("test_bbox")
    test_bbox.set_rotations(90, 180, 270)
    return test_bbox


def test_vertices_export(bounding_box, tmpdir):
    label_manager = LabelManager(strategy="vertices", path_to_label_folder=tmpdir)
    label_manager.export_labels("testfolder/testpcd.ply", [bounding_box])

    with open(os.path.join(tmpdir, "testpcd.json"), "r") as read_file:
        data = json.load(read_file)

    assert data == {
        "folder": "testfolder",
        "filename": "testpcd.ply",
        "path": "testfolder/testpcd.ply",
        "objects": [
            {
                "name": "test_bbox",
                "vertices": [
                    [0.5, -0.5, 0.5],
                    [0.5, -0.5, -0.5],
                    [0.5, 0.5, -0.5],
                    [0.5, 0.5, 0.5],
                    [-0.5, -0.5, 0.5],
                    [-0.5, -0.5, -0.5],
                    [-0.5, 0.5, -0.5],
                    [-0.5, 0.5, 0.5],
                ],
            }
        ],
    }


def test_centroid_rel_export(bounding_box, tmpdir):
    label_manager = LabelManager(strategy="centroid_rel", path_to_label_folder=tmpdir)
    label_manager.export_labels("testfolder/testpcd.ply", [bounding_box])

    with open(os.path.join(tmpdir, "testpcd.json"), "r") as read_file:
        data = json.load(read_file)

    assert data == {
        "folder": "testfolder",
        "filename": "testpcd.ply",
        "path": "testfolder/testpcd.ply",
        "objects": [
            {
                "name": "test_bbox",
                "centroid": {"x": 0, "y": 0, "z": 0},
                "dimensions": {"length": 1, "width": 1, "height": 1},
                "rotations": {"x": 1.57079633, "y": 3.14159265, "z": -1.57079633},
            }
        ],
    }


def test_centroid_abs_export(bounding_box, tmpdir):
    label_manager = LabelManager(strategy="centroid_abs", path_to_label_folder=tmpdir)
    label_manager.export_labels("testfolder/testpcd.ply", [bounding_box])

    with open(os.path.join(tmpdir, "testpcd.json"), "r") as read_file:
        data = json.load(read_file)

    assert data == {
        "folder": "testfolder",
        "filename": "testpcd.ply",
        "path": "testfolder/testpcd.ply",
        "objects": [
            {
                "name": "test_bbox",
                "centroid": {"x": 0, "y": 0, "z": 0},
                "dimensions": {"length": 1, "width": 1, "height": 1},
                "rotations": {"x": 90, "y": 180, "z": 270},
            }
        ],
    }


def test_kitti_export(bounding_box, tmpdir):
    label_manager = LabelManager(strategy="kitti", path_to_label_folder=tmpdir)
    label_manager.export_labels("testfolder/testpcd.ply", [bounding_box])

    with open(os.path.join(tmpdir, "testpcd.txt"), "r") as read_file:
        data = read_file.readlines()

    assert data == ["test_bbox 0 0 0 0 0 0 0 1 1 1 0 0 0 -1.57079633\n"]
