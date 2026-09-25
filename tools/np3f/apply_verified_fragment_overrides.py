from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


FRAGMENT_NAME_RE = re.compile(r"^  - name:\s*fragment(\d+)\s*$")
SEGMENT_START_RE = re.compile(
    r"^(?P<prefix>\s+start:\s*)(?P<start>0x[0-9A-Fa-f]+|\d+)(?P<suffix>.*)$"
)
SUBSEGMENT_RE = re.compile(
    r"^(?P<prefix>\s*-\s*\[\s*)"
    r"(?P<start>0x[0-9A-Fa-f]+|\d+)"
    r"(?P<suffix>\s*,.*)$"
)

VERIFIED_INTERNAL_STARTS: dict[str, dict[int, int]] = {
    # Header-adjacent or tail boundaries independently verified against
    # NP3F and the exact NP3E reference ROM.
    "fragment26": {
        1: 0x15E900,
    },
    "fragment28": {
        1: 0x165F10,
        2: 0x166000,
    },
    "fragment31": {
        30: 0x1A0440,
    },
    "fragment36": {
        1: 0x1CEC00,
        2: 0x1D0750,
    },
    "fragment45": {
        5: 0x234B40,
    },
    "fragment71": {
        1: 0x35EDA0,
        2: 0x35FBB0,
    },
    "fragment77": {
        1: 0x369580,
        2: 0x36C930,
    },
    "fragment79": {
        15: 0x38F3B0,
        25: 0x3BEB40,
        40: 0x3D9E80,
    },
    "fragment80": {
        4: 0x41CDE0,
    },
}


def parse_int(value: str) -> int:
    return int(value, 0)


def discover_fragment_headers(rom: bytes) -> dict[str, int]:
    lo = 0xA0000
    hi = 0x440000
    signature = b"FRAGMENT"

    starts: list[int] = []
    pos = lo
    while True:
        hit = rom.find(signature, pos, hi)
        if hit < 0:
            break

        candidate = hit - 8
        if candidate >= lo and candidate % 0x10 == 0:
            starts.append(candidate)

        pos = hit + 1

    if len(starts) != 88:
        raise SystemExit(
            "ERROR: expected exactly 88 aligned primary FRAGMENT headers "
            f"between 0x{lo:X} and 0x{hi:X}; found {len(starts)}"
        )

    if any(b <= a for a, b in zip(starts, starts[1:])):
        raise SystemExit("ERROR: discovered fragment headers are not monotonic")

    return {
        f"fragment{index}": start
        for index, start in enumerate(starts, 1)
    }


