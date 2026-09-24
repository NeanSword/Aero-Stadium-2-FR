from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


FRAGMENT_HINT_RE = re.compile(
    r"^Data segment (?P<data_segment>[^,]+), symbol at vram "
    r"(?P<vram>[0-9A-Fa-f]+) is a jumptable, indicating the start "
    r"of the rodata section _may_ be near here\.$"
)
RODATA_START_RE = re.compile(
    r"^\s*-\s*\[(?P<rom_start>0x[0-9A-Fa-f]+),\s*rodata\]\s*$"
)
TEXT_HINT_RE = re.compile(
    r"^Rodata segment '(?P<rodata_segment>[0-9A-Fa-f]+)' may belong "
    r"to the text segment '(?P<text_segment>[^']+)'$"
)
TEXT_USAGE_RE = re.compile(
    r"^\s*Based on the usage from the function (?P<function>\S+) "
    r"to the symbol (?P<symbol>\S+)\s*$"
)


def parse_splat_hints(text: str) -> dict[str, object]:
    lines = text.splitlines()
    fragment_candidates: list[dict[str, object]] = []
    text_hints: list[dict[str, object]] = []

    for index, line in enumerate(lines):
        fragment_match = FRAGMENT_HINT_RE.match(line)
        if fragment_match:
            rom_start = None
            for following in lines[index + 1 : index + 5]:
                start_match = RODATA_START_RE.match(following)
                if start_match:
                    rom_start = int(start_match.group("rom_start"), 0)
                    break

            if rom_start is not None:
                vram = int(fragment_match.group("vram"), 16)
                fragment_candidates.append(
                    {
                        "data_segment": fragment_match.group("data_segment"),
                        "vram": vram,
                        "vram_hex": f"0x{vram:X}",
                        "rom_start": rom_start,
                        "rom_start_hex": f"0x{rom_start:X}",
                    }
                )
            continue

        text_match = TEXT_HINT_RE.match(line)
        if text_match:
            function = None
            symbol = None
            if index + 1 < len(lines):
                usage_match = TEXT_USAGE_RE.match(lines[index + 1])
                if usage_match:
                    function = usage_match.group("function")
                    symbol = usage_match.group("symbol")

            rodata_segment = int(text_match.group("rodata_segment"), 16)
            text_hints.append(
                {
                    "rodata_segment": rodata_segment,
                    "rodata_segment_hex": f"0x{rodata_segment:X}",
                    "text_segment": text_match.group("text_segment"),
                    "function": function,
                    "symbol": symbol,
                }
            )

    return {
        "summary": {
            "fragment_rodata_candidates": len(fragment_candidates),
            "text_rodata_ownership_hints": len(text_hints),
        },
        "fragment_rodata_candidates": fragment_candidates,
        "text_rodata_ownership_hints": text_hints,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract Splat rodata/jumptable hints into JSON."
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=Path("build/NP3F_SPLAT_EXTRACT.log"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/np3f/analysis/splat_hints.json"),
    )
    args = parser.parse_args()

    payload = parse_splat_hints(
        args.log.read_text(encoding="utf-8", errors="replace")
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(payload["summary"], indent=2))
    print(f"Hints: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
