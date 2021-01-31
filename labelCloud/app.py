import sys

from PyQt5 import QtWidgets

from control.controler import Controler
from view.gui import GUI


def run():
    app = QtWidgets.QApplication(sys.argv)

    # Setup Model-View-Control structure
    control = Controler()
    view = GUI(control)

    # Install event filter to catch user interventions
    app.installEventFilter(view)

    # Start gui
    view.show()
    sys.exit(app.exec_())
