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

        self.msg_context = Context.DEFAULT

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
