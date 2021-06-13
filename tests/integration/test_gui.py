import os
from PyQt5 import QtCore
from PyQt5.QtCore import QPoint, QPointF
from PyQt5.QtGui import QWheelEvent
from PyQt5.QtWidgets import QAbstractSlider

from control.config_manager import config


def test_gui(qtbot, startup_pyqt):
    view, controller = startup_pyqt

    assert len(controller.pcd_manager.pcds) > 0
    os.remove("labels/exemplary.json")
    assert len(os.listdir("labels")) == 0
    qtbot.mouseClick(view.button_next_pcd, QtCore.Qt.LeftButton, delay=0)
    assert len(os.listdir("labels")) == 1

    bbox = controller.bbox_controller.bboxes[0]
    bbox.center = (0, 0, 0)
    controller.bbox_controller.set_active_bbox(0)
    print("BBOX: %s" % [str(c) for c in bbox.get_center()])
    qtbot.mouseClick(view.button_right, QtCore.Qt.LeftButton, delay=0)
    qtbot.mouseClick(view.button_up, QtCore.Qt.LeftButton, delay=0)
    qtbot.mouseClick(view.button_backward, QtCore.Qt.LeftButton, delay=0)
    print("BBOX: %s" % [str(c) for c in bbox.get_center()])
    assert bbox.center == (0.03, 0.03, 0.03)

    view.close()


def test_bbox_control_with_buttons(qtbot, startup_pyqt):
    view, controller = startup_pyqt

    bbox = controller.bbox_controller.bboxes[0]
    bbox.center = (0, 0, 0)
    bbox.length = old_length = 3
    bbox.width = old_width = 2
    bbox.height = old_height = 1
    bbox.z_rotation = 0
    controller.bbox_controller.set_active_bbox(0)

    # Translation
    translation_step = config.getfloat("LABEL", "std_translation")
    qtbot.mouseClick(view.button_right, QtCore.Qt.LeftButton, delay=0)
    qtbot.mouseClick(view.button_up, QtCore.Qt.LeftButton, delay=0)
    qtbot.mouseClick(view.button_backward, QtCore.Qt.LeftButton, delay=0)
    print("BBOX: %s" % [str(c) for c in bbox.get_center()])  # TODO: remove!
    assert bbox.center == (translation_step, translation_step, translation_step)
    qtbot.mouseClick(view.button_left, QtCore.Qt.LeftButton, delay=0)
    qtbot.mouseClick(view.button_down, QtCore.Qt.LeftButton, delay=0)
    qtbot.mouseClick(view.button_forward, QtCore.Qt.LeftButton)
    print("BBOX: %s" % [str(c) for c in bbox.get_center()])
    assert bbox.center == (0.00, 0.00, 0.00)

    # Scaling
    scaling_step = config.getfloat("LABEL", "std_scaling")
    qtbot.mouseClick(view.button_incr_dim, QtCore.Qt.LeftButton)
    assert bbox.length == old_length + scaling_step
    assert bbox.width == old_width / old_length * bbox.length
    assert bbox.height == old_height / old_length * bbox.length

    # Rotation
    # TODO: Make dial configureable?
    view.dial_zrotation.triggerAction(QAbstractSlider.SliderSingleStepAdd)
    assert bbox.z_rotation == 1
    view.dial_zrotation.triggerAction(QAbstractSlider.SliderPageStepAdd)
    assert bbox.z_rotation == 11

    view.close()
