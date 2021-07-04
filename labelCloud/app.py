import sys

from PyQt5 import QtWidgets

from control.controller import Controller
from view.gui import GUI


def get_main_app():
    app = QtWidgets.QApplication(sys.argv)

    # Setup Model-View-Control structure
    control = Controller()
    view = GUI(control)

    # Install event filter to catch user interventions
    app.installEventFilter(view)

    # Start GUI
    view.show()

    return app, view


def run():
    app, _ = get_main_app()

    app.setStyle("Fusion")

    sys.exit(app.exec_())
