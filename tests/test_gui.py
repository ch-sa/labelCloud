import sys
import threading
import time

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QApplication


def test_gui(qtbot):
    import sys, os
    os.chdir("../labelCloud")
    # print("CWD= %s" % os.curdir)
    sys.path.insert(0, "labelCloud")
    from control.controller import Controller
    from view.gui import GUI

    # Setup Model-View-Control structure
    control = Controller()
    view = GUI(control)
    qtbot.addWidget(view)
    qtbot.addWidget(view.glWidget)

    # Install event filter to catch user interventions
    # app.installEventFilter(view)
    # Start GUI
    view.show()
    time.sleep(1)

    assert len(view.controller.pcd_manager.pcds) > 0
    os.remove("labels/exemplary.json")
    assert len(os.listdir("labels")) == 0
    qtbot.mouseClick(view.button_next_pcd, QtCore.Qt.LeftButton, delay=2000)
    time.sleep(2)
    assert len(os.listdir("labels")) == 1

    bbox = view.controller.bbox_controller.bboxes[0]
    bbox.center = (0, 0, 0)
    view.controller.bbox_controller.set_active_bbox(0)
    print("BBOX: %s" % [str(c) for c in bbox.get_center()])
    qtbot.mouseClick(view.button_right, QtCore.Qt.LeftButton, delay=2000)
    qtbot.mouseClick(view.button_up, QtCore.Qt.LeftButton, delay=2000)
    qtbot.mouseClick(view.button_backward, QtCore.Qt.LeftButton, delay=2000)
    print("BBOX: %s" % [str(c) for c in bbox.get_center()])
    assert bbox.center == (0.03, 0.03, 0.03)

    view.close()