def patch_candidate(
    text: str,
    headers: dict[str, int],
) -> tuple[str, list[dict]]:
    output: list[str] = []
    changes: list[dict] = []

    current_fragment: str | None = None
    segment_start_pending = False
    in_subsegments = False
    sub_index = 0

    for line in text.splitlines():
        name_match = FRAGMENT_NAME_RE.match(line)
        if name_match:
            current_fragment = f"fragment{int(name_match.group(1))}"
            segment_start_pending = True
            in_subsegments = False
            sub_index = 0
            output.append(line)
            continue

        if current_fragment is not None and segment_start_pending:
            match = SEGMENT_START_RE.match(line)
            if match:
                old = parse_int(match.group("start"))
                new = headers[current_fragment]
                if old != new:
                    changes.append(
                        {
                            "segment": current_fragment,
                            "kind": "segment_start",
                            "old": old,
                            "new": new,
                            "delta": new - old,
                        }
                    )
                line = (
                    match.group("prefix")
                    + f"0x{new:X}"
                    + match.group("suffix")
                )
                segment_start_pending = False
                output.append(line)
                continue

        if current_fragment is not None and re.match(r"^\s+subsegments:\s*$", line):
            in_subsegments = True
            sub_index = 0
            output.append(line)
            continue

        if in_subsegments and re.match(r"^  - ", line):
            in_subsegments = False
            current_fragment = None

        if in_subsegments and current_fragment is not None:
            match = SUBSEGMENT_RE.match(line)
            if match:
                old = parse_int(match.group("start"))

                if sub_index == 0:
                    new = headers[current_fragment]
                    source = "verified_header"
                else:
                    new = VERIFIED_INTERNAL_STARTS.get(
                        current_fragment, {}
                    ).get(sub_index)
                    source = "verified_internal"

                if new is not None:
                    if old != new:
                        changes.append(
                            {
                                "segment": current_fragment,
                                "kind": f"subsegment_{sub_index}",
                                "source": source,
                                "old": old,
                                "new": new,
                                "delta": new - old,
                            }
                        )
                    line = (
                        match.group("prefix")
                        + f"0x{new:X}"
                        + match.group("suffix")
                    )

                sub_index += 1

        output.append(line)

    banner = [
        "# GENERATED VERIFIED NP3F CANDIDATE.",
        "# Fragment headers are taken directly from aligned on-ROM",
        '# "FRAGMENT" signatures. A small set of independently checked',
        "# internal boundaries resolves fragments that lacked reliable",
        "# relocation anchors.",
        "",
    ]
    return "\n".join(banner + output) + "\n", changes


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Patch the segment-relocated NP3F candidate with exact fragment "
            "header starts discovered directly from the FR ROM, plus a small "
            "set of independently verified internal boundaries."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("build/np3f/analysis/splat-segment-relocated.yaml"),
    )
    parser.add_argument(
        "--rom",
        type=Path,
        default=Path("baseroms/fr/baserom.z64"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/np3f/analysis/splat-segment-verified.yaml"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "build/np3f/analysis/verified_fragment_overrides.json"
        ),
    )
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"ERROR: input candidate not found: {args.input}")
    if not args.rom.is_file():
        raise SystemExit(f"ERROR: NP3F ROM not found: {args.rom}")

    rom = args.rom.read_bytes()
    if len(rom) != 0x4000000:
        raise SystemExit(
            f"ERROR: unexpected NP3F ROM size: {len(rom)} "
            "(expected 67108864)"
        )
    if rom[:4] != bytes.fromhex("80371240"):
        raise SystemExit(
            "ERROR: NP3F ROM must be in native .z64 byte order "
            "(magic 80 37 12 40)"
        )

    headers = discover_fragment_headers(rom)
    text = args.input.read_text(encoding="utf-8")
    patched, changes = patch_candidate(text, headers)

    expected = {
        "fragment26": 0x15E8E0,
        "fragment28": 0x165EF0,
        "fragment36": 0x1CEBE0,
        "fragment71": 0x35ED80,
        "fragment77": 0x369560,
    }
    for name, start in expected.items():
        if headers.get(name) != start:
            raise SystemExit(
                f"ERROR: {name} discovered at 0x{headers.get(name, -1):X}; "
                f"expected verified NP3F start 0x{start:X}"
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(patched, encoding="utf-8")

    report = {
        "input": str(args.input),
        "rom": str(args.rom),
        "output": str(args.output),
        "fragment_headers_found": len(headers),
        "headers": headers,
        "verified_internal_starts": VERIFIED_INTERNAL_STARTS,
        "changes": changes,
        "summary": {
            "total_changes": len(changes),
            "segment_start_changes": sum(
                item["kind"] == "segment_start" for item in changes
            ),
            "subsegment_changes": sum(
                item["kind"].startswith("subsegment_") for item in changes
            ),
        },
    }
    args.report.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Verified NP3F fragment pass:")
    print(f"  exact headers found : {len(headers)} / 88")
    print(f"  YAML changes        : {len(changes)}")
    print(f"  output              : {args.output}")
    print(f"  report              : {args.report}")
    print("")
    for name in ("fragment26", "fragment28", "fragment36", "fragment71", "fragment77"):
        print(f"  {name}: 0x{headers[name]:X}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
