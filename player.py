#!/usr/bin/env python3
"""Playback a mouse/keyboard recording captured with recorder.py.

To see script usage and all available command line options run:
player.py -h/--help
"""

import json
import time
import argparse
import pynput
import pyautogui
from recorder import Record


def deserialize_records(record_file: str) -> list[Record]:
    """Read a list of Record objects from the paramater *.mr file."""
    data = None
    with open(record_file, "r", encoding="ascii") as file:
        data = json.load(file)

    records = []  # pylint: disable=redefined-outer-name
    for record in data["records"]:
        records.append(Record(
            record["timestamp"],
            record["mouse_pos"],
            record["keys"],
            record["button"],
        ))
    return records


def get_key(key_str: str):
    """Return the pynput key object corresponding to the input string."""
    # For normal alphabetic characters, we return the character itself
    if len(key_str) == 1:
        return key_str

    # If it's a special key, we return the corresponding Key object from the Key class
    if key_str.startswith("Key."):
        return getattr(pynput.keyboard.Key, key_str.split('.')[1])

    return key_str


def execute_event(record: Record, keypress_cache: dict[str, float]) -> None:
    """Execute the parameter record object."""
    # pyautogui automatically inserts an ~50ms delay on each mouse movement.
    # Setting PAUSE to 0 disables this feature.
    pyautogui.PAUSE = 0

    screen_width, screen_height = pyautogui.size()
    if not 0 <= record.mouse_pos[0] < screen_width:
        raise ValueError(
            f"mouse x coordinate {record.mouse_pos[0]} out of range [0,{screen_width}]")
    if not 0 <= record.mouse_pos[1] < screen_height:
        raise ValueError(
            f"mouse y coordinate {record.mouse_pos[1]} out of range [0,{screen_height}]")
    pyautogui.moveTo(record.mouse_pos)

    if record.button != "None":
        if record.button in ["Button.left", "Button.right", "Button.middle"]:
            pyautogui.click(button=record.button.removeprefix("Button."))
        else:
            raise ValueError(f"unknown button type '{record.button}'")

    if record.keys:
        # To avoid pressing duplicate keys, we must filter keypresses by
        # timestamp. A few special keys are exempt from timestamp filtering.
        key_strs = []
        exempt_keys = ["Key.ctrl", "Key.alt", "Key.shift", "Key.cmd"]
        for key in record.keys:
            key_str, timestamp = key[0], key[1]
            if key_str in exempt_keys:
                key_strs.append(key_str)
            elif not key_str in keypress_cache or timestamp > keypress_cache[key_str]:
                keypress_cache[key_str] = timestamp
                key_strs.append(key_str)

        # Press and release the key combo.
        keyboard = pynput.keyboard.Controller()
        for k in key_strs:
            key_obj = get_key(k)
            keyboard.press(key_obj)
        for k in key_strs:
            key_obj = get_key(k)
            keyboard.release(key_obj)


def playback(records: list[Record], speed: float) -> None:  # pylint: disable=redefined-outer-name
    """Playback a set of mouse/keyboard records at the paramater playback speed."""
    keypress_cache = {}
    for i in range(1, len(records)):
        curr_event = records[i - 1]
        next_event = records[i]
        dt = next_event.timestamp - curr_event.timestamp

        execute_event(curr_event, keypress_cache)
        time.sleep(dt / speed)

    execute_event(records[-1], keypress_cache)


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
        records = deserialize_records(args.record_file)
        playback(records, args.speed)
    except (FileNotFoundError, ValueError, AttributeError) as e:
        print(f"error: {e}")
    except KeyboardInterrupt:
        pass
