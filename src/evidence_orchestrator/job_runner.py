"""Launch one adapter command only after the broker enables its process tree."""

from __future__ import annotations

import json
import os
import subprocess
import sys

COMMAND_ENV = "EFO_ADAPTER_COMMAND_JSON"


def main() -> int:
    """Wait for the broker gate, then run the configured command."""

    raw = os.environ.pop(COMMAND_ENV, "")
    try:
        command = json.loads(raw)
    except json.JSONDecodeError:
        return 125
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(item, str) and item for item in command)
    ):
        return 125
    if sys.stdin.buffer.readline() != b"start\n":
        return 126
    try:
        completed = subprocess.run(command, check=False, shell=False)
    except OSError:
        return 127
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
