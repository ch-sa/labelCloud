from typing import Optional

from PyQt5 import QtCore, QtWidgets

from ..definitions import Context, Mode


class StatusManager:
    def __init__(self, status_bar: QtWidgets.QStatusBar) -> None:
        self.status_bar = status_bar

        # Add permanent status label
        self.mode_label = QtWidgets.QLabel("Navigation Mode")
        self.mode_label.setStyleSheet(
            "font-weight: bold; font-size: 14px; min-width: 275px;"
        )
        self.mode_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_bar.addWidget(self.mode_label, stretch=0)

        # Add temporary status message / tips
        self.message_label = QtWidgets.QLabel()
        self.message_label.setStyleSheet("font-size: 14px;")
        self.message_label.setAlignment(QtCore.Qt.AlignLeft)
        self.status_bar.addWidget(self.message_label, stretch=1)

        # Yiming added **New: coordinate label on the right**
        # self.coord_label = QtWidgets.QLabel("3D Cursor: (X, Y, Z)")
        # self.coord_label.setStyleSheet("font-size: 14px; min-width: 180px;")
        # self.coord_label.setAlignment(QtCore.Qt.AlignRight)
        # self.status_bar.addPermanentWidget(self.coord_label, stretch=0)

        # Yiming added - Coordinate and rotation display
        self.coord_label = QtWidgets.QLabel("Cursor: (X: -, Y: -, Z: -)")
        self.rotation_label = QtWidgets.QLabel("Camera: (Pitch: -, Yaw: -)")
        
        # Style setup
        for label in [self.coord_label, self.rotation_label]:
            label.setStyleSheet("font-size: 14px; min-width: 180px;")
            label.setAlignment(QtCore.Qt.AlignRight)
        
        self.status_bar.addPermanentWidget(self.coord_label, stretch=0)
        self.status_bar.addPermanentWidget(self.rotation_label, stretch=0)

        self.msg_context = Context.DEFAULT

    # Yiming added: add method to update coordinate text
    # def set_coordinates(self, x: float, y: float, z: float) -> None:
    #     self.coord_label.setText(f"3D Cursor: ({x:.2f}, {y:.2f}, {z:.2f})")

    def set_coordinates(self, x: float, y: float, z: float) -> None:
        self.coord_label.setText(f"Cursor: (X: {x:.2f}, Y: {y:.2f}, Z: {z:.2f})")
    
    def set_camera_rotation(self, rot_x: float, rot_z: float) -> None:
        self.rotation_label.setText(f"Camera: (Pitch: {rot_x:.1f}°, Yaw: {rot_z:.1f}°)")

    def set_mode(self, mode: Mode) -> None:
        self.mode_label.setText(mode.value)

    def set_message(self, message: str, context: Context = Context.DEFAULT) -> None:
        if context >= self.msg_context:
            self.message_label.setText(message)
            self.msg_context = context

    def clear_message(self, context: Optional[Context] = None):
        if context == None or context == self.msg_context:
            self.msg_context = Context.DEFAULT
            self.set_message("")

    def update_status(
        self,
        message: str,
        mode: Optional[Mode] = None,
        context: Context = Context.DEFAULT,
    ):
        self.set_message(message, context)

        if mode:
            self.set_mode(mode)
