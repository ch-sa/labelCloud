import pytest
from PyQt5 import QtCore
from PyQt5.QtCore import QPoint

from control.config_manager import config


def test_picking_mode(qtbot, startup_pyqt):
    view, control = startup_pyqt

    control.bbox_controller.bboxes = []

    qtbot.mouseClick(view.button_activate_picking, QtCore.Qt.LeftButton, delay=1000)
    qtbot.mouseClick(view.glWidget, QtCore.Qt.LeftButton, pos=QPoint(500, 500), delay=1000)

    assert len(control.bbox_controller.bboxes) == 1
    new_bbox = control.bbox_controller.bboxes[0]
    assert new_bbox.center == tuple(pytest.approx(x, 0.1) for x in [-0.2479, -0.2245, 0.0447])

    assert new_bbox.length == config.getfloat("LABEL", "std_boundingbox_length")
    assert new_bbox.width == config.getfloat("LABEL", "std_boundingbox_width")
    assert new_bbox.height == config.getfloat("LABEL", "std_boundingbox_height")
    assert new_bbox.z_rotation == new_bbox.y_rotation == new_bbox.x_rotation == 0


# def test_spanning_mode(qtbot, startup_pyqt):
#     view, control = startup_pyqt
#     control.bbox_controller.bboxes = []
