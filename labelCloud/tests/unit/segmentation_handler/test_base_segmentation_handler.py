from labelCloud.io.segmentations import (
    BaseSegmentationHandler,
    NumpySegmentationHandler,
)


def test_get_subclass() -> None:
    handler = BaseSegmentationHandler.get_handler(".bin")
    assert handler is NumpySegmentationHandler
