from __future__ import annotations

import argparse
from pathlib import Path

from n64rom import detect_byte_order, normalize_to_z64


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert an N64 ROM dump to Z64/big-endian byte order."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    if not args.source.is_file():
        raise SystemExit(f"ERROR: source ROM not found: {args.source}")

    data = args.source.read_bytes()
    order = detect_byte_order(args.source)
    normalized = normalize_to_z64(data, order)

    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_bytes(normalized)

    print(f"source     : {args.source}")
    print(f"byte order : {order}")
    print(f"destination: {args.destination}")
    print(f"bytes      : {len(normalized)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
