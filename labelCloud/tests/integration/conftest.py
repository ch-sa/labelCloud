import logging
import os
import time
from typing import Tuple

import pytest
from PyQt5 import QtCore

from labelCloud.control.controller import Controller
from labelCloud.model.bbox import BBox
from labelCloud.view.gui import GUI
from labelCloud.view.startup_dialog import StartupDialog


def pytest_configure(config):
    os.chdir("../labelCloud")
    logging.info(f"Set working directory to {os.getcwd()}.")


@pytest.fixture
def startup_pyqt(qtbot, qapp, monkeypatch):

    # Setup Model-View-Control structure
    control = Controller()

    monkeypatch.setattr(StartupDialog, "exec", lambda self: 1)

    view = GUI(control)
    qtbot.addWidget(view)
    qtbot.addWidget(view.gl_widget)

    # Install event filter to catch user interventions
    qapp.installEventFilter(view)

    # Start GUI
    view.show()
    return view, control


@pytest.fixture
def bbox():

    return BBox(cx=0, cy=0, cz=0, length=3, width=2, height=1)
