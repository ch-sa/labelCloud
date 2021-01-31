import sys

from PyQt5 import QtWidgets

from control.controler import Controler
from view.gui import GUI


def run():
    app = QtWidgets.QApplication(sys.argv)

    # Setup Model-View-Control structure
    control = Controler()
    view = GUI(control)
    app.installEventFilter(view)

    view.show()

    sys.exit(app.exec_())
