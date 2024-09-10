#!/usr/bin/env python3
"""Record mouse and keyboard events for later playback."""

import copy
import time
import argparse
import threading
from dataclasses import dataclass
import pynput


@dataclass
class Record:
    """Representation of a macro event.

    Fields
        timestamp: The number of seconds since the Epoch.
        mouse_pos: (x, y) position of the mouse.
        key: The key that was pressed. None if no key was pressed.
        button: The mouse button that was clicked. None if no button was clicked.
    """

    timestamp: int
    mouse_pos: tuple[int]
    key: str
    button: str

    def __str__(self) -> str:
        """Return this Record's string representation."""
        return ",".join([
            f"timestamp={self.timestamp}",
            f"mouse_pos={self.mouse_pos}",
            f"key={self.key}",
            f"button={self.button}",
        ])


class Recorder:  # pylint: disable=too-many-instance-attributes
    """The Recorder class records mouse and keyboard events."""

    def _on_press(self, key) -> None:
        try:
            with self._record_lock:
                self._record.key = key.char
        except AttributeError:
            with self._record_lock:
                # Capture special keys (e.g., shift, ctrl).
                self._record.key = str(key)

    def _record_keypress(self) -> None:
        with self._terminate_cv:
            listener = pynput.keyboard.Listener(on_press=self._on_press)
            listener.start()
            self._terminate_cv.wait()
            listener.stop()

    def _on_click(self, x, y, button, pressed) -> None:  # pylint: disable=unused-argument
        if pressed:
            with self._record_lock:
                self._record.button = button

    def _record_click(self) -> None:
        with self._terminate_cv:
            listener = pynput.mouse.Listener(on_click=self._on_click)
            listener.start()
            self._terminate_cv.wait()
            listener.stop()

    def _update_records(self) -> None:
        while True:
            with self._is_recording_lock:
                if not self._is_recording:
                    break

            with self._record_lock:
                self._record.timestamp = time.time()
                self._record.mouse_pos = pynput.mouse.Controller().position
                self._records.append(copy.deepcopy(self._record))

            time.sleep(self._rate_sec)

    def __init__(self, rate_hz: int) -> None:
        """Initialize the Recorder with the parameter rate.

        Args 
            rate_hz: The rate in Hertz at which state will be recorded.
        """
        self._rate_sec = 1.0 / rate_hz
        self._is_recording = False
        self._record = Record(timestamp=None,
                              mouse_pos=None,
                              key=None,
                              button=None)
        self._records = []

        self._is_recording_lock = threading.Lock()
        self._record_lock = threading.Lock()
        self._terminate_cv = threading.Condition()

        self._keypress_thrd = threading.Thread(
            target=self._record_keypress)
        self._click_thrd = threading.Thread(
            target=self._record_click)
        self._update_thrd = threading.Thread(
            target=self._update_records)

    def start(self) -> None:
        """Begin recording mouse and keyboard events.

        Throws
            RuntimeError: When a new recording is initiated without stopping the previous recording.
        """
        with self._is_recording_lock:
            if self._is_recording:
                raise RuntimeError("recording already in progress")
            self._is_recording = True

        self._keypress_thrd.start()
        self._click_thrd.start()
        self._update_thrd.start()

    def stop(self) -> None:
        """Stop the current recording.

        Throws
            RuntimeError: When stop() is called without a preceding call to start().
        """
        with self._is_recording_lock:
            if not self._is_recording:
                raise RuntimeError(
                    "Recorder.stop() called but a recording was never started")
            self._is_recording = False

        with self._terminate_cv:
            self._terminate_cv.notify_all()
        self._keypress_thrd.join()
        self._click_thrd.join()
        self._update_thrd.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="record the mouse and keyboard",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("duration-min", type=int,
                        help="duration of the recording session in minutes")
    parser.add_argument("--rate-hz", "-r", type=int, default=100,
                        help="rate at which events are recorded in Hertz")
    parser.add_argument("--start-delay-sec", "-d", type=int,
                        help="number of seconds by which to delay the start of a recording")
    args = parser.parse_args()

    recorder = Recorder(args.rate_hz)
    recorder.start()
    print("going to sleep...")
    time.sleep(5)
    print("stopping recorder...")
    recorder.stop()
