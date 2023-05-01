import logging
from pathlib import Path
from typing import List, Tuple

from PyQt5 import QtCore
from PyQt5.QtWidgets import QInputDialog, QWidget


class PointCloudIndexSelector:
    def __init__(
        self, parent: QWidget, point_cloud_paths: List[Path], start_index: int
    ) -> None:
        """A dialog that asks for the index of the next point cloud.

         - automatically updates the label with the related point cloud file name

        Args:
            point_cloud_paths: All point cloud paths in the current point cloud folder
            start_index: Index of the current point cloud (0 = first in list)
        """
        self._dialog = QInputDialog(parent, QtCore.Qt.WindowType.Dialog)

        self._dialog.setInputMode(QInputDialog.IntInput)
        self._dialog.setWindowTitle("Change to another point cloud")
        self._dialog.setLabelText("Insert Point Cloud number:")

        self.point_cloud_paths = point_cloud_paths

        self._dialog.setIntMaximum(len(self.point_cloud_paths) - 1)

        self._dialog.intValueChanged.connect(lambda index: self._update_label(index))
        self._dialog.setIntValue(start_index)

    def _update_label(self, index: int) -> None:
        pcd_path = self.point_cloud_paths[index]
        self._dialog.setLabelText(f"Insert Point Cloud number: {pcd_path.name}")

    def get_index(self) -> Tuple[int, bool]:
        """Get the index of the selected point cloud and if it was accepted."""
        result = self._dialog.exec_()
        index = self._dialog.intValue()
        ok = result == QInputDialog.Accepted
        return index, ok
