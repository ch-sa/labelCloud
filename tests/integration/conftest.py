import os
import sys

import pytest


def pytest_configure(config):
    os.chdir("../labelCloud")
    print(f"Set working directory to {os.getcwd()}.")

    sys.path.insert(0, "labelCloud")
    print("Added labelCloud to Python path.")

    # preventing circular import
    import app  # noqa: E401


@pytest.fixture
def startup_pyqt(qtbot, qapp):
    from control.controller import Controller
    from view.gui import GUI

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
    from model.bbox import BBox

    return BBox(cx=0, cy=0, cz=0, length=3, width=2, height=1)
