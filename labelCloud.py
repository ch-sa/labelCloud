import sys

from PyQt5 import QtWidgets

from modules.control.controler import Controler
from modules.view.gui import GUI

print("All imports loaded successfully!")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # Create GUI
    control = Controler()
    view = GUI(control)
    app.installEventFilter(view)

    view.show()

    sys.exit(app.exec_())
