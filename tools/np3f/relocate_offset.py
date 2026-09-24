from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "np3f_fragments.json"


def load_ranges(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["rom_delta_ranges"]


def fragment_delta(fragment: int, ranges: list[dict]) -> int:
    for item in ranges:
        if item["first"] <= fragment <= item["last"]:
            return int(item["delta_bytes"])
    raise ValueError(f"Fragment {fragment} is outside the configured range.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Relocate an NP3E ROM offset into the NP3F candidate position for a known fragment.")
    parser.add_argument("fragment", type=int)
    parser.add_argument("offset", type=lambda value: int(value, 0), help="Reference ROM offset, e.g. 0x0277B4")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()

    delta = fragment_delta(args.fragment, load_ranges(args.config))
    relocated = args.offset + delta

    print(f"fragment : {args.fragment}")
    print(f"delta    : {delta:+d} bytes")
    print(f"reference: 0x{args.offset:06X}")
    print(f"candidate: 0x{relocated:06X}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
