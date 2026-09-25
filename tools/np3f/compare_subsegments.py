from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise SystemExit(
        "ERROR: PyYAML is required. Install the project Splat environment first "
        '(for example: python -m pip install -U "splat64[mips]").'
    ) from exc

from n64rom import read_normalized


def parse_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise TypeError(f"Unsupported ROM address: {value!r}")


def segment_start(segment: Any) -> int | None:
    if isinstance(segment, dict) and "start" in segment:
        return parse_int(segment["start"])
    if isinstance(segment, list) and segment:
        return parse_int(segment[0])
    return None


def collect_subsegments(config: dict[str, Any], rom_size: int) -> list[dict[str, Any]]:
    segments = config.get("segments")
    if not isinstance(segments, list):
        raise ValueError("YAML does not contain a top-level 'segments' list.")

    result: list[dict[str, Any]] = []

    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            continue

        subsegments = segment.get("subsegments")
        if not isinstance(subsegments, list) or not subsegments:
            continue

        next_start = rom_size
        for following in segments[index + 1 :]:
            candidate = segment_start(following)
            if candidate is not None:
                next_start = candidate
                break

        segment_name = str(segment.get("name", f"segment_{index}"))

        for sub_index, subsegment in enumerate(subsegments):
            if not isinstance(subsegment, list) or len(subsegment) < 2:
                continue

            start = parse_int(subsegment[0])
            seg_type = str(subsegment[1])

            if sub_index + 1 < len(subsegments):
                following = subsegments[sub_index + 1]
                if isinstance(following, list) and following:
                    end = parse_int(following[0])
                else:
                    end = next_start
            else:
                end = next_start

            if end < start:
                raise ValueError(
                    f"Invalid range in {segment_name}: 0x{start:X}..0x{end:X}"
                )

            name = (
                str(subsegment[2])
                if len(subsegment) >= 3 and subsegment[2] is not None
                else f"{segment_name}_{start:X}"
            )

            result.append(
                {
                    "segment": segment_name,
                    "subsegment_index": sub_index,
                    "type": seg_type,
                    "name": name,
                    "start": start,
                    "end": end,
                    "size": end - start,
                }
            )

    return result


def compare_range(fr: bytes, us: bytes, start: int, end: int) -> dict[str, Any]:
    if start < 0 or end > len(fr) or end > len(us):
        raise ValueError(f"Range outside ROM: 0x{start:X}..0x{end:X}")

    fr_slice = fr[start:end]
    us_slice = us[start:end]
    size = len(fr_slice)

    equal_bytes = sum(a == b for a, b in zip(fr_slice, us_slice))
    first_diff = next(
        (start + i for i, (a, b) in enumerate(zip(fr_slice, us_slice)) if a != b),
        None,
    )

    return {
        "equal_bytes": equal_bytes,
        "equal_ratio": (equal_bytes / size) if size else 1.0,
        "exact_match": equal_bytes == size,
        "first_diff": first_diff,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare NP3F and NP3E at every subsegment boundary from the NP3F "
            "Splat map. ROMs are normalized to z64 byte order before comparison."
        )
    )
    parser.add_argument("--fr", type=Path, default=Path("baseroms/fr/baserom.z64"))
    parser.add_argument("--us", type=Path, required=True)
    parser.add_argument("--yaml", type=Path, default=Path("yamls/fr/splat.seed.yaml"))
    parser.add_argument(
        "--json",
        dest="json_path",
        type=Path,
        default=Path("build/np3f/analysis/subsegment_diff.json"),
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        type=Path,
        default=Path("build/np3f/analysis/subsegment_diff.csv"),
    )
    parser.add_argument(
        "--types",
        default="c,asm,hasm,lib,textbin,data,rodata,bin",
        help="Comma-separated subsegment types to include.",
    )
    args = parser.parse_args()

    fr = read_normalized(args.fr)
    us = read_normalized(args.us)
    if len(fr) != len(us):
        raise SystemExit(
            f"ERROR: ROM sizes differ: FR={len(fr)} bytes, US={len(us)} bytes."
        )

    config = yaml.safe_load(args.yaml.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise SystemExit("ERROR: YAML root must be a mapping.")

    allowed_types = {item.strip() for item in args.types.split(",") if item.strip()}
    rows: list[dict[str, Any]] = []

    for entry in collect_subsegments(config, len(fr)):
        if allowed_types and entry["type"] not in allowed_types:
            continue
        entry.update(compare_range(fr, us, entry["start"], entry["end"]))
        rows.append(entry)

    exact_count = sum(bool(row["exact_match"]) for row in rows)
    total_bytes = sum(int(row["size"]) for row in rows)
    equal_bytes = sum(int(row["equal_bytes"]) for row in rows)

    summary = {
        "fr_rom": str(args.fr),
        "us_rom": str(args.us),
        "yaml": str(args.yaml),
        "subsegments": len(rows),
        "exact_subsegments": exact_count,
        "changed_subsegments": len(rows) - exact_count,
        "covered_bytes": total_bytes,
        "equal_bytes": equal_bytes,
        "equal_ratio": (equal_bytes / total_bytes) if total_bytes else 0.0,
    }

    payload = {"summary": summary, "subsegments": rows}

    args.json_path.parent.mkdir(parents=True, exist_ok=True)
    args.csv_path.parent.mkdir(parents=True, exist_ok=True)
    args.json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    fieldnames = [
        "segment",
        "subsegment_index",
        "type",
        "name",
        "start",
        "end",
        "size",
        "equal_bytes",
        "equal_ratio",
        "exact_match",
        "first_diff",
    ]
    with args.csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            csv_row = dict(row)
            csv_row["start"] = f"0x{int(row['start']):X}"
            csv_row["end"] = f"0x{int(row['end']):X}"
            if row["first_diff"] is not None:
                csv_row["first_diff"] = f"0x{int(row['first_diff']):X}"
            writer.writerow(csv_row)

    print(json.dumps(summary, indent=2))
    print()
    print(f"JSON: {args.json_path}")
    print(f"CSV : {args.csv_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
