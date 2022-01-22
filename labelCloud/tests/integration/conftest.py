import logging
import os

import pytest
from labelCloud.control.controller import Controller
from labelCloud.model.bbox import BBox
from labelCloud.view.gui import GUI


def pytest_configure(config):
    os.chdir("../labelCloud")
    logging.info(f"Set working directory to {os.getcwd()}.")


@pytest.fixture
def startup_pyqt(qtbot, qapp):

    # Setup Model-View-Control structure
    control = Controller()
    view = GUI(control)
    qtbot.addWidget(view)
    qtbot.addWidget(view.glWidget)

    # Install event filter to catch user interventions
    qapp.installEventFilter(view)

    # Start GUI
    view.show()
    return view, control


@pytest.fixture
def bbox():

    return BBox(cx=0, cy=0, cz=0, length=3, width=2, height=1)
