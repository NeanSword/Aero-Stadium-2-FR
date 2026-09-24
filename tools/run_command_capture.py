from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a command, save combined output to a log, and preserve the exit code."
    )
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]

    if not command:
        parser.error("a command is required after --")

    args.log.parent.mkdir(parents=True, exist_ok=True)

    completed = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    args.log.write_text(
        "=== COMMAND ===\n"
        + " ".join(command)
        + "\n\n=== OUTPUT ===\n"
        + (completed.stdout or "")
        + f"\n=== EXIT CODE: {completed.returncode} ===\n",
        encoding="utf-8",
    )

    print(completed.stdout or "", end="")
    print(f"\nLog: {args.log}")
    print(f"Exit code: {completed.returncode}")

    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
