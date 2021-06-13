import os
import sys

import pytest


def pytest_configure(config):
    os.chdir("../labelCloud")
    print(f"Set working directory to {os.getcwd()}.")

    sys.path.insert(0, "labelCloud")
    print(f"Added labelCloud to Python path.")

    import app  # preventing circular import


@pytest.fixture
def startup_pyqt(qtbot):
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
    return view, control
