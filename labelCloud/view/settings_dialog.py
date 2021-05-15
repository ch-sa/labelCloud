from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QLineEdit, QDoubleSpinBox

from labelCloud.control.config_manager import config


class SettingsDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi("labelCloud/ressources/settings_interface.ui", self)
        self.fill_with_current_settings()

        self.buttonBox.accepted.connect(self.save)
        self.buttonBox.rejected.connect(self.chancel)

    def fill_with_current_settings(self):
        self.lineEdit_pointcloudfolder.setText(config.get_file_settings("POINTCLOUD_FOLDER"))
        self.lineEdit_labelfolder.setText(config.get_file_settings("LABEL_FOLDER"))

        self.doubleSpinBox_pointsize.setValue(config.get_pointcloud_settings("POINT_SIZE"))
        self.lineEdit_pointcolor.setText(str(config.get_pointcloud_settings("COLORLESS_COLOR")))
        self.doubleSpinBox_standardtranslation.setValue(config.get_pointcloud_settings("STD_TRANSLATION"))
        self.doubleSpinBox_standardzoom.setValue(config.get_pointcloud_settings("STD_ZOOM"))

    def save(self) -> None:
        print("Settings dialog was accepted!")

        config.config["FILE"]["pointcloud_folder"] = self.lineEdit_pointcloudfolder.text()
        config.config["FILE"]["label_folder"] = self.lineEdit_labelfolder.text()

        config.config["POINTCLOUD"]["point_size"] = str(self.doubleSpinBox_pointsize.value())
        config.config["POINTCLOUD"]["colorless_color"] = self.lineEdit_pointcolor.text()
        config.config["POINTCLOUD"]["std_translation"] = str(self.doubleSpinBox_standardtranslation.value())
        config.config["POINTCLOUD"]["std_zoom"] = str(self.doubleSpinBox_standardzoom.value())

        config.write_into_file()

    def chancel(self) -> None:
        print("Settings dialog was chanceled!")
