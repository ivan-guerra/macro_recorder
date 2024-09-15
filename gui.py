#!/usr/bin/env python3
"""Define a GUI that allows the user to record and playback mouse/keyboard macros.

This script provides a graphical frontend to the recorder.py and player.py
scripts.
"""

import json
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QHBoxLayout, QWidget, QFileDialog, QSizePolicy, QMessageBox
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt
from player import Player
from recorder import Recorder, load_records_from_json


class MainWindow(QMainWindow):  # pylint: disable=too-few-public-methods
    """Define the PySide6 main application window."""

    def __init__(self):
        """Construct the main window and macro Recorder/Player instances."""
        super().__init__()
        self.setWindowTitle("Macro Recorder and Player")

        central_widget = QWidget()
        # Use QHBoxLayout to arrange buttons horizontally.
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Define button images and tooltips.
        self.button_info = [
            ("assets/camera.png", "Start/stop a new recording."),
            ("assets/play.png", "Start/stop the current recording."),
            ("assets/diskette.png", "Save current recording."),
            ("assets/open-file.png", "Load a recording."),
            ("assets/help.png", "Display program usage."),
        ]

        self._buttons = []
        for i, (image_path, tooltip_text) in enumerate(self.button_info):
            button = QPushButton()
            pixmap = QPixmap(image_path)
            pixmap = pixmap.scaled(
                32, 32, Qt.AspectRatioMode.IgnoreAspectRatio)
            icon = QIcon(pixmap)
            button.setIcon(icon)
            button.setIconSize(pixmap.size())
            button.setToolTip(tooltip_text)
            button.setStyleSheet("background-color: white;")

            if i == 0:
                button.clicked.connect(
                    lambda _, btn=button: self._toggle_recording(btn))
            if i == 1:
                button.clicked.connect(
                    lambda _, btn=button: self._toggle_playback(btn))
            elif i == 2:
                button.clicked.connect(self._open_file_save_dialog)
            elif i == 3:
                button.clicked.connect(self._open_file_open_dialog)
            elif i == 4:
                button.clicked.connect(self._open_info_dialog)

            # Ensure button expands
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            layout.addWidget(button)
            self._buttons.append(button)

        self.setFixedSize(250, 50)

        self._recorder = Recorder(rate_hz=100.0)
        self._player = Player()
        self._playback_records = []
        self._has_unsaved_data = False

    def _toggle_recording(self, button) -> None:
        current_color = button.styleSheet().split(': ')[1].strip(';')
        if current_color == "white":
            self._recorder.start()
            self._has_unsaved_data = True
        else:
            self._recorder.stop()
            self._playback_records = self._recorder.get_records()

        new_color = "gray" if current_color == "white" else "white"
        button.setStyleSheet(f"background-color: {new_color};")

    def _toggle_playback(self, button) -> None:
        if self._recorder.is_recording():
            QMessageBox.critical(
                self, "Error", "Cannot playback while recording is in progress.")
            return

        if not self._playback_records:
            QMessageBox.critical(
                self, "Error",
                "No data available. Try recording some data or loading data from a file.")
            return

        play_icon = QIcon(QPixmap("assets/play.png"))
        stop_icon = QIcon(QPixmap("assets/stop.png"))

        def playback_complete_cb():
            button.setIcon(play_icon)
            button.setStyleSheet("background-color: white;")

        current_color = button.styleSheet().split(': ')[1].strip(';')
        if current_color == "white":
            button.setIcon(stop_icon)
            button.setStyleSheet("background-color: gray;")
            self._player.start(self._playback_records, playback_complete_cb)
        else:
            button.setIcon(play_icon)
            button.setStyleSheet("background-color: white;")
            self._player.stop()

    def _open_file_save_dialog(self) -> None:
        if self._recorder.is_recording():
            QMessageBox.critical(
                self, "Error", "Cannot save while a recording is in progress.")
            return

        if not self._has_unsaved_data:
            QMessageBox.information(
                self, "Information", "Ignoring save request, there's no recording to save.")
            return

        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", "All Files (*);;Text Files (*.txt)", options=options)
        if filename:
            self._recorder.save(filename)
            self._has_unsaved_data = False

    def _open_file_open_dialog(self) -> None:
        if self._recorder.is_recording():
            QMessageBox.critical(
                self, "Error", "Cannot load files while a recording is in progress.")
            return

        if self._has_unsaved_data:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("Warning")
            msg_box.setText(
                "You have unsaved data. Would you like to overwrite it?")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            result = msg_box.exec()
            if result == QMessageBox.Yes:
                self._playback_records = []
                self._has_unsaved_data = False
            else:
                return

        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "All Files (*);;Text Files (*.txt)", options=options)

        if filename:
            try:
                self._playback_records = load_records_from_json(filename)
            except (json.decoder.JSONDecodeError, ValueError, TypeError, UnicodeDecodeError) as e:
                QMessageBox.critical(
                    self, "Error", f"Failed to read recording: {e}")

    def _open_info_dialog(self) -> None:
        QMessageBox.information(
            self, "Information", "TODO")


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
