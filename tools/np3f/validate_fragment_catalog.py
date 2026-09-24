from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    fragments = data.get("fragments", [])

    if data.get("fragment_count") != 88:
        errors.append("fragment_count must be 88")
    if len(fragments) != 88:
        errors.append(f"expected 88 fragment entries, got {len(fragments)}")

    ids = [item.get("id") for item in fragments]
    if ids != list(range(1, 89)):
        errors.append("fragment ids must be exactly 1..88")

    starts = []
    for item in fragments:
        try:
            starts.append(int(str(item["rom_start"]), 0))
            int(str(item["vram"]), 0)
        except (KeyError, TypeError, ValueError):
            errors.append(f"invalid fragment entry: {item}")

    if starts and starts != sorted(starts):
        errors.append("fragment ROM starts must be strictly increasing")
    if len(starts) != len(set(starts)):
        errors.append("fragment ROM starts must be unique")

    end = int(str(data["fragment_rom_end"]), 0)
    if starts and starts[-1] >= end:
        errors.append("final fragment start must be before fragment_rom_end")

    ranges = data.get("rom_delta_ranges", [])
    covered = []
    for item in ranges:
        first = int(item["first"])
        last = int(item["last"])
        if first > last:
            errors.append(f"invalid delta range: {item}")
        covered.extend(range(first, last + 1))
    if sorted(covered) != list(range(1, 89)):
        errors.append("ROM delta ranges must cover every fragment exactly once")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()

    errors = validate(load(args.config))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    guessed = sum(1 for item in load(args.config)["fragments"]
                  if item.get("confidence") == "guessed")
    print(f"NP3F fragment catalog: OK (88 fragments, {guessed} guessed VRAM entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
