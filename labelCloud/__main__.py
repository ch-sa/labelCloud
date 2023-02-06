import argparse
import logging

from labelCloud import __version__


def main():
    parser = argparse.ArgumentParser(
        description="Label 3D bounding boxes inside point clouds."
    )
    parser.add_argument(
        "-e",
        "--example",
        action="store_true",
        help="Setup a project with an example point cloud and label.",
    )
    parser.add_argument(
        "-v", "--version", action="version", version="%(prog)s " + __version__
    )
    args = parser.parse_args()

    if args.example:
        setup_example_project()

    start_gui()


def setup_example_project() -> None:
    import shutil
    from pathlib import Path

    import pkg_resources

    from labelCloud.control.config_manager import config

    logging.info(
        "Starting labelCloud in example mode.\n"
        "Setting up project with example point cloud ,label and default config."
    )
    cwdir = Path().cwd()

    # Create folders
    pcd_folder = cwdir.joinpath(config.get("FILE", "pointcloud_folder"))
    pcd_folder.mkdir(exist_ok=True)
    label_folder = cwdir.joinpath(config.get("FILE", "label_folder"))
    label_folder.mkdir(exist_ok=True)

    # Copy example files
    shutil.copy(
        pkg_resources.resource_filename("labelCloud.resources", "default_config.ini"),
        str(cwdir.joinpath("config.ini")),
    )
    shutil.copy(
        pkg_resources.resource_filename(
            "labelCloud.resources.examples", "exemplary.ply"
        ),
        str(pcd_folder.joinpath("exemplary.ply")),
    )
    shutil.copy(
        pkg_resources.resource_filename("labelCloud.resources", "default_classes.json"),
        str(label_folder.joinpath("_classes.json")),
    )
    shutil.copy(
        pkg_resources.resource_filename(
            "labelCloud.resources.examples", "exemplary.json"
        ),
        str(label_folder.joinpath("exemplary.json")),
    )
    logging.info(
        f"Setup example project in {cwdir}:"
        "\n - config.ini"
        "\n - pointclouds/exemplary.ply"
        "\n - labels/exemplary.json"
    )


def start_gui():
    import sys

    from PyQt5.QtWidgets import QApplication, QDesktopWidget

    from labelCloud.control.controller import Controller
    from labelCloud.view.gui import GUI

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
    width = (desktop.width() - view.width()) // 2
    height = (desktop.height() - view.height()) // 2
    view.move(width, height)

    logging.info("Showing GUI...")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
