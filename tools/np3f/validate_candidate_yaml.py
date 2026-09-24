from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


FRAGMENT_RE = re.compile(r"^\s*-\s+name:\s+fragment(\d+)\s*$")
START_RE = re.compile(r"^\s+start:\s+(0x[0-9A-Fa-f]+|\d+)\s*$")
VRAM_RE = re.compile(r"^\s+vram:\s+(0x[0-9A-Fa-f]+|\d+)")

DEFAULT_CATALOG = (
    Path(__file__).resolve().parents[2] / "config" / "np3f_fragments.json"
)


def parse_int(value: str) -> int:
    return int(value, 0)


def parse_fragment_headers(path: Path) -> dict[int, dict[str, int]]:
    found: dict[int, dict[str, int]] = {}
    current: int | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        match = FRAGMENT_RE.match(raw_line)
        if match:
            current = int(match.group(1))
            found.setdefault(current, {})
            continue

        if current is None:
            continue

        match = START_RE.match(raw_line)
        if match:
            found[current]["rom_start"] = parse_int(match.group(1))
            continue

        match = VRAM_RE.match(raw_line)
        if match and "vram" not in found[current]:
            found[current]["vram"] = parse_int(match.group(1))

    return found


def load_catalog(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(candidate: dict[int, dict[str, int]], catalog: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    expected = {
        item["id"]: item for item in catalog.get("fragments", [])
    }

    if len(candidate) != catalog.get("fragment_count"):
        errors.append(
            f"candidate contains {len(candidate)} fragments; "
            f"expected {catalog.get('fragment_count')}"
        )

    for fragment_id in range(1, int(catalog.get("fragment_count", 0)) + 1):
        actual = candidate.get(fragment_id)
        if actual is None:
            errors.append(f"fragment{fragment_id} is missing")
            continue

        ref = expected.get(fragment_id)
        if ref is None:
            errors.append(f"fragment{fragment_id} has no catalog entry")
            continue

        if "rom_start" not in actual:
            errors.append(f"fragment{fragment_id} has no start field")
        elif parse_int(str(ref["rom_start"])) != actual["rom_start"]:
            errors.append(
                f"fragment{fragment_id}: start 0x{actual['rom_start']:X} "
                f"!= catalog 0x{parse_int(str(ref['rom_start'])):X}"
            )

        if "vram" not in actual:
            errors.append(f"fragment{fragment_id} has no vram field")
        else:
            expected_vram = parse_int(str(ref["vram"]))
            if actual["vram"] != expected_vram:
                errors.append(
                    f"fragment{fragment_id}: vram 0x{actual['vram']:08X} "
                    f"!= catalog 0x{expected_vram:08X}"
                )

            if ref.get("confidence") == "guessed":
                warnings.append(
                    f"fragment{fragment_id}: matching a catalog VRAM currently "
                    f"marked guessed; independent validation is still required"
                )

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate NP3F fragment starts and VRAM values in a Splat-style YAML."
    )
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args()

    if not args.candidate.is_file():
        print(f"ERROR: candidate YAML not found: {args.candidate}")
        return 2
    if not args.catalog.is_file():
        print(f"ERROR: catalog not found: {args.catalog}")
        return 2

    candidate = parse_fragment_headers(args.candidate)
    errors, warnings = validate(candidate, load_catalog(args.catalog))

    for warning in warnings:
        print(f"WARNING: {warning}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        f"NP3F candidate YAML: OK ({len(candidate)} fragments; "
        f"{len(warnings)} entries require independent VRAM validation)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
