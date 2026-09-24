from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from n64rom import read_normalized


def find_identical_runs(left: bytes, right: bytes, minimum: int) -> list[tuple[int, int]]:
    if len(left) != len(right):
        raise ValueError("ROMs must have the same size.")

    runs: list[tuple[int, int]] = []
    start = None

    for index, (a, b) in enumerate(zip(left, right)):
        equal = a == b
        if equal and start is None:
            start = index
        elif not equal and start is not None:
            if index - start >= minimum:
                runs.append((start, index))
            start = None

    if start is not None and len(left) - start >= minimum:
        runs.append((start, len(left)))

    return runs


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two N64 ROM images after byte-order normalization.")
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--min-run", type=int, default=4096)
    parser.add_argument("--json", dest="json_path", type=Path)
    parser.add_argument("--csv", dest="csv_path", type=Path)
    args = parser.parse_args()

    left = read_normalized(args.left)
    right = read_normalized(args.right)

    if len(left) != len(right):
        raise SystemExit("ERROR: ROM sizes differ.")

    equal_bytes = sum(a == b for a, b in zip(left, right))
    runs = find_identical_runs(left, right, args.min_run)

    result = {
        "left": str(args.left),
        "right": str(args.right),
        "size": len(left),
        "identical_bytes": equal_bytes,
        "identical_ratio": equal_bytes / len(left) if left else 0,
        "minimum_identical_run": args.min_run,
        "runs": [
            {"start": start, "end": end, "length": end - start}
            for start, end in runs
        ],
    }

    print(json.dumps(result, indent=2))

    if args.json_path:
        args.json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    if args.csv_path:
        with args.csv_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(("start", "end", "length"))
            writer.writerows(runs)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
