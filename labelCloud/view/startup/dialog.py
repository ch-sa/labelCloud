import traceback

import pkg_resources
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QComboBox,
    QDesktopWidget,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
)

from ...io.labels.config import LabelConfig
from ...io.labels.exceptions import (
    DefaultIdMismatchException,
    LabelClassNameEmpty,
    LabelIdsNotUniqueException,
    ZeroLabelException,
)
from .class_list import ClassList
from .labeling_mode import SelectLabelingMode


class StartupDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.parent_gui = parent

        self.setWindowTitle("Welcome to labelCloud")
        screen_size = QDesktopWidget().availableGeometry(self).size()
        self.resize(screen_size * 0.5)
        self.setWindowIcon(
            QIcon(
                pkg_resources.resource_filename(
                    "labelCloud.resources.icons", "labelCloud.ico"
                )
            )
        )
        self.setContentsMargins(50, 10, 50, 10)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setAlignment(Qt.AlignTop)
        self.setLayout(main_layout)

        # 1. Row: Selection of labeling mode via checkable buttons
        self.button_semantic_segmentation: QPushButton
        self.add_labeling_mode_row(main_layout)

        # 2. Row: Definition of class labels
        self.add_class_definition_rows(main_layout)

        # 3. Row: Select label export format
        self.add_default_and_export_format(main_layout)

        # 4. Row: Buttons to save or cancel
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Save)
        self.buttonBox.accepted.connect(self.save)
        self.buttonBox.rejected.connect(self.reject)

        main_layout.addWidget(self.buttonBox)

    # ---------------------------------------------------------------------------- #
    #                                     SETUP                                    #
    # ---------------------------------------------------------------------------- #

    def add_labeling_mode_row(self, parent_layout: QVBoxLayout) -> None:
        """
        Add a row to select the labeling mode with two exclusive buttons.

         - the selected mode influences the available label export formats
        """
        parent_layout.addWidget(QLabel("Select labeling mode:"))

        self.select_labeling_mode = SelectLabelingMode()
        self.select_labeling_mode.changed.connect(self._update_label_formats)
        parent_layout.addWidget(self.select_labeling_mode)

    def _update_label_formats(self) -> None:
        self.label_export_format.clear()
        self.label_export_format.addItems(
            self.select_labeling_mode.available_label_formats
        )

    def add_default_and_export_format(self, parent_layout: QVBoxLayout) -> None:
        """
        Add a row to select the default class and the label export format.
        """
        row = QHBoxLayout()

        row.addWidget(QLabel("Default class:"))

        self.default_label = QComboBox()
        self.default_label.addItems(
            [class_label.name for class_label in LabelConfig().classes]
        )
        self.default_label.setCurrentText(LabelConfig().get_default_class_name())
        row.addWidget(self.default_label, 2)

        row.addSpacing(100)

        row.addWidget(QLabel("Label export format:"))

        self.label_export_format = QComboBox()
        self._update_label_formats()
        self.label_export_format.setCurrentText(LabelConfig().format)
        row.addWidget(self.label_export_format, 2)

        parent_layout.addLayout(row)

    def _on_class_list_changed(self):
        old_index = self.default_label.currentIndex()
        old_text = self.default_label.currentText()
        old_count = self.default_label.count()

        self.default_label.clear()
        self.default_label.addItems(
            [class_label.name for class_label in self.label_list.get_class_configs()]
        )

        if old_count == self.default_label.count():  # only renaming
            self.default_label.setCurrentIndex(old_index)
        else:
            self.default_label.setCurrentText(old_text)

    def add_class_definition_rows(self, parent_layout: QVBoxLayout) -> None:
        scroll_area = QScrollArea()
        self.label_list = ClassList(scroll_area)

        self.label_list.changed.connect(self._on_class_list_changed)

        parent_layout.addWidget(QLabel("Change class labels:"))

        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.label_list)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        parent_layout.addWidget(scroll_area)

        button_add_label = QPushButton(text="Add new label")
        button_add_label.clicked.connect(lambda: self.label_list.add_label())
        parent_layout.addWidget(button_add_label)

    # ---------------------------------------------------------------------------- #
    #                                     LOGIC                                    #
    # ---------------------------------------------------------------------------- #

    def _populate_label_config(self) -> None:
        LabelConfig().type = self.select_labeling_mode.selected_labeling_mode

        LabelConfig().classes = self.label_list.get_class_configs()

        LabelConfig().set_default_class(self.default_label.currentText())
        LabelConfig().set_label_format(self.label_export_format.currentText())

    def _save_class_labels(self) -> None:
        LabelConfig().validate()
        LabelConfig().save_config()

    def save(self):
        self._populate_label_config()

        title = "Something went wrong"
        text = ""
        informative_text = ""
        icon = QMessageBox.Critical
        buttons = QMessageBox.Cancel
        msg = QMessageBox()

        try:
            self._save_class_labels()
            self.accept()
            return

        except DefaultIdMismatchException as e:
            text = e.__class__.__name__
            informative_text = (
                str(e)
                + f" Do you want to overwrite the default to the first label `{LabelConfig().classes[0].id}`?"
            )
            icon = QMessageBox.Question
            buttons |= QMessageBox.Ok
            msg.accepted.connect(LabelConfig().set_first_as_default)

        except (
            ZeroLabelException,
            LabelIdsNotUniqueException,
            LabelClassNameEmpty,
        ) as e:
            text = e.__class__.__name__
            informative_text = str(e)

        except Exception as e:
            text = e.__class__.__name__
            informative_text = traceback.format_exc()

        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setInformativeText(informative_text)
        msg.setIcon(icon)
        msg.setStandardButtons(buttons)
        msg.setDefaultButton(QMessageBox.Cancel)

        msg.exec_()
