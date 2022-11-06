from typing import List

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ..definitions.types import LabelingMode
from ..io.labels.config import ClassConfig, LabelConfig
from ..utils.color import hex_to_rgb, rgb_to_hex


class ColorButton(QtWidgets.QPushButton):
    """
    Custom Qt Widget to show a chosen color.

    Left-clicking the button shows the color-chooser, while
    right-clicking resets the color to None (no-color).

    Source: https://www.pythonguis.com/widgets/qcolorbutton-a-color-selector-tool-for-pyqt/
    """

    colorChanged = pyqtSignal(object)

    def __init__(self, *args, color=None, **kwargs):
        super(ColorButton, self).__init__(*args, **kwargs)

        self._color = None
        self._default = color
        self.pressed.connect(self.onColorPicker)

        # Set the initial/default state.
        self.setColor(self._default)

    def setColor(self, color):
        if color != self._color:
            self._color = color
            self.colorChanged.emit(color)

        if self._color:
            self.setStyleSheet("background-color: %s;" % self._color)
        else:
            self.setStyleSheet("")

    def color(self):
        return self._color

    def onColorPicker(self):
        """
        Show color-picker dialog to select color.

        Qt will use the native dialog by default.

        """
        dlg = QtWidgets.QColorDialog(self)
        if self._color:
            dlg.setCurrentColor(QtGui.QColor(self._color))

        if dlg.exec_():
            self.setColor(dlg.currentColor().name())

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            self.setColor(self._default)

        return super(ColorButton, self).mousePressEvent(e)


class StartupDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.parent_gui = parent

        self.setWindowTitle("Welcome to labelCloud")

        self.main_layout = QVBoxLayout()

        row_buttons = QHBoxLayout()
        self.button_object_detection = QPushButton(text=LabelingMode.OBJECT_DETECTION.title().replace("_", " "))
        self.button_object_detection.setCheckable(True)
        self.button_semantic_segmentation = QPushButton(text=LabelingMode.SEMANTIC_SEGMENTATION.title().replace("_", " "))
        self.button_semantic_segmentation.setCheckable(True)

        row_buttons.addWidget(self.button_object_detection)
        row_buttons.addWidget(self.button_semantic_segmentation)
        self.main_layout.addLayout(row_buttons)

        self.load_class_labels(self.main_layout)

        self.button_add_label = QPushButton(text="Add new label")
        self.button_add_label.clicked.connect(self.add_label_row)
        self.main_layout.addWidget(self.button_add_label)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Save)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.button_object_detection.clicked.connect(self.switch_to_object_detection_mode)
        self.button_semantic_segmentation.clicked.connect(self.switch_to_semantic_segmentation_mode)
        self.main_layout.addWidget(self.buttonBox)
        self.setLayout(self.main_layout)

        self.delete_buttons.buttonClicked.connect(self.delete_label_row)

    def switch_to_object_detection_mode(self) -> None:
        self.button_object_detection.setChecked(True)
        self.button_semantic_segmentation.setChecked(False)

    def switch_to_semantic_segmentation_mode(self) -> None:
        self.button_object_detection.setChecked(False)
        self.button_semantic_segmentation.setChecked(True)

    def get_labeling_mode(self) -> LabelingMode:
        if self.button_object_detection.isChecked():
            return LabelingMode.OBJECT_DETECTION
        return LabelingMode.SEMANTIC_SEGMENTATION

    def load_class_labels(self, main_layout: QVBoxLayout) -> None:

        self.class_labels = QVBoxLayout()
        self.delete_buttons = QButtonGroup()
        self.delete_button_hash: List[int] = []

        for class_label in LabelConfig().classes:
            row_label = QHBoxLayout()
            # label id
            label_id = QSpinBox()
            label_id.setMinimum(0)
            label_id.setMaximum(255)
            label_id.setValue(class_label.id)
            # label name
            label_name = QLineEdit(class_label.name)
            # label color
            label_color = ColorButton(color=rgb_to_hex(class_label.color))
            # delete button
            label_delete = QPushButton(text="X")
            self.delete_buttons.addButton(label_delete, hash(label_delete))
            self.delete_button_hash.append(hash(label_delete))

            row_label.addWidget(label_delete)
            row_label.addWidget(label_id)
            row_label.addWidget(label_name, stretch=2)
            row_label.addWidget(label_color)

            self.class_labels.addLayout(row_label)
        main_layout.addWidget(QLabel("Class definition"))
        main_layout.addLayout(self.class_labels)
        # Load annotation mode
        if LabelConfig().type == LabelingMode.OBJECT_DETECTION:
            self.button_object_detection.setChecked(True)
        else:
            self.button_semantic_segmentation.setChecked(True)

    def save_class_labels(self) -> None:
        classes = []
        for i in range(self.class_labels.count()):
            
            row: QHBoxLayout = self.class_labels.itemAt(i)
            class_id = int(row.itemAt(1).widget().text())
            class_name = row.itemAt(2).widget().text()
            class_color = hex_to_rgb(row.itemAt(3).widget().color())
            classes.append(ClassConfig(id=class_id, name=class_name, color=class_color))
        LabelConfig().classes = classes
        LabelConfig().type = self.get_labeling_mode()        
        LabelConfig().save_config()

    def next_label_id(self) -> int:
        max_class_id = 0
        for i in range(self.class_labels.count()):
            row: QHBoxLayout = self.class_labels.itemAt(i)
            max_class_id = max(max_class_id, int(row.itemAt(1).widget().text()))
        return max_class_id + 1

    def delete_label_row(self, object):

        row = self.delete_button_hash.index(hash(object))
        del self.delete_button_hash[row]
        row_label: QHBoxLayout = self.class_labels.itemAt(row)
        for _ in range(row_label.count()):
            row_label.removeWidget(row_label.itemAt(0).widget())

        self.class_labels.removeItem(self.class_labels.itemAt(row))
        

    def add_label_row(self) -> None:
        row_label = QHBoxLayout()

        label_id = QSpinBox()
        label_id.setMinimum(0)
        label_id.setMaximum(255)
        label_id.setValue(self.next_label_id())
        label_name = QLineEdit()
        label_color = ColorButton()
        label_delete = QPushButton(text="X")
        self.delete_button_hash.append(hash(label_delete))
        self.delete_buttons.addButton(label_delete)
        row_label.addWidget(label_delete)
        row_label.addWidget(label_id)
        row_label.addWidget(label_name, stretch=2)
        row_label.addWidget(label_color)
        self.class_labels.insertLayout(self.class_labels.count(), row_label)
