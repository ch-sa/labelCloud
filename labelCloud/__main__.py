import sys

from PyQt5.QtWidgets import QApplication, QDesktopWidget


from labelCloud.view.gui import GUI
from labelCloud.control.controller import Controller


def main():
    app = QApplication(sys.argv)

    # Setup Model-View-Control structure
    control = Controller()
    view = GUI(control)

    # Install event filter to catch user interventions
    app.installEventFilter(view)

    # Start GUI
    view.show()

    app.setStyle("Fusion")
    desktop = QDesktopWidget().availableGeometry()
    width = (desktop.width() - view.width()) / 2
    height = (desktop.height() - view.height()) / 2
    view.move(width, height)

    print("Showing GUI...")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
