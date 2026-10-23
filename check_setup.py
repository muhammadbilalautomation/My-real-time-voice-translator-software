"""Check the local development environment without recording audio."""

import importlib.metadata
import json
import platform
import sys
import tkinter

import numpy
import sounddevice


def main():
    interpreter = tkinter.Tcl()
    devices = sounddevice.query_devices()
    report = {
        "python": sys.version,
        "executable": sys.executable,
        "architecture": platform.architecture()[0],
        "tcl_version": interpreter.call("info", "patchlevel"),
        "numpy": numpy.__version__,
        "sounddevice": importlib.metadata.version("sounddevice"),
        "default_audio_devices": list(sounddevice.default.device),
        "audio_devices": [dict(device) for device in devices],
        "recording_started": False,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
