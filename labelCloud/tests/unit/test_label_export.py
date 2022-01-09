# Testing the correct processing of labels for the export in different formats
import json
import os
from pathlib import Path

import pytest
from labelCloud.control.label_manager import LabelManager
from labelCloud.model.bbox import BBox


@pytest.fixture
def bounding_box():
    test_bbox = BBox(0, 0, 0, 1, 1, 1)
    test_bbox.set_classname("test_bbox")
    test_bbox.set_rotations(90, 180, 270)
    return test_bbox


def test_vertices_export(bounding_box, tmppath):
    label_manager = LabelManager(strategy="vertices", path_to_label_folder=tmppath)
    pcd_path = Path("testfolder/testpcd.ply")
    label_manager.export_labels(pcd_path, [bounding_box])

    with tmppath.joinpath("testpcd.json").open("r") as read_file:
        data = json.load(read_file)

    assert data["folder"] == "testfolder"
    assert data["filename"] == "testpcd.ply"
    assert data["path"] == str(pcd_path)
    assert data["objects"] == [
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
    ]


def test_centroid_rel_export(bounding_box, tmppath):
    label_manager = LabelManager(strategy="centroid_rel", path_to_label_folder=tmppath)
    pcd_path = Path("testfolder/testpcd.ply")
    label_manager.export_labels(pcd_path, [bounding_box])

    with tmppath.joinpath("testpcd.json").open("r") as read_file:
        data = json.load(read_file)

    assert data["folder"] == "testfolder"
    assert data["filename"] == "testpcd.ply"
    assert data["path"] == str(pcd_path)
    assert data["objects"] == [
        {
            "name": "test_bbox",
            "centroid": {"x": 0, "y": 0, "z": 0},
            "dimensions": {"length": 1, "width": 1, "height": 1},
            "rotations": {"x": 1.57079633, "y": 3.14159265, "z": -1.57079633},
        }
    ]


def test_centroid_abs_export(bounding_box, tmppath):
    label_manager = LabelManager(strategy="centroid_abs", path_to_label_folder=tmppath)
    pcd_path = Path("testfolder/testpcd.ply")
    label_manager.export_labels(pcd_path, [bounding_box])

    with tmppath.joinpath("testpcd.json").open("r") as read_file:
        data = json.load(read_file)

    assert data["folder"] == "testfolder"
    assert data["filename"] == "testpcd.ply"
    assert data["path"] == str(pcd_path)
    assert data["objects"] == [
        {
            "name": "test_bbox",
            "centroid": {"x": 0, "y": 0, "z": 0},
            "dimensions": {"length": 1, "width": 1, "height": 1},
            "rotations": {"x": 90, "y": 180, "z": 270},
        }
    ]


def test_kitti_export(bounding_box, tmppath):
    label_manager = LabelManager(
        strategy="kitti_untransformed", path_to_label_folder=tmppath
    )
    label_manager.export_labels(Path("testfolder/testpcd.ply"), [bounding_box])

    with tmppath.joinpath("testpcd.txt").open("r") as read_file:
        data = read_file.readlines()

    assert data == ["test_bbox 0 0 0 0 0 0 0 1 1 1 0 0 0 -1.57079633\n"]
