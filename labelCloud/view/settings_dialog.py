from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QLineEdit, QDoubleSpinBox

from control.label_manager import LabelManager
from labelCloud.control.config_manager import config


class SettingsDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_gui = parent
        uic.loadUi("labelCloud/ressources/settings_interface.ui", self)
        self.fill_with_current_settings()

        self.buttonBox.accepted.connect(self.save)
        self.buttonBox.rejected.connect(self.chancel)

    def fill_with_current_settings(self):
        # File
        self.lineEdit_pointcloudfolder.setText(config.get_file_settings("POINTCLOUD_FOLDER"))
        self.lineEdit_labelfolder.setText(config.get_file_settings("LABEL_FOLDER"))

        # Pointcloud
        self.doubleSpinBox_pointsize.setValue(config.get_pointcloud_settings("POINT_SIZE"))
        self.lineEdit_pointcolor.setText(config.config["POINTCLOUD"]["colorless_color"])
        self.checkBox_colorizecolorless.setChecked(config.get_pointcloud_settings("COLORLESS_COLORIZE"))
        self.doubleSpinBox_standardtranslation.setValue(config.get_pointcloud_settings("STD_TRANSLATION"))
        self.doubleSpinBox_standardzoom.setValue(config.get_pointcloud_settings("STD_ZOOM"))

        # Label
        self.comboBox_labelformat.addItems(LabelManager.LABEL_FORMATS)  # TODO: Fix visualization
        self.comboBox_labelformat.setCurrentText(config.config["LABEL"]["label_format"])
        self.plainTextEdit_objectclasses.setPlainText(config.config["LABEL"]["object_classes"])
        self.lineEdit_standardobjectclass.setText(config.config["LABEL"]["std_object_class"])
        self.checkBox_zrotationonly.setChecked(config.get_label_settings("z_rotation_only"))
        self.spinBox_exportprecision.setValue(config.get_label_settings("export_precision"))
        self.spinBox_viewingprecision.setValue(config.get_label_settings("viewing_precision"))
        self.doubleSpinBox_minbboxdimensions.setValue(config.get_label_settings("min_boundingbox_dimension"))
        self.doubleSpinBox_stdbboxlength.setValue(config.get_label_settings("std_boundingbox_length"))
        self.doubleSpinBox_stdbboxwidth.setValue(config.get_label_settings("std_boundingbox_width"))
        self.doubleSpinBox_stdbboxheight.setValue(config.get_label_settings("std_boundingbox_height"))
        self.doubleSpinBox_stdbboxtranslation.setValue(config.get_label_settings("std_translation"))
        self.doubleSpinBox_stdbboxrotation.setValue(config.get_label_settings("std_rotation"))
        self.doubleSpinBox_stdbboxscaling.setValue(config.get_label_settings("std_scaling"))

        # User Interface
        self.lineEdit_backgroundcolor.setText(config.config["USER_INTERFACE"]["background_color"])
        self.checkBox_showfloor.setChecked(config.get_app_settings("show_floor"))
        self.checkBox_showbboxorientation.setChecked(config.get_app_settings("show_orientation"))

    def save(self) -> None:

        # File
        config.config["FILE"]["pointcloud_folder"] = self.lineEdit_pointcloudfolder.text()
        config.config["FILE"]["label_folder"] = self.lineEdit_labelfolder.text()

        # Pointcloud
        config.config["POINTCLOUD"]["point_size"] = str(self.doubleSpinBox_pointsize.value())
        config.config["POINTCLOUD"]["colorless_color"] = self.lineEdit_pointcolor.text()
        config.config["POINTCLOUD"]["colorless_colorize"] = str(self.checkBox_colorizecolorless.isChecked())
        config.config["POINTCLOUD"]["std_translation"] = str(self.doubleSpinBox_standardtranslation.value())
        config.config["POINTCLOUD"]["std_zoom"] = str(self.doubleSpinBox_standardzoom.value())

        # Label
        config.config["LABEL"]["label_format"] = self.comboBox_labelformat.currentText()
        config.config["LABEL"]["object_classes"] = self.plainTextEdit_objectclasses.toPlainText()
        config.config["LABEL"]["std_object_class"] = self.lineEdit_standardobjectclass.text()
        config.config["LABEL"]["z_rotation_only"] = str(self.checkBox_zrotationonly.isChecked())
        config.config["LABEL"]["export_precision"] = str(self.spinBox_exportprecision.value())
        config.config["LABEL"]["viewing_precision"] = str(self.spinBox_viewingprecision.value())
        config.config["LABEL"]["min_bounding_box_dimension"] = str(self.doubleSpinBox_minbboxdimensions.value())
        config.config["LABEL"]["std_boundingbox_length"] = str(self.doubleSpinBox_stdbboxlength.value())
        config.config["LABEL"]["std_boundingbox_width"] = str(self.doubleSpinBox_stdbboxwidth.value())
        config.config["LABEL"]["std_boundingbox_height"] = str(self.doubleSpinBox_stdbboxheight.value())
        config.config["LABEL"]["std_translation"] = str(self.doubleSpinBox_stdbboxtranslation.value())
        config.config["LABEL"]["std_rotation"] = str(self.doubleSpinBox_stdbboxrotation.value())
        config.config["LABEL"]["std_scaling"] = str(self.doubleSpinBox_stdbboxscaling.value())

        # User Interface
        config.config["USER_INTERFACE"]["background_color"] = self.lineEdit_backgroundcolor.text()
        config.config["USER_INTERFACE"]["show_floor"] = str(self.checkBox_showfloor.isChecked())
        config.config["USER_INTERFACE"]["show_orientation"] = str(self.checkBox_showbboxorientation.isChecked())

        config.write_into_file()
        self.parent_gui.glWidget.update_configuration()
        print("Saved and activated new configuration!")


    def chancel(self) -> None:
        print("Settings dialog was chanceled!")
