#!/usr/bin/env python3
"""Temp."""

import csv
import time
import argparse
import pyautogui
from recorder import Record


def deserialize_records(record_file: str) -> list[Record]:
    """Read a list of Record objects from the paramater *.mr file."""
    records = []  # pylint: disable=redefined-outer-name
    expected_num_cols = 5

    with open(record_file, "r", encoding="ascii") as file:
        csv_reader = csv.reader(file)
        next(csv_reader)  # Skip the CSV column header.
        for row in csv_reader:
            if len(row) != expected_num_cols:
                raise ValueError(
                    f"invalid number of fields, expected {expected_num_cols} got {len(row)}: {row}")
            records.append(
                Record(float(row[0]), (int(row[1]), int(row[2])), row[3], row[4]))

    return records


def execute_event(record: Record) -> None:
    """Execute the parameter record object."""
    # pyautogui automatically inserts an ~50ms delay on each mouse movement.
    # Setting PAUSE to 0 disables this feature.
    pyautogui.PAUSE = 0

    pyautogui.moveTo(record.mouse_pos)
    # TODO: Execute click.
    # TODO: Execute keypress.


def playback(records: list[Record], speed: float) -> None:  # pylint: disable=redefined-outer-name
    """Playback a set of mouse/keyboard records at the paramater playback speed."""
    for i in range(1, len(records)):
        curr_event = records[i - 1]
        next_event = records[i]
        dt = next_event.timestamp - curr_event.timestamp

        execute_event(curr_event)
        time.sleep(dt / speed)

    execute_event(records[-1])


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
    except (FileNotFoundError, ValueError) as e:
        print(f"error: {e}")
    except KeyboardInterrupt:
        pass
