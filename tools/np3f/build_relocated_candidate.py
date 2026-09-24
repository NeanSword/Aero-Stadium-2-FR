from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise SystemExit(
        'ERROR: PyYAML is required. Install the project Splat environment first '
        '(for example: python -m pip install -U "splat64[mips]").'
    ) from exc


SEGMENT_RE = re.compile(r"^fragment\d+$")
SUBSEGMENT_LINE_RE = re.compile(
    r"^(?P<prefix>\s*-\s*\[\s*)(?P<start>0x[0-9A-Fa-f]+|\d+)(?P<suffix>.*)$"
)


def parse_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise TypeError(f"Unsupported ROM address: {value!r}")


def eligible_anchor(row: dict[str, Any], min_good_ratio: float) -> bool:
    delta = row.get("best_delta")
    if delta is None:
        return False

    status = str(row.get("status", ""))
    hits = int(row.get("best_delta_hits", 0))
    support = float(row.get("support_ratio", 0.0))
    ratio = float(row.get("aligned_equal_ratio", 0.0))

    if status == "strong":
        return hits >= 3 and support >= 0.60

    if status == "good":
        return (
            hits >= 2
            and support >= 0.50
            and ratio >= min_good_ratio
        )

    return False


def segment_end(segments: list[Any], index: int, rom_size: int) -> int:
    for following in segments[index + 1 :]:
        if isinstance(following, dict) and "start" in following:
            return parse_int(following["start"])
        if isinstance(following, list) and following:
            return parse_int(following[0])
    return rom_size


def nearest_direct(
    direct: dict[int, dict[str, Any]],
    index: int,
    direction: int,
    count: int,
) -> dict[str, Any] | None:
    cursor = index + direction
    while 0 <= cursor < count:
        item = direct.get(cursor)
        if item is not None:
            return item
        cursor += direction
    return None


def build_segment_proposal(
    segment: dict[str, Any],
    direct: dict[int, dict[str, Any]],
    seg_end: int,
) -> dict[str, Any]:
    name = str(segment.get("name", ""))
    subsegments = segment.get("subsegments")
    if not isinstance(subsegments, list) or not subsegments:
        return {"segment": name, "status": "skipped", "reason": "no_subsegments"}

    if not direct:
        return {"segment": name, "status": "skipped", "reason": "no_reliable_anchor"}

    proposals: list[dict[str, Any]] = []
    count = len(subsegments)

    for index, subsegment in enumerate(subsegments):
        if not isinstance(subsegment, list) or len(subsegment) < 2:
            return {
                "segment": name,
                "status": "skipped",
                "reason": f"unsupported_subsegment_shape_{index}",
            }

        old_start = parse_int(subsegment[0])
        seg_type = str(subsegment[1])
        new_start = old_start
        source = "preserved"
        delta = 0

        if index == 0:
            source = "fixed_segment_start"
        elif index in direct:
            delta = int(direct[index]["best_delta"])
            new_start = old_start + delta
            source = "direct_anchor"
        else:
            left = nearest_direct(direct, index, -1, count)
            right = nearest_direct(direct, index, 1, count)
            if (
                left is not None
                and right is not None
                and int(left["best_delta"]) == int(right["best_delta"])
            ):
                delta = int(left["best_delta"])
                new_start = old_start + delta
                source = "inferred_same_delta"
            elif (
                left is not None
                and right is None
                and seg_type in {"data", "rodata", "bin"}
            ):
                candidate_delta = int(left["best_delta"])
                candidate_start = old_start + candidate_delta
                if candidate_start < seg_end:
                    delta = candidate_delta
                    new_start = candidate_start
                    source = "inferred_tail_delta"

        proposals.append(
            {
                "index": index,
                "type": seg_type,
                "old_start": old_start,
                "new_start": new_start,
                "delta": delta,
                "source": source,
            }
        )

    seg_start = parse_int(segment.get("start", proposals[0]["old_start"]))

    if proposals[0]["new_start"] != seg_start:
        return {
            "segment": name,
            "status": "skipped",
            "reason": "segment_start_would_move",
            "proposals": proposals,
        }

    for previous, current in zip(proposals, proposals[1:]):
        if current["new_start"] <= previous["new_start"]:
            return {
                "segment": name,
                "status": "skipped",
                "reason": (
                    "non_monotonic_"
                    f"{previous['index']}_{current['index']}"
                ),
                "proposals": proposals,
            }

    if proposals[-1]["new_start"] >= seg_end:
        return {
            "segment": name,
            "status": "skipped",
            "reason": "last_subsegment_crosses_segment_end",
            "proposals": proposals,
        }

    changes = [
        item for item in proposals
        if item["new_start"] != item["old_start"]
    ]

    return {
        "segment": name,
        "status": "applied",
        "reason": None,
        "changes": len(changes),
        "direct_changes": sum(
            item["source"] == "direct_anchor" for item in changes
        ),
        "inferred_changes": sum(
            str(item["source"]).startswith("inferred_") for item in changes
        ),
        "same_delta_inferred_changes": sum(
            item["source"] == "inferred_same_delta" for item in changes
        ),
        "tail_inferred_changes": sum(
            item["source"] == "inferred_tail_delta" for item in changes
        ),
        "proposals": proposals,
    }


