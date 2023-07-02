import os
from pathlib import Path

import pytest
from labelCloud.control.label_manager import LabelManager


@pytest.fixture
def label_centroid():  # absolute and relative
    label = """{"folder": "pointclouds", "filename": "test.ply", "path": "pointclouds/test.ply",
                "objects": [{"name": "cart", "centroid": { "x": -0.186338, "y": -0.241696, "z": 0.054818},
                "dimensions": {"length": 0.80014, "width": 0.512493, "height": 0.186055},
                "rotations": {"x": 0, "y": 0, "z": 1.616616} } ] }"""
    return label


@pytest.mark.parametrize(
    "label_format, rotation",
    [("centroid_abs", (0, 0, 1.616616)), ("centroid_rel", (0, 0, 92.6252738933211))],
)
def test_centroid_import(label_centroid, tmppath, label_format, rotation):
    # Write label to file
    with tmppath.joinpath("test.json").open("w") as write_file:
        write_file.write(label_centroid)

    # Import label file
    label_manager = LabelManager(strategy=label_format, path_to_label_folder=tmppath)
    bounding_boxes = label_manager.import_labels(Path("test.ply"))
    bbox = bounding_boxes[0]

    # Check label content
    assert bbox.get_classname() == "cart"
    assert bbox.get_center() == (-0.186338, -0.241696, 0.054818)
    assert bbox.get_dimensions() == (0.80014, 0.512493, 0.186055)
    assert bbox.get_rotations() == rotation


@pytest.fixture
def label_vertices():
    label = """{"folder": "pointclouds", "filename": "test.ply", "path": "pointclouds/test.ply", "objects": [
                {"name": "cart", "vertices": [[-0.245235,-0.465784,0.548944], [-0.597706,-0.630144,0.160035],
                [-0.117064,-0.406017,-0.370295], [0.235407,-0.241657,0.018614], [-0.308628,-0.329838,0.548944],
                [-0.661099,-0.494198,0.160035], [-0.180457,-0.270071,-0.370295], [0.172014,-0.105711,0.018614]]}]}"""
    return label


def test_vertices(label_vertices, tmppath):
    # Write label to file
    with tmppath.joinpath("test.json").open("w") as write_file:
        write_file.write(label_vertices)

    # Import label file
    label_manager = LabelManager(strategy="vertices", path_to_label_folder=tmppath)
    bounding_boxes = label_manager.import_labels(Path("test.ply"))
    bbox = bounding_boxes[0]

    # Check label content
    assert bbox.get_classname() == "cart"
    assert bbox.get_center() == pytest.approx((-0.212846, -0.3679275, 0.0893245))
    assert bbox.get_dimensions() == pytest.approx((0.75, 0.55, 0.15))
    assert bbox.get_rotations() == pytest.approx(
        (270, 45, 25)
    )  # apply for rounding errors


@pytest.fixture
def label_kitti():
    label = "cart 0 0 0 0 0 0 0 0.75 0.55 0.15 -0.409794 -0.012696 0.076757 0.436332"
    return label


def test_kitti(label_kitti, tmppath):
    # Write label to file
    with open(os.path.join(tmppath, "test.txt"), "w") as write_file:
        write_file.write(label_kitti)

    # Import label file
    label_manager = LabelManager(
        strategy="kitti_untransformed", path_to_label_folder=tmppath
    )
    bounding_boxes = label_manager.import_labels(Path("test.txt"))
    bbox = bounding_boxes[0]

    # Check label content
    assert bbox.get_classname() == "cart"
    assert bbox.get_center() == (-0.409794, -0.012696, 0.076757)
    assert bbox.get_dimensions() == (0.15, 0.55, 0.75)
    assert bbox.get_rotations() == pytest.approx(
        (0, 0, 25)
    )  # apply for rounding errors
