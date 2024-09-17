# Macro Recorder

https://github.com/user-attachments/assets/abff9ad7-146d-4ada-9812-984f0cc8d6ce

Record and playback mouse gestures and keystrokes. The scripts included in this
repo allow the user to trigger the recording and playback functions via the
command line or a GUI. Recordings can be saved to a human readable JSON format
that can be later loaded for playback.

### Installation

To run this script, your system must meet the following requirements:

- Windows or Linux OS.
- A working Internet connection.
- [Python3][1]

Follow these steps to install the run environment:

1. Create a Python virtualenv:

```bash
python -m venv mr_venv
```

2. Source the virtual environment:

```bash
mr_venv\Scripts\activate.bat # Windows
source mr_venv/bin/activate.sh # Linux
```

3. Install all dependencies using `pip`:

```bash
pip install -r requirements.txt
```

> **Note**: If you restart the terminal or `deactivate` the venv, you will have
> to activate it again using the command provided in (2).

### Running via GUI

To run the GUI version of the app:

```bash
python gui.py
```

You should see a GUI like the one shown below:

![Macro Recorder GUI](demo/gui.webp)

Here's what each button does going from left to right:

- Toggles recording. If the background of this button is red, it means you're
  currently recording. Each recording overwrites the previous recording. If you
  want to take multiple recordings and save them, you must click the save button
  after each recording.
- Start playback.
- Save recording to disk.
- Load a recording from disk.
- Program settings. Currently, the only configurable options are the playback
  speed and recording rate.

### Running via Command Line

You can record and playback a macro using the `recorder.py` and `player.py`
scripts. Run each script with the `--help` option to see script usage and all
options. Below are some examples of how to run each script.

#### Recording

To create a 1 minute recording with a capture rate of 100HZ run

```bash
./recorder.py 1 --rate-hz 100
```

The command will produce a JSON recording file with the name
`${DATETIME}_recorder.json`. If you'd like to terminate a recording before the
duration timer has expired, press `CTRL+c` in the terminal in which the script
was launched. The script will prompt you as to whether to save the recording up
to the time of termination.

#### Playback

To playback a recording at half speed run

```bash
./player.py ${DATETIME}_recorder.json --speed 0.5
```

[1]: https://www.python.org/downloads/
