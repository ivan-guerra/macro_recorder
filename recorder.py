#!/usr/bin/env python3
"""Record mouse and keyboard events for later playback.

This script allows the user to record key and mouse events. The script takes
command line options that allow the user to adjust the duration of the
recording as well the frequency at which events are captured. Each recording is
output as a JSON file. The output file is meant to be used as an argument to
recorder.py's companion script: playback.py. To see script usage and all
available command line options run: recorder.py -h/--help
"""

import json
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
        keys: A list of tuples where the first element is the actively pressed
              key and the second element is a timestamp of when the key was pressed.
        button: A tuple where the first element is the mouse button that is
                interacted with and the second element is a boolean indicating whether
                the button was pressed (true) or released (false).
        scroll: A tuple where the first element is the horizontal scroll delta
                and the second element is the vertical scroll delta.
    """

    timestamp: float
    mouse_pos: tuple[int]
    keys: list[tuple[str, int]]
    button: tuple[str, bool]
    scroll: tuple[int, int]

    def clear(self) -> None:
        """Clear the contents of this Record object."""
        self.timestamp = None
        self.mouse_pos = None
        self.keys = None
        self.button = None
        self.scroll = None


def save_records_to_json(json_filepath: str, records: list[Record]) -> None:
    """Output a list of Record objects to a JSON file."""
    if not records:
        raise RuntimeError("failed to save, list of records is empty")

    with open(json_filepath, "w", encoding="ascii") as file:
        record_dicts = []
        for r in records:
            record_dict = {
                "timestamp": r.timestamp,
                "mouse_pos": r.mouse_pos,
                "keys": r.keys,
                "button": r.button,
                "scroll": r.scroll
            }
            record_dicts.append(record_dict)
        output = {"records": record_dicts}
        json.dump(output, file, indent=2)


def load_records_from_json(json_filepath: str) -> list[Record]:
    """Read a list of Record objects from the parameter JSON file."""
    with open(json_filepath, "r", encoding="ascii") as file:
        data = json.load(file)
        records = []
        for record in data["records"]:
            records.append(Record(
                record["timestamp"],
                record["mouse_pos"],
                record["keys"],
                record["button"],
                record["scroll"],
            ))
    return records


class Recorder:  # pylint: disable=too-many-instance-attributes
    """The Recorder class records mouse and keyboard events."""

    def _on_release(self, key) -> None:
        def update_keys(key_str: str) -> None:
            with self._active_keys_lock:
                if self._active_keys:
                    with self._record_lock:
                        self._record.keys = copy.deepcopy(self._active_keys)
                        self._active_keys = [
                            x for x in self._active_keys if x[0] != key_str]

        if hasattr(key, "char"):
            update_keys(str(key.char))
        else:
            update_keys(str(key))

    def _on_press(self, key) -> None:
        with self._active_keys_lock:
            if hasattr(key, "char"):
                # Capture single character keys.
                self._active_keys.append((str(key.char), time.time()))
            else:
                # Capture special keys (e.g., shift, ctrl).
                self._active_keys.append((str(key), time.time()))

    def _record_key_events(self) -> None:
        with self._terminate_cv:
            press_listener = pynput.keyboard.Listener(on_press=self._on_press)
            release_listener = pynput.keyboard.Listener(
                on_release=self._on_release)

            press_listener.start()
            release_listener.start()

            self._terminate_cv.wait()

            press_listener.stop()
            release_listener.stop()

    def _on_click(self, x, y, button, is_pressed) -> None:  # pylint: disable=unused-argument
        with self._record_lock:
            self._record.button = (str(button), is_pressed)

    def _on_scroll(self, x, y, dx, dy) -> None:  # pylint: disable=unused-argument
        with self._record_lock:
            if dy > 0 or dy < 0:
                self._record.scroll = (0, dy)
            if dx > 0 or dx < 0:
                self._record.scroll = (dx, 0)

    def _record_mouse_events(self) -> None:
        with self._terminate_cv:
            click_listener = pynput.mouse.Listener(on_click=self._on_click)
            scroll_listener = pynput.mouse.Listener(on_scroll=self._on_scroll)

            click_listener.start()
            scroll_listener.start()

            self._terminate_cv.wait()

            click_listener.stop()
            scroll_listener.stop()

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

    def __init__(self) -> None:
        """Initialize the Recorder."""
        self._rate_sec = 1.0
        self._is_recording = False
        self._record = Record(timestamp=None,
                              mouse_pos=None,
                              keys=None,
                              button=None,
                              scroll=None)
        self._records = []
        self._active_keys = []

        self._is_recording_lock = threading.Lock()
        self._record_lock = threading.Lock()
        self._active_keys_lock = threading.Lock()
        self._terminate_cv = threading.Condition()

        self._keypress_thrd = None
        self._click_thrd = None
        self._update_thrd = None

    def start(self, rate_hz: int = 100) -> None:
        """Begin recording mouse and keyboard events.

        Args 
            rate_hz: The rate at which the state of the mouse and keyboard is
                     recorded in Hertz.

        Throws
            RuntimeError: When a new recording is initiated without stopping the previous recording.
        """
        with self._is_recording_lock:
            if self._is_recording:
                raise RuntimeError("recording already in progress")
            self._is_recording = True

        self._rate_sec = 1.0 / rate_hz
        self._records = []
        self._active_keys = []

        self._keypress_thrd = threading.Thread(
            target=self._record_key_events)
        self._click_thrd = threading.Thread(
            target=self._record_mouse_events)
        self._update_thrd = threading.Thread(
            target=self._update_records)

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

    def is_recording(self) -> bool:
        """Return the state of this Recorder."""
        with self._is_recording_lock:
            return self._is_recording

    def get_records(self) -> list[Record]:
        """Return all recorded Record objects."""
        with self._is_recording_lock:
            if self._is_recording:
                raise RuntimeError(
                    "cannot return records during active recording")
        return self._records

    def save(self, json_filepath: str) -> None:
        """Save all records to disk.

        Throws
            RuntimeError: When save() is called during an active recording
                          session or when there are no records to save.
        """
        with self._is_recording_lock:
            if self._is_recording:
                raise RuntimeError("failed to save, recording in progress")

        save_records_to_json(json_filepath, self._records)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="record mouse and keyboard events",
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
            raise ValueError("rate-hz must be a positive integer")
        if args.start_delay_sec < 0:
            raise ValueError(
                "start-delay-sec must be greater than or equal to 0")

        outfile = time.strftime("%Y%m%d-%H%M%S") + "_recording.json"

        time.sleep(args.start_delay_sec)

        recorder = Recorder()
        recorder.start(args.rate_hz)

        time.sleep(args.duration * 60)

        recorder.stop()
        recorder.save(outfile)
    except KeyboardInterrupt:
        recorder.stop()

        answer = input(
            "recording interrupted, would you like to save all events [y/n]? ")
        if answer == "y":
            recorder.save(outfile)
    except (RuntimeError, ValueError) as e:
        print(f"error: {e}")
