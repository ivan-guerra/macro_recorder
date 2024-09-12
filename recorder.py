#!/usr/bin/env python3
"""Record mouse and keyboard events for later playback.

This script allows the user to record key releases, mouse clicks, and mouse
movement. The script takes command line options that allow the user to adjust
the duration of the recording as well the frequency at which events are
captured. Each recording is output as a CSV file. The output file is meant to
be used as an argument to recorder.py's companion script: playback.py. To see
script usage and all available command line options run: recorder.py -h/--help
"""

import copy
import time
import argparse
import threading
from dataclasses import dataclass
import pynput


@dataclass
class Record:
    """Representation of a single recording event.

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

    def clear(self) -> None:
        """Clear the contents of this Record."""
        self.timestamp = None
        self.mouse_pos = None
        self.key = None
        self.button = None

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

    def _on_release(self, key) -> None:
        try:
            with self._record_lock:
                self._record.key = key.char
        except AttributeError:
            with self._record_lock:
                # Capture special keys (e.g., shift, ctrl).
                self._record.key = str(key)

    def _record_keypress(self) -> None:
        with self._terminate_cv:
            listener = pynput.keyboard.Listener(on_release=self._on_release)
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
                self._record.clear()

            time.sleep(self._rate_sec)

    def __init__(self, rate_hz: int) -> None:
        """Initialize the Recorder with the parameter rate.

        Args
            rate_hz: The rate in Hertz at which records will be recorded.
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
                    "stop called but a recording was never started")
            self._is_recording = False

        with self._terminate_cv:
            self._terminate_cv.notify_all()
        self._keypress_thrd.join()
        self._click_thrd.join()
        self._update_thrd.join()

    def save(self) -> None:
        """Save all records to disk.

        Throws
            RuntimeError: When save() is called during an active recording
            session or when there are no records to save.
        """
        with self._is_recording_lock:
            if self._is_recording:
                raise RuntimeError("failed to save, recording in progress")

        # We don't need to synchronize access to self._records with the update
        # thread since it is guaranteed the Recorder instance was stopped
        # before reaching this point in the code.
        if not self._records:
            raise RuntimeError("failed to save, no data has been recorded")

        outfile = time.strftime("%Y%m%d-%H%M%S") + "_recording.csv"
        with open(outfile, "w", encoding="ascii") as file:
            file.write(
                ",".join(["timestamp", "mouse_x", "mouse_y",
                         "keypressed", "button_clicked"])
                + "\n")
            for r in self._records:
                line = f"{r.timestamp},{r.mouse_pos[0]},{r.mouse_pos[1]},{r.key},{r.button}"
                file.write(f"{line}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="record the mouse and keyboard",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("duration", type=int,
                        help="duration of the recording session in minutes")
    parser.add_argument("--rate-hz", "-r", type=int, default=100,
                        help="rate at which events are recorded in Hertz")
    parser.add_argument("--start-delay-sec", "-d", type=int, default=0,
                        help="number of seconds by which to delay the start of a recording")
    args = parser.parse_args()

    try:
        if args.duration <= 0:
            raise ValueError("duration must be a positive integer")
        if args.rate_hz <= 0:
            raise ValueError("rate_hz must be a positive integer")
        if args.start_delay_sec < 0:
            raise ValueError("start_delay_sec must be >= 0")

        time.sleep(args.start_delay_sec)

        recorder = Recorder(args.rate_hz)
        recorder.start()
        time.sleep(args.duration * 60)
        recorder.stop()
        recorder.save()
    except KeyboardInterrupt:
        recorder.stop()

        answer = input(
            "recording interrupted, would you like to save all events [y/n]? ")
        if answer == "y":
            recorder.save()
    except (RuntimeError, ValueError) as e:
        print(f"error: {e}")
