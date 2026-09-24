#!/usr/bin/env python3
"""Verify that a local ROM matches the expected NP3F reference."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

EXPECTED = {
    "size": 67_108_864,
    "md5": "4748d96916ae2bcc5fc1630515ee2561",
    "sha1": "d7e13535b671024a92822db01507e87bd42f68ec",
    "sha256": "b661d92a94eb3c7a00cd27acc1e93d1e52299bf85a76397ee38e998a84af68ea",
}


def digest(path: Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    args = parser.parse_args()

    if not args.rom.is_file():
        print(f"ERROR: ROM not found: {args.rom}")
        return 2

    size = args.rom.stat().st_size
    md5 = digest(args.rom, "md5")
    sha1 = digest(args.rom, "sha1")
    sha256 = digest(args.rom, "sha256")

    print(f"size   : {size}")
    print(f"md5    : {md5}")
    print(f"sha1   : {sha1}")
    print(f"sha256 : {sha256}")

    checks = [
        ("size", size, EXPECTED["size"]),
        ("md5", md5.lower(), EXPECTED["md5"]),
        ("sha1", sha1.lower(), EXPECTED["sha1"]),
        ("sha256", sha256.lower(), EXPECTED["sha256"]),
    ]

    failed = False
    for name, actual, expected in checks:
        ok = actual == expected
        print(f"{name:6}: {'OK' if ok else 'FAIL'}")
        failed |= not ok

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
