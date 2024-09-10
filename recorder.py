#!/usr/bin/env python3
"""Record mouse and keyboard events for later playback."""

import argparse
from dataclasses import dataclass


@dataclass
class Record:
    """Representation of macro event.

    Fields
        timestamp: The number of seconds since the Epoch.
        mouse_pos: x,y position of the mouse.
        keypress: The key that was pressed. None if no key was pressed.
        button: The mouse button that was clicked. None if no button was clicked.
    """

    timestamp: int
    mouse_pos: tuple[int]
    keypress: str
    button: str

    def __str__(self) -> str:
        """Return this Record's string representation."""
        return ",".join([
            f"timestamp={self.timestamp}",
            f"mouse_pos={self.mouse_pos}",
            f"keypress={self.keypress}",
            f"button={self.button}",
        ])


class Recorder:
    """The Recorder class records mouse and keyboard events."""

    def __init__(self, rate_hz: int, duration_min: int) -> None:
        """Initialize the Recorder with the parameter rate and duration.

        Args 
            rate_hz: The rate in Hertz at which state will be recorded.
            duration_min: The duration of the recording in minutes.
        """
        self._rate_hz = rate_hz
        self._duration_min = duration_min
        self._is_recording = False

    def start(self):
        return None

    def stop(self):
        return None

    def save(self):
        return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="record the mouse and keyboard",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("duration-min", type=int,
                        help="duration of the recording session in minutes")
    parser.add_argument("--rate-hz", "-r", type=int, default=100,
                        help="rate at which events are recorded in Hertz")
    args = parser.parse_args()