def patch_yaml_text(
    original: str,
    applied: dict[str, dict[int, int]],
) -> str:
    output: list[str] = []
    current_segment: str | None = None
    in_subsegments = False
    sub_index = 0

    for line in original.splitlines():
        segment_match = re.match(r"^  - name:\s*(.+?)\s*$", line)
        if segment_match:
            current_segment = segment_match.group(1).strip().strip("\"'")
            in_subsegments = False
            sub_index = 0
            output.append(line)
            continue

        if current_segment is not None and re.match(
            r"^\s+subsegments:\s*$", line
        ):
            in_subsegments = True
            sub_index = 0
            output.append(line)
            continue

        if in_subsegments:
            match = SUBSEGMENT_LINE_RE.match(line)
            if match:
                replacement = applied.get(current_segment, {}).get(sub_index)
                if replacement is not None:
                    line = (
                        match.group("prefix")
                        + f"0x{replacement:X}"
                        + match.group("suffix")
                    )
                sub_index += 1
                output.append(line)
                continue

            if re.match(r"^  - ", line):
                in_subsegments = False

        output.append(line)

    banner = [
        "# GENERATED CANDIDATE - do not treat as the canonical NP3F map yet.",
        "# Built from exact NP3F/NP3E relocation anchors.",
        "# Source: yamls/fr/splat.yaml",
        "",
    ]
    return "\n".join(banner + output) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a conservative NP3F Splat candidate by applying reliable "
            "FR<->US relocation anchors to fragment subsegment starts."
        )
    )
    parser.add_argument(
        "--yaml",
        type=Path,
        default=Path("yamls/fr/splat.yaml"),
    )
    parser.add_argument(
        "--relocations",
        type=Path,
        default=Path(
            "build/np3f/analysis/subsegment_relocations.json"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "build/np3f/analysis/splat-relocated.yaml"
        ),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "build/np3f/analysis/relocation_application.json"
        ),
    )
    parser.add_argument(
        "--rom-size",
        type=lambda value: int(value, 0),
        default=0x4000000,
    )
    parser.add_argument(
        "--min-good-ratio",
        type=float,
        default=0.75,
        help=(
            "Minimum aligned equality ratio for status=good anchors. "
            "Strong anchors are accepted by hit/support evidence."
        ),
    )
    args = parser.parse_args()

    original_text = args.yaml.read_text(encoding="utf-8")
    config = yaml.safe_load(original_text)
    if not isinstance(config, dict):
        raise SystemExit("ERROR: YAML root must be a mapping.")

    relocation_payload = json.loads(
        args.relocations.read_text(encoding="utf-8")
    )
    relocation_rows = relocation_payload.get("subsegments")
    if not isinstance(relocation_rows, list):
        raise SystemExit(
            "ERROR: relocation report does not contain a subsegments list."
        )

    segments = config.get("segments")
    if not isinstance(segments, list):
        raise SystemExit("ERROR: YAML does not contain a segments list.")

    accepted: dict[tuple[str, int], dict[str, Any]] = {}
    rejected_suspicious: list[dict[str, Any]] = []

    for row in relocation_rows:
        if not isinstance(row, dict):
            continue

        segment_name = str(row.get("segment", ""))
        sub_index = int(row.get("subsegment_index", -1))

        if eligible_anchor(row, args.min_good_ratio):
            accepted[(segment_name, sub_index)] = row
        elif (
            row.get("best_delta") is not None
            and str(row.get("status", "")) in {"strong", "good"}
        ):
            rejected_suspicious.append(
                {
                    "segment": segment_name,
                    "subsegment_index": sub_index,
                    "name": row.get("name"),
                    "status": row.get("status"),
                    "best_delta": row.get("best_delta"),
                    "best_delta_hits": row.get("best_delta_hits"),
                    "support_ratio": row.get("support_ratio"),
                    "aligned_equal_ratio": row.get(
                        "aligned_equal_ratio"
                    ),
                }
            )

    applied_map: dict[str, dict[int, int]] = {}
    segment_results: list[dict[str, Any]] = []

    for seg_index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            continue

        name = str(segment.get("name", ""))
        if not SEGMENT_RE.fullmatch(name):
            continue

        direct = {
            index: row
            for (segment_name, index), row in accepted.items()
            if segment_name == name
        }

        proposal = build_segment_proposal(
            segment,
            direct,
            segment_end(segments, seg_index, args.rom_size),
        )
        segment_results.append(proposal)

        if proposal["status"] != "applied":
            continue

        applied_map[name] = {
            int(item["index"]): int(item["new_start"])
            for item in proposal["proposals"]
            if item["new_start"] != item["old_start"]
        }

    output_text = patch_yaml_text(original_text, applied_map)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output_text, encoding="utf-8")

    applied_segments = [
        item for item in segment_results
        if item["status"] == "applied"
    ]
    skipped_segments = [
        item for item in segment_results
        if item["status"] != "applied"
    ]

    summary = {
        "input_yaml": str(args.yaml),
        "relocations": str(args.relocations),
        "output_yaml": str(args.output),
        "min_good_ratio": args.min_good_ratio,
        "accepted_direct_anchors": len(accepted),
        "rejected_suspicious_anchors": len(rejected_suspicious),
        "applied_segments": len(applied_segments),
        "skipped_segments": len(skipped_segments),
        "changed_subsegment_starts": sum(
            item.get("changes", 0)
            for item in applied_segments
        ),
        "direct_changes": sum(
            item.get("direct_changes", 0)
            for item in applied_segments
        ),
        "inferred_changes": sum(
            item.get("inferred_changes", 0)
            for item in applied_segments
        ),
        "same_delta_inferred_changes": sum(
            item.get("same_delta_inferred_changes", 0)
            for item in applied_segments
        ),
        "tail_inferred_changes": sum(
            item.get("tail_inferred_changes", 0)
            for item in applied_segments
        ),
    }

    report_payload = {
        "summary": summary,
        "skipped_segments": [
            {
                "segment": item["segment"],
                "reason": item.get("reason"),
            }
            for item in skipped_segments
        ],
        "rejected_suspicious_anchors": rejected_suspicious,
        "segments": segment_results,
    }

    args.report.write_text(
        json.dumps(report_payload, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))
    if skipped_segments:
        print()
        print("Skipped segments:")
        for item in skipped_segments:
            print(
                f"  {item['segment']}: "
                f"{item.get('reason', 'unknown')}"
            )

    print()
    print(f"Candidate: {args.output}")
    print(f"Report   : {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
