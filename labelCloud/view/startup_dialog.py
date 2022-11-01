import random
from typing import List, Optional, Tuple

import pkg_resources
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QValidator
from PyQt5.QtWidgets import (
    QButtonGroup,
    QDesktopWidget,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..definitions.types import LabelingMode
from ..io.labels.config import ClassConfig, LabelConfig
from ..utils.color import get_distinct_colors, hex_to_rgb, rgb_to_hex
from ..view.color_button import ColorButton


class LabelNameValidator(QValidator):
    def validate(self, a0: str, a1: int) -> Tuple["QValidator.State", str, int]:
        if a0 != "":
            return (QValidator.Acceptable, a0, a1)
        return (QValidator.Invalid, a0, a1)


class StartupDialog(QDialog):

    NAME_VALIDATOR = LabelNameValidator()

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

        self.colors: List[str] = []

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setAlignment(Qt.AlignTop)
        self.setLayout(main_layout)

        # 1. Row: Selection of labeling mode via checkable buttons
        self.button_semantic_segmentation: QPushButton
        self.add_labeling_mode_row(main_layout)

        # 2. Row: Definition of class labels
        self.add_class_definition_rows(main_layout)

        # 3. Row: Addition of new class labels
        self.button_add_label = QPushButton(text="Add new label")
        self.button_add_label.clicked.connect(
            lambda: self.add_label(id=self.next_label_id)
        )
        self.delete_buttons.buttonClicked.connect(self.delete_label)
        main_layout.addWidget(self.button_add_label)

        # 4. Row: Buttons to save or cancel
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Save)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        main_layout.addWidget(self.buttonBox)

    # ---------------------------------------------------------------------------- #
    #                                     SETUP                                    #
    # ---------------------------------------------------------------------------- #

    def add_labeling_mode_row(self, parent_layout: QVBoxLayout) -> None:
        """
        Add a row to the dialog to select the labeling mode with two exclusive buttons.
        """
        parent_layout.addWidget(QLabel("Select labeling mode:"))

        row_buttons = QHBoxLayout()

        self.button_object_detection = QPushButton(
            text=LabelingMode.OBJECT_DETECTION.title().replace("_", " ")
        )
        self.button_object_detection.setCheckable(True)
        self.button_object_detection.setToolTip(
            "This will result in a label file for each point cloud\n"
            "with a bounding box for each annotated object."
        )
        row_buttons.addWidget(self.button_object_detection)

        self.button_semantic_segmentation = QPushButton(
            text=LabelingMode.SEMANTIC_SEGMENTATION.title().replace("_", " ")
        )
        self.button_semantic_segmentation.setCheckable(True)
        self.button_semantic_segmentation.setToolTip(
            "This will result in a *.bin file for each point cloud\n"
            "with a label for each annotated point of an object."
        )
        row_buttons.addWidget(self.button_semantic_segmentation)

        parent_layout.addLayout(row_buttons)

        # Click callbacks to switch between the two modes
        def select_object_detection():
            self.button_object_detection.setChecked(True)
            self.button_semantic_segmentation.setChecked(False)

        self.button_object_detection.clicked.connect(select_object_detection)

        def select_semantic_segmentation():
            self.button_semantic_segmentation.setChecked(True)
            self.button_object_detection.setChecked(False)

        self.button_semantic_segmentation.clicked.connect(select_semantic_segmentation)

    def add_class_definition_rows(self, parent_layout: QVBoxLayout) -> None:
        scroll_area = QScrollArea()
        widget = QWidget()
        self.class_labels = QVBoxLayout()
        self.class_labels.addStretch()

        widget.setLayout(self.class_labels)
        self.delete_buttons = QButtonGroup()

        for class_label in LabelConfig().classes:
            self.add_label(
                class_label.id, class_label.name, rgb_to_hex(class_label.color)
            )

        parent_layout.addWidget(QLabel("Change class labels:"))

        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(widget)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        parent_layout.addWidget(scroll_area)
        # Load annotation mode
        if LabelConfig().type == LabelingMode.OBJECT_DETECTION:
            self.button_object_detection.setChecked(True)
        else:
            self.button_semantic_segmentation.setChecked(True)

    # ---------------------------------------------------------------------------- #
    #                                  PROPERTIES                                  #
    # ---------------------------------------------------------------------------- #

    @property
    def get_labeling_mode(self) -> LabelingMode:
        if self.button_object_detection.isChecked():
            return LabelingMode.OBJECT_DETECTION
        return LabelingMode.SEMANTIC_SEGMENTATION

    @property
    def nb_of_labels(self) -> int:
        return len(self.class_labels.children())

    @property
    def next_label_id(self) -> int:
        max_class_id = 0
        for i in range(self.nb_of_labels):
            label_id = int(self.class_labels.itemAt(i).itemAt(0).widget().text())  # type: ignore
            max_class_id = max(max_class_id, label_id)
        return max_class_id + 1

    @property
    def distinct_color(self) -> str:
        if not self.colors:
            self.colors = get_distinct_colors(25)
            random.shuffle(self.colors)
        return self.colors.pop()

    # ---------------------------------------------------------------------------- #
    #                                     LOGIC                                    #
    # ---------------------------------------------------------------------------- #

    def add_label(
        self, id: int, name: Optional[str] = None, hex_color: Optional[str] = None
    ) -> None:
        row_label = QHBoxLayout()
        row_label.setSpacing(15)

        label_id = QSpinBox()
        label_id.setMinimum(0)
        label_id.setMaximum(255)
        label_id.setValue(id)
        row_label.addWidget(label_id)

        label_name = QLineEdit(name or f"label_{id}")
        label_name.setValidator(self.NAME_VALIDATOR)
        row_label.addWidget(label_name, stretch=2)

        label_color = ColorButton(color=hex_color or self.distinct_color)
        row_label.addWidget(label_color)

        label_delete = QPushButton(
            icon=QIcon(
                QPixmap(
                    pkg_resources.resource_filename(
                        "labelCloud.resources.icons", "delete-outline.svg"
                    )
                )
            ),
            text="",
        )
        self.delete_buttons.addButton(label_delete)
        row_label.addWidget(label_delete)

        self.class_labels.insertLayout(self.nb_of_labels, row_label)

    def delete_label(self, delete_button: QPushButton) -> None:
        row_label: QHBoxLayout
        for row_index, row_label in enumerate(self.class_labels.children()):  # type: ignore
            if row_label.itemAt(3).widget() == delete_button:
                for _ in range(row_label.count()):
                    row_label.removeWidget(row_label.itemAt(0).widget())
                break

        self.class_labels.removeItem(self.class_labels.itemAt(row_index))  # type: ignore

    def save_class_labels(self) -> None:
        classes = []
        for i in range(self.nb_of_labels):

            row: QHBoxLayout = self.class_labels.itemAt(i)  # type: ignore
            class_id = int(row.itemAt(0).widget().text())  # type: ignore
            class_name = row.itemAt(1).widget().text()  # type: ignore
            class_color = hex_to_rgb(row.itemAt(2).widget().color())  # type: ignore
            classes.append(ClassConfig(id=class_id, name=class_name, color=class_color))
        LabelConfig().classes = classes
        LabelConfig().type = self.get_labeling_mode
        LabelConfig().save_config()
