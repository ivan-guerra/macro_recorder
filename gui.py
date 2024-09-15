from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QHBoxLayout, QWidget, QFileDialog, QSizePolicy, QMessageBox
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt

from recorder import Recorder


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Macro Recorder and Player")

        # Create a central widget and set layout
        central_widget = QWidget()
        layout = QHBoxLayout()  # Use QHBoxLayout to arrange buttons horizontally
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        layout.setSpacing(0)  # Remove spacing between buttons
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Define button images and tooltips
        self.button_info = [
            ("assets/camera.png", "Start/stop a new recording."),
            ("assets/play-pause.png", "Play/pause the last recording."),
            ("assets/diskette.png", "Save current recording."),
            ("assets/open-file.png", "Load a recording."),
            ("assets/help.png", "Display program usage."),
        ]

        # Create buttons with images and tooltips
        self.buttons = []
        for i, (image_path, tooltip_text) in enumerate(self.button_info):
            button = QPushButton()
            pixmap = QPixmap(image_path)
            # Scale image to 32x32
            pixmap = pixmap.scaled(
                32, 32, Qt.AspectRatioMode.IgnoreAspectRatio)
            icon = QIcon(pixmap)
            button.setIcon(icon)
            button.setIconSize(pixmap.size())
            button.setToolTip(tooltip_text)
            # Set initial background color
            button.setStyleSheet("background-color: white;")
            if i == 0:
                button.clicked.connect(
                    lambda _, btn=button: self._toggle_recording(btn))
            if i == 1:  # Apply color toggling to buttons 1 and 2
                button.clicked.connect(
                    lambda _, btn=button: self._toggle_button_color(btn))
            elif i == 2:  # Button 3: Open file save dialog
                button.clicked.connect(self._open_file_save_dialog)
            elif i == 3:  # Button 4: Open file open dialog
                button.clicked.connect(self._open_file_open_dialog)
            elif i == 4:  # Button 5: Open info dialog
                button.clicked.connect(self._open_info_dialog)
            # Ensure button expands
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            layout.addWidget(button)
            self.buttons.append(button)

        # Set the fixed window size
        # Adjust size to accommodate the fifth button
        self.setFixedSize(250, 50)
        self._recorder = Recorder(rate_hz=100.0)

    def _toggle_recording(self, button) -> None:
        current_color = button.styleSheet().split(': ')[1].strip(';')
        if current_color == "white":
            self._recorder.start()
        else:
            self._recorder.stop()

        new_color = 'gray' if current_color == 'white' else 'white'
        button.setStyleSheet(f"background-color: {new_color};")

    def _toggle_button_color(self, button) -> None:
        # Toggle the button's background color between gray and white
        current_color = button.styleSheet().split(': ')[1].strip(';')
        new_color = 'gray' if current_color == 'white' else 'white'
        button.setStyleSheet(f"background-color: {new_color};")

    def _open_file_save_dialog(self) -> None:
        if self._recorder.is_recording():
            QMessageBox.critical(
                self, "Error", "Cannot save while a recording is in progress.")
            return

        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save File", "", "All Files (*);;Text Files (*.txt)", options=options)
        if filename:
            self._recorder.save(filename)

    def _open_file_open_dialog(self) -> None:
        if self._recorder.is_recording():
            QMessageBox.critical(
                self, "Error", "Cannot load recording while a recording is in progress.")
            return

        options = QFileDialog.Options()
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open File", "", "All Files (*);;Text Files (*.txt)", options=options)
        if filename:
            print(f"File opened: {filename}")

    def _open_info_dialog(self) -> None:
        # Open an info dialog box
        QMessageBox.information(
            self, "Information", "TODO")


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
