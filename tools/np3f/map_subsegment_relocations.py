from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from compare_subsegments import collect_subsegments
from n64rom import read_normalized


CODE_TYPES = {"c", "asm", "hasm", "lib"}


def sample_anchor_positions(start: int, end: int, anchor_size: int, max_anchors: int) -> list[int]:
    usable = end - start
    if usable < anchor_size:
        return []

    last = end - anchor_size
    if max_anchors <= 1 or last <= start:
        return [start]

    span = last - start
    step = max(anchor_size, span // (max_anchors - 1))
    positions = list(range(start, last + 1, step))
    if positions[-1] != last:
        positions.append(last)

    if len(positions) > max_anchors:
        indices = [
            round(i * (len(positions) - 1) / (max_anchors - 1))
            for i in range(max_anchors)
        ]
        positions = [positions[i] for i in indices]

    return sorted(set(positions))


def anchor_is_useful(blob: bytes, min_distinct: int) -> bool:
    if not blob:
        return False
    if len(set(blob)) < min_distinct:
        return False
    if blob.count(0) > len(blob) // 2:
        return False
    return True


def find_unique_aligned_match(
    haystack: bytes,
    needle: bytes,
    absolute_start: int,
    alignment: int,
) -> int | None:
    matches: list[int] = []
    cursor = 0

    while True:
        found = haystack.find(needle, cursor)
        if found < 0:
            break

        absolute = absolute_start + found
        if alignment <= 1 or absolute % alignment == 0:
            matches.append(absolute)
            if len(matches) > 1:
                return None

        cursor = found + 1

    return matches[0] if len(matches) == 1 else None


def compare_with_delta(
    fr: bytes,
    us: bytes,
    start: int,
    end: int,
    delta: int,
) -> dict[str, Any]:
    fr_start = start + delta
    fr_end = end + delta

    if fr_start < 0 or fr_end > len(fr):
        return {
            "aligned_equal_bytes": 0,
            "aligned_equal_ratio": 0.0,
            "mapped_fr_start": fr_start,
            "mapped_fr_end": fr_end,
        }

    us_slice = us[start:end]
    fr_slice = fr[fr_start:fr_end]
    equal = sum(a == b for a, b in zip(us_slice, fr_slice))
    size = len(us_slice)

    return {
        "aligned_equal_bytes": equal,
        "aligned_equal_ratio": (equal / size) if size else 1.0,
        "mapped_fr_start": fr_start,
        "mapped_fr_end": fr_end,
    }


def analyze_subsegment(
    fr: bytes,
    us: bytes,
    entry: dict[str, Any],
    window: int,
    anchor_size: int,
    max_anchors: int,
    min_distinct: int,
) -> dict[str, Any]:
    start = int(entry["start"])
    end = int(entry["end"])
    seg_type = str(entry["type"])
    alignment = 4 if seg_type in CODE_TYPES else 1

    sampled = sample_anchor_positions(start, end, anchor_size, max_anchors)
    deltas: list[int] = []
    tested = 0
    unique_hits = 0

    for us_pos in sampled:
        anchor = us[us_pos : us_pos + anchor_size]
        if not anchor_is_useful(anchor, min_distinct):
            continue

        tested += 1
        search_start = max(0, us_pos - window)
        search_end = min(len(fr), us_pos + window + anchor_size)
        match = find_unique_aligned_match(
            fr[search_start:search_end],
            anchor,
            search_start,
            alignment,
        )
        if match is None:
            continue

        unique_hits += 1
        deltas.append(match - us_pos)

    counts = Counter(deltas)
    best_delta: int | None = None
    best_hits = 0
    second_hits = 0

    if counts:
        ranked = sorted(
            counts.items(),
            key=lambda item: (-item[1], abs(item[0]), item[0]),
        )
        best_delta, best_hits = ranked[0]
        if len(ranked) > 1:
            second_hits = ranked[1][1]

    support_ratio = (best_hits / unique_hits) if unique_hits else 0.0

    if best_delta is None:
        status = "no_anchor"
        aligned = {
            "aligned_equal_bytes": 0,
            "aligned_equal_ratio": 0.0,
            "mapped_fr_start": None,
            "mapped_fr_end": None,
        }
    else:
        aligned = compare_with_delta(fr, us, start, end, best_delta)
        if best_hits >= 3 and support_ratio >= 0.60:
            status = "strong"
        elif best_hits >= 2 and support_ratio >= 0.40:
            status = "good"
        else:
            status = "weak"

    return {
        **entry,
        "anchor_size": anchor_size,
        "anchors_tested": tested,
        "unique_anchor_hits": unique_hits,
        "best_delta": best_delta,
        "best_delta_hits": best_hits,
        "second_best_hits": second_hits,
        "support_ratio": support_ratio,
        "status": status,
        **aligned,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Find dominant FR<->US relocation deltas for NP3F Splat subsegments "
            "using exact byte anchors searched around the expected US offset."
        )
    )
    parser.add_argument("--fr", type=Path, default=Path("baseroms/fr/baserom.z64"))
    parser.add_argument("--us", type=Path, required=True)
    parser.add_argument("--yaml", type=Path, default=Path("yamls/fr/splat.yaml"))
    parser.add_argument(
        "--json",
        dest="json_path",
        type=Path,
        default=Path("build/np3f/analysis/subsegment_relocations.json"),
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        type=Path,
        default=Path("build/np3f/analysis/subsegment_relocations.csv"),
    )
    parser.add_argument(
        "--types",
        default="c,asm,hasm,lib",
        help="Comma-separated subsegment types to analyze.",
    )
    parser.add_argument(
        "--window",
        type=lambda value: int(value, 0),
        default=0x4000,
        help="Search radius around each expected anchor position (default: 0x4000).",
    )
    parser.add_argument("--anchor-size", type=int, default=32)
    parser.add_argument("--max-anchors", type=int, default=48)
    parser.add_argument("--min-distinct", type=int, default=8)
    args = parser.parse_args()

    fr = read_normalized(args.fr)
    us = read_normalized(args.us)
    if len(fr) != len(us):
        raise SystemExit(
            f"ERROR: ROM sizes differ: FR={len(fr)} bytes, US={len(us)} bytes."
        )

    try:
        import yaml
    except ImportError as exc:
        raise SystemExit(
            "ERROR: PyYAML is required. Install splat64[mips] first."
        ) from exc

    config = yaml.safe_load(args.yaml.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise SystemExit("ERROR: YAML root must be a mapping.")

    allowed_types = {item.strip() for item in args.types.split(",") if item.strip()}
    entries = [
        entry
        for entry in collect_subsegments(config, len(us))
        if not allowed_types or entry["type"] in allowed_types
    ]

    rows = [
        analyze_subsegment(
            fr,
            us,
            entry,
            args.window,
            args.anchor_size,
            args.max_anchors,
            args.min_distinct,
        )
        for entry in entries
    ]

    statuses = Counter(str(row["status"]) for row in rows)
    delta_counts = Counter(
        int(row["best_delta"])
        for row in rows
        if row["best_delta"] is not None and row["status"] in {"strong", "good"}
    )

    summary = {
        "fr_rom": str(args.fr),
        "us_rom": str(args.us),
        "yaml": str(args.yaml),
        "window": args.window,
        "anchor_size": args.anchor_size,
        "subsegments": len(rows),
        "status_counts": dict(sorted(statuses.items())),
        "top_deltas": [
            {"delta": delta, "count": count}
            for delta, count in delta_counts.most_common(20)
        ],
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
        "best_delta",
        "mapped_fr_start",
        "mapped_fr_end",
        "anchors_tested",
        "unique_anchor_hits",
        "best_delta_hits",
        "second_best_hits",
        "support_ratio",
        "aligned_equal_bytes",
        "aligned_equal_ratio",
        "status",
    ]

    with args.csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            csv_row = {key: row.get(key) for key in fieldnames}
            for key in ("start", "end", "mapped_fr_start", "mapped_fr_end"):
                if csv_row[key] is not None:
                    csv_row[key] = f"0x{int(csv_row[key]):X}"
            if csv_row["best_delta"] is not None:
                delta = int(csv_row["best_delta"])
                csv_row["best_delta"] = f"{delta:+#x}"
            writer.writerow(csv_row)

    print(json.dumps(summary, indent=2))
    print()
    print(f"JSON: {args.json_path}")
    print(f"CSV : {args.csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
