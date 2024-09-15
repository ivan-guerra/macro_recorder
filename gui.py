#!/usr/bin/env python3
"""Define a GUI that allows the user to record and playback mouse/keyboard macros.

This script provides a graphical frontend to the recorder.py and player.py
scripts.
"""

import json
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton,
                               QHBoxLayout, QWidget, QFileDialog,
                               QSizePolicy, QMessageBox, QDialog,
                               QLineEdit, QFormLayout, QVBoxLayout)
from recorder import Recorder, load_records_from_json
from player import Player


class ProgramSettingsDialog(QDialog):  # pylint: disable=too-few-public-methods
    """Define a program settings input dialog box."""

    def __init__(self):
        """Construct the dialog box."""
        super().__init__()
        self.setWindowTitle("Recorder Settings")

        layout = QVBoxLayout()
        form_layout = QFormLayout()
        self._speed_input = QLineEdit(self)
        self._rate_input = QLineEdit(self)

        form_layout.addRow("Playback Speed Multiplier:", self._speed_input)
        form_layout.addRow("Rate of Recording (Hz):", self._rate_input)
        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        self._ok_button = QPushButton("OK")
        self._cancel_button = QPushButton("Cancel")
        button_layout.addWidget(self._ok_button)
        button_layout.addWidget(self._cancel_button)

        self._ok_button.clicked.connect(self.accept)
        self._cancel_button.clicked.connect(self.reject)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def get_inputs(self) -> tuple[str, str]:
        """Return a tuple containing the playback speed and recording rate strings."""
        return self._speed_input.text(), self._rate_input.text()


class MainWindow(QMainWindow):  # pylint: disable=too-few-public-methods, too-many-instance-attributes
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
            ("assets/settings.png", "Display program settings."),
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
                button.clicked.connect(self._open_settings_dialog)

            # Ensure button expands
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            layout.addWidget(button)
            self._buttons.append(button)

        self.setFixedSize(250, 50)

        self._recorder = Recorder()
        self._player = Player()
        self._playback_records = []
        self._has_unsaved_data = False
        self._record_rate_hz = 100
        self._playback_multiplier = 1.0

    def _toggle_recording(self, button) -> None:
        current_color = button.styleSheet().split(': ')[1].strip(';')
        if current_color == "white":
            self._recorder.start(rate_hz=self._record_rate_hz)
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
            self._player.start(
                self._playback_records, playback_complete_cb, speed=self._playback_multiplier)
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

    def _open_settings_dialog(self) -> None:
        dialog = ProgramSettingsDialog()
        if dialog.exec() == QDialog.Accepted:
            playback_multiplier, record_rate_hz = dialog.get_inputs()
            try:
                if playback_multiplier:
                    multiplier = float(playback_multiplier)
                    if multiplier <= 0.0:
                        raise ValueError()

                    self._playback_multiplier = multiplier
            except (TypeError, ValueError):
                QMessageBox.critical(
                    self, "Error", "Playback multiplier must be a positive floating point value.")

            try:
                if record_rate_hz:
                    rate = int(record_rate_hz)
                    if rate <= 0:
                        raise ValueError

                    self._record_rate_hz = rate
            except (TypeError, ValueError):
                QMessageBox.critical(
                    self, "Error", "Recording rate must be a positive integer.")


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
