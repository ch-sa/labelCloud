import sys

from PyQt5 import QtWidgets

from control.controler import Controler
from view.gui import GUI


def get_main_app():
    app = QtWidgets.QApplication(sys.argv)

    # Setup Model-View-Control structure
    control = Controler()
    view = GUI(control)

    # Install event filter to catch user interventions
    app.installEventFilter(view)

    # Start GUI
    view.show()

    return app, view


def run():
    app, _ = get_main_app()
    sys.exit(app.exec_())
