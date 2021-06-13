import pytest
from PyQt5 import QtCore
from PyQt5.QtCore import QPoint

from control.config_manager import config
from model.bbox import BBox


def test_picking_mode(qtbot, startup_pyqt):
    view, control = startup_pyqt
    control.bbox_controller.bboxes = []

    qtbot.mouseClick(view.button_activate_picking, QtCore.Qt.LeftButton, delay=1000)
    qtbot.mouseClick(view.glWidget, QtCore.Qt.LeftButton, pos=QPoint(500, 500), delay=1000)

    assert len(control.bbox_controller.bboxes) == 1
    new_bbox = control.bbox_controller.bboxes[0]
    assert new_bbox.center == tuple(pytest.approx(x, 0.01) for x in [-0.2479, -0.2245, 0.0447])

    assert new_bbox.length == config.getfloat("LABEL", "std_boundingbox_length")
    assert new_bbox.width == config.getfloat("LABEL", "std_boundingbox_width")
    assert new_bbox.height == config.getfloat("LABEL", "std_boundingbox_height")
    assert new_bbox.z_rotation == new_bbox.y_rotation == new_bbox.x_rotation == 0


def test_spanning_mode(qtbot, startup_pyqt):
    view, control = startup_pyqt
    control.bbox_controller.bboxes = []
    config.set("USER_INTERFACE", "z_rotation_only", "True")

    qtbot.mouseClick(view.button_activate_spanning, QtCore.Qt.LeftButton, delay=10)
    qtbot.mouseClick(view.glWidget, QtCore.Qt.LeftButton, pos=QPoint(431, 475), delay=20)
    qtbot.mouseClick(view.glWidget, QtCore.Qt.LeftButton, pos=QPoint(506, 367), delay=20)
    qtbot.mouseClick(view.glWidget, QtCore.Qt.LeftButton, pos=QPoint(572, 439), delay=20)
    qtbot.mouseClick(view.glWidget, QtCore.Qt.LeftButton, pos=QPoint(607, 556), delay=20)

    assert len(control.bbox_controller.bboxes) == 1
    new_bbox: BBox = control.bbox_controller.bboxes[0]
    assert new_bbox.center == tuple(pytest.approx(x, 0.01) for x in [-0.2100, -0.2348, 0.0568])
    assert new_bbox.get_dimensions() == tuple(pytest.approx(x, 0.01) for x in [0.7344, 0.5305, 0.1212])
    assert new_bbox.get_rotations() == tuple(pytest.approx(x % 360, 0.5) for x in [0, 0, 55.2205])
