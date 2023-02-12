import random
from typing import List, Optional

import pkg_resources
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...io.labels.config import ClassConfig, LabelConfig
from ...utils.color import get_distinct_colors, hex_to_rgb, rgb_to_hex
from .color_button import ColorButton


class ClassList(QWidget):
    changed = pyqtSignal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.colors: List[str] = []

        self.class_labels = QVBoxLayout()
        self.class_labels.addStretch()

        self.setLayout(self.class_labels)
        self.delete_buttons = QButtonGroup()

        self.delete_buttons.buttonClicked.connect(self._delete_label)

        for class_label in LabelConfig().classes:
            self.add_label(
                class_label.id, class_label.name, rgb_to_hex(class_label.color)
            )

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

    def _get_next_distinct_color(self) -> str:
        if not self.colors:
            self.colors = get_distinct_colors(25)
            random.shuffle(self.colors)
        return self.colors.pop()

    def add_label(
        self,
        id: Optional[int] = None,
        name: Optional[str] = None,
        hex_color: Optional[str] = None,
    ) -> None:
        if id is None:
            id = self.next_label_id

        if name is None:
            name = f"label_{id}"

        if hex_color is None:
            hex_color = self._get_next_distinct_color()

        row_label = QHBoxLayout()
        row_label.setSpacing(15)

        label_id = QSpinBox()
        label_id.setMinimum(0)
        label_id.setMaximum(255)
        label_id.setValue(id)
        row_label.addWidget(label_id)

        label_name = QLineEdit(name)
        row_label.addWidget(label_name, stretch=2)

        label_name.editingFinished.connect(self.changed.emit)

        label_color = ColorButton(color=hex_color)
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

        self.changed.emit()

    def _delete_label(self, delete_button: QPushButton) -> None:
        row_label: QHBoxLayout
        for row_index, row_label in enumerate(self.class_labels.children()):  # type: ignore
            if row_label.itemAt(3).widget() == delete_button:
                class_name = row_label.itemAt(1).widget().text()  # type: ignore

                for _ in range(row_label.count()):
                    row_label.removeWidget(row_label.itemAt(0).widget())
                break

        self.class_labels.removeItem(self.class_labels.itemAt(row_index))  # type: ignore

        self.changed.emit()

    def _get_class_config(self, row_id: int) -> ClassConfig:
        row: QHBoxLayout = self.class_labels.itemAt(row_id)  # type: ignore

        class_id = int(row.itemAt(0).widget().text())  # type: ignore
        class_name = row.itemAt(1).widget().text()  # type: ignore
        class_color = hex_to_rgb(row.itemAt(2).widget().color())  # type: ignore

        return ClassConfig(id=class_id, name=class_name, color=class_color)

    def get_class_configs(self) -> List[ClassConfig]:
        classes = []

        for i in range(self.nb_of_labels):
            classes.append(self._get_class_config(i))

        return classes
