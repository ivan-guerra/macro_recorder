#!/usr/bin/env python3
"""Playback a mouse/keyboard recording captured with recorder.py.

To see script usage and all available command line options run:
player.py -h/--help
"""

import time
import argparse
import threading
import pynput
import pyautogui
from recorder import Record, load_records_from_json


class Player:  # pylint: disable=too-many-instance-attributes
    """Playback a recording captured by a Recorder object."""

    def _get_key(self, key_str: str):
        # For normal alphabetic characters, we return the character itself.
        if len(key_str) == 1:
            return key_str

        # If it's a special key, we return the corresponding Key object from the Key class.
        if key_str.startswith("Key."):
            return getattr(pynput.keyboard.Key, key_str.split('.')[1])

        return key_str

    def _move_mouse(self, mouse_pos: tuple[int]) -> None:
        # pyautogui automatically inserts a ~50ms delay on each mouse movement.
        # Setting PAUSE to 0 disables this feature.
        pyautogui.PAUSE = 0

        screen_width, screen_height = pyautogui.size()
        if not 0 <= mouse_pos[0] < screen_width:
            raise ValueError(
                f"mouse x coordinate {mouse_pos[0]} out of range [0,{screen_width}]")
        if not 0 <= mouse_pos[1] < screen_height:
            raise ValueError(
                f"mouse y coordinate {mouse_pos[1]} out of range [0,{screen_height}]")
        pyautogui.moveTo(mouse_pos)

    def _click_button(self, button: tuple[str, bool]) -> None:
        if not button:
            return

        button_str, is_pressed = button[0], button[1]
        if button_str in ["Button.left", "Button.right", "Button.middle"]:
            if is_pressed:
                pyautogui.mouseDown(button=button_str.removeprefix("Button."))
            else:
                pyautogui.mouseUp(button=button_str.removeprefix("Button."))
        else:
            raise ValueError(f"unknown button type '{button}'")

    def _scroll(self, scroll: tuple[int, int]) -> None:
        if not scroll:
            return

        dx, dy = scroll[0], scroll[1]
        if dy != 0:
            pyautogui.scroll(dy)
        if dx != 0:
            pyautogui.hscroll(dx)

    def _press_and_release_key_combo(self,
                                     keys: list[tuple[str, float]],
                                     keypress_cache: dict[str, float]) -> None:
        if not keys:
            return

        # To avoid pressing duplicate keys, we must filter keypresses by
        # timestamp. A few special keys are exempt from timestamp filtering.
        key_strs = []
        exempt_keys = ["Key.ctrl", "Key.alt", "Key.shift", "Key.cmd"]
        for key in keys:
            key_str, timestamp = key[0], key[1]
            if key_str in exempt_keys:
                key_strs.append(key_str)
            elif not key_str in keypress_cache or timestamp > keypress_cache[key_str]:
                keypress_cache[key_str] = timestamp
                key_strs.append(key_str)

        # Press and release the key combo.
        keyboard = pynput.keyboard.Controller()
        for k in key_strs:
            key_obj = self._get_key(k)
            keyboard.press(key_obj)
        for k in key_strs:
            key_obj = self._get_key(k)
            keyboard.release(key_obj)

    def _execute_event(self, record: Record, keypress_cache: dict[str, float]) -> None:
        self._move_mouse(record.mouse_pos)
        self._click_button(record.button)
        self._scroll(record.scroll)
        self._press_and_release_key_combo(record.keys, keypress_cache)

    def _playback(self) -> None:  # pylint: disable=redefined-outer-name
        keypress_cache = {}
        for i in range(1, len(self._records)):
            # Check if we need to pause execution.
            with self._pause_cv:
                if self._is_paused:
                    self._pause_cv.wait()

            # Check if we have been asked to stop before the end of the playback.
            with self._stop_requested_lock:
                if self._stop_requested:
                    break

            curr_event = self._records[i - 1]
            next_event = self._records[i]
            dt = next_event.timestamp - curr_event.timestamp

            self._execute_event(curr_event, keypress_cache)

            time.sleep(dt / self._speed)

        self._execute_event(self._records[-1], keypress_cache)

        with self._wait_cv:
            with self._is_playing_lock:
                self._is_playing = False
            self._wait_cv.notify()

    def __init__(self):
        """Construct a mouse/keyboard recording player."""
        self._records = []
        self._speed = 1.0

        self._is_playing = False
        self._is_playing_lock = threading.Lock()
        self._is_paused = False
        self._pause_cv = threading.Condition()
        self._stop_requested = False
        self._stop_requested_lock = threading.Lock()
        self._wait_cv = threading.Condition()
        self._playback_thrd = None

    def start(self, records: list[Record], speed: float = 1.0) -> None:  # pylint: disable=redefined-outer-name
        """Playback the recordings in the parameter list of records."""
        with self._is_playing_lock:
            if self._is_playing:
                raise RuntimeError(
                    "cannot play a new recording while playback is active")

        self._records = records
        self._speed = speed
        self._is_playing = True
        self._is_paused = False
        self._stop_requested = False
        self._playback_thrd = threading.Thread(
            target=self._playback)
        self._playback_thrd.start()

    def pause(self) -> None:
        """Toggle pausing a previously started playback."""
        with self._is_playing_lock:
            if not self._is_playing:
                raise RuntimeError(
                    "pause called but recording is not playing")

        with self._pause_cv:
            if self._is_paused:
                self._is_paused = False
                self._pause_cv.notify()
            else:
                self._is_paused = True

    def wait(self) -> None:
        """Block the calling thread until the recording has finished playing."""
        with self._is_playing_lock:
            if not self._is_playing:
                raise RuntimeError(
                    "wait called but recording is not playing")

        with self._wait_cv:
            self._wait_cv.wait()

    def stop(self) -> None:
        """Stop the active playback."""
        with self._stop_requested_lock:
            self._stop_requested = True

        self._playback_thrd.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="playback a mouse and keyboard recording",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("record_file", type=str,
                        help="a recording captured by recorder.py")
    parser.add_argument("--speed", "-s", type=float, default=1.0,
                        help="speed at which to playback the recording, "
                        "fractional values such as 0.5 allow for a reduction in playback speed")
    args = parser.parse_args()

    try:
        records = load_records_from_json(args.record_file)

        player = Player()
        player.start(records, args.speed)
        player.wait()
    except (FileNotFoundError, ValueError, AttributeError) as e:
        print(f"error: {e}")
    except KeyboardInterrupt:
        pass
