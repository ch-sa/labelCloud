import tempfile
from contextlib import nullcontext
from pathlib import Path
from typing import Dict

import numpy as np
import pytest
from labelCloud.io.segmentations import NumpySegmentationHandler


@pytest.fixture
def segmentation_path() -> Path:
    path = Path("labels/segmentation/")
    assert path.exists()
    return path


@pytest.fixture
def label_definition_path() -> Path:
    path = Path("labels/schema/label_definition.json")
    assert path.exists()
    return path


@pytest.fixture
def label_path(segmentation_path) -> Path:
    path = segmentation_path / Path("exemplary.bin")
    assert path.exists()
    return path


@pytest.fixture
def not_label_path(segmentation_path) -> Path:
    path = segmentation_path / Path("foo.bin")
    assert not path.exists()
    return path


@pytest.fixture
def expected_label_definition() -> Dict[str, int]:
    return {
        "unassigned": 0,
        "person": 1,
        "cart": 2,
        "wall": 3,
        "floor": 4,
    }


@pytest.fixture
def handler() -> NumpySegmentationHandler:
    return NumpySegmentationHandler()


def test_read_labels(handler: NumpySegmentationHandler, label_path: Path) -> None:
    labels = handler._read_labels(label_path)
    assert labels.dtype == np.int8
    assert labels.shape == (86357,)


def test_create_labels(handler: NumpySegmentationHandler) -> None:
    labels = handler._create_labels(num_points=420)
    assert labels.dtype == np.int8
    assert labels.shape == (420,)
    assert (labels == np.zeros((420,))).all()


def test_write_labels(handler: NumpySegmentationHandler) -> None:
    labels = np.random.randint(low=0, high=4, size=(420,), dtype=np.int8)
    with tempfile.TemporaryDirectory() as tempdir:
        label_path = Path(tempdir) / Path("foo.bin")
        handler._write_labels(label_path=label_path, labels=labels)

        saved_labels = handler._read_labels(label_path)

    assert saved_labels.dtype == np.int8
    assert (labels == saved_labels).all()


@pytest.mark.parametrize(
    ("num_points", "exception"),
    (
        [
            (86357, nullcontext()),
            (420, pytest.raises(ValueError)),
        ]
    ),
)
def test_read_or_create_labels_when_exist(
    handler: NumpySegmentationHandler,
    label_path: Path,
    num_points: int,
    exception: BaseException,
) -> None:
    with exception:
        labels = handler.read_or_create_labels(
            label_path=label_path, num_points=num_points
        )
        assert labels.dtype == np.int8
        assert labels.shape == (num_points,)


def test_read_or_create_labels_when_not_exist(
    handler: NumpySegmentationHandler,
    not_label_path: Path,
) -> None:
    labels = handler.read_or_create_labels(label_path=not_label_path, num_points=420)
    assert labels.dtype == np.int8
    assert labels.shape == (420,)
    assert (labels == np.zeros((420,))).all()


def test_overwrite_labels(handler: NumpySegmentationHandler) -> None:
    labels = np.random.randint(low=0, high=4, size=(420,), dtype=np.int8)
    with tempfile.TemporaryDirectory() as tempdir:
        label_path = Path(tempdir) / Path("foo.bin")
        handler.overwrite_labels(label_path=label_path, labels=labels)
        saved_labels = handler._read_labels(label_path)

    assert saved_labels.dtype == np.int8
    assert (labels == saved_labels).all()
