#!/usr/bin/env python3
"""Verify a local N64 dump against the expected NP3F ROM identity."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from np3f.n64rom import detect_byte_order, normalize_to_z64

EXPECTED = {
    "size": 67_108_864,
    "md5": "4748d96916ae2bcc5fc1630515ee2561",
    "sha1": "d7e13535b671024a92822db01507e87bd42f68ec",
    "sha256": "b661d92a94eb3c7a00cd27acc1e93d1e52299bf85a76397ee38e998a84af68ea",
}


def digest(data: bytes, algorithm: str) -> str:
    return hashlib.new(algorithm, data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    args = parser.parse_args()

    if not args.rom.is_file():
        print(f"ERROR: ROM not found: {args.rom}")
        return 2

    raw = args.rom.read_bytes()

    try:
        byte_order = detect_byte_order(args.rom)
        normalized = normalize_to_z64(raw, byte_order)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    print(f"size       : {len(raw)}")
    print(f"byte order : {byte_order}")
    print(f"md5        : {digest(normalized, 'md5')}")
    print(f"sha1       : {digest(normalized, 'sha1')}")
    print(f"sha256     : {digest(normalized, 'sha256')}")

    checks = [
        ("size", len(normalized), EXPECTED["size"]),
        ("md5", digest(normalized, "md5"), EXPECTED["md5"]),
        ("sha1", digest(normalized, "sha1"), EXPECTED["sha1"]),
        ("sha256", digest(normalized, "sha256"), EXPECTED["sha256"]),
    ]

    failed = False
    for name, actual, expected in checks:
        ok = actual == expected
        print(f"{name:10}: {'OK' if ok else 'FAIL'}")
        failed |= not ok

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
