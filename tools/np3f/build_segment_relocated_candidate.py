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

try:
    from .build_relocated_candidate import (
        SEGMENT_RE,
        SUBSEGMENT_LINE_RE,
        eligible_anchor,
        nearest_direct,
        parse_int,
    )
except ImportError:
    from build_relocated_candidate import (
        SEGMENT_RE,
        SUBSEGMENT_LINE_RE,
        eligible_anchor,
        nearest_direct,
        parse_int,
    )


CODE_TYPES = {"c", "asm", "hasm", "lib", "bin"}
SEGMENT_START_RE = re.compile(
    r"^(?P<prefix>\s+start:\s*)(?P<start>0x[0-9A-Fa-f]+|\d+)(?P<suffix>.*)$"
)


def collect_accepted(
    rows: list[Any],
    min_good_ratio: float,
) -> tuple[
    dict[tuple[str, int], dict[str, Any]],
    list[dict[str, Any]],
]:
    accepted: dict[tuple[str, int], dict[str, Any]] = {}
    rejected: list[dict[str, Any]] = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        segment_name = str(row.get("segment", ""))
        sub_index = int(row.get("subsegment_index", -1))

        if eligible_anchor(row, min_good_ratio):
            accepted[(segment_name, sub_index)] = row
        elif (
            row.get("best_delta") is not None
            and str(row.get("status", "")) in {"strong", "good"}
        ):
            rejected.append(
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

    return accepted, rejected


def infer_fragment_start_delta(
    segment: dict[str, Any],
    direct: dict[int, dict[str, Any]],
) -> tuple[int, str]:
    subsegments = segment.get("subsegments")
    if not isinstance(subsegments, list) or len(subsegments) < 2:
        return 0, "no_subsegments"

    segment_start = parse_int(segment["start"])
    first = subsegments[1]
    if not isinstance(first, list) or len(first) < 2:
        return 0, "unsupported_first_subsegment"

    first_start = parse_int(first[0])
    first_type = str(first[1])
    first_anchor = direct.get(1)

    if first_anchor is None:
        return 0, "no_direct_index1_anchor"
    if first_start - segment_start != 0x20:
        return 0, "first_subsegment_not_plus_0x20"
    if first_type not in CODE_TYPES:
        return 0, "first_subsegment_not_executable"

    return int(first_anchor["best_delta"]), "direct_index1_plus_0x20"


def find_next_start(
    segments: list[Any],
    index: int,
    fragment_deltas: dict[str, int],
    rom_size: int,
) -> tuple[int, str]:
    current = segments[index]
    current_name = (
        str(current.get("name", ""))
        if isinstance(current, dict)
        else ""
    )
    current_delta = fragment_deltas.get(current_name, 0)

    for following in segments[index + 1 :]:
        if isinstance(following, dict) and "start" in following:
            following_start = parse_int(following["start"])
            following_name = str(following.get("name", ""))
            if SEGMENT_RE.fullmatch(following_name):
                following_start += fragment_deltas.get(
                    following_name, 0
                )
            return following_start, following_name or "dict"

        if isinstance(following, list) and following:
            following_start = parse_int(following[0])
            if current_name == "fragment88" and current_delta:
                following_start += current_delta
                return following_start, "shifted_post_fragment_bin"
            return following_start, "list"

    return rom_size, "rom_end"


def build_segment_proposal(
    segment: dict[str, Any],
    direct: dict[int, dict[str, Any]],
    seg_end: int,
    segment_delta: int,
    segment_delta_source: str,
) -> dict[str, Any]:
    name = str(segment.get("name", ""))
    subsegments = segment.get("subsegments")

    if not isinstance(subsegments, list) or not subsegments:
        return {
            "segment": name,
            "status": "skipped",
            "reason": "no_subsegments",
        }

    if not direct:
        return {
            "segment": name,
            "status": "skipped",
            "reason": "no_reliable_anchor",
            "segment_start_delta": segment_delta,
            "segment_start_source": segment_delta_source,
        }

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
            delta = segment_delta
            new_start = old_start + segment_delta
            source = (
                "inferred_segment_start"
                if segment_delta
                else "fixed_segment_start"
            )
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
                and int(left["best_delta"])
                == int(right["best_delta"])
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

    old_segment_start = parse_int(
        segment.get("start", proposals[0]["old_start"])
    )
    new_segment_start = old_segment_start + segment_delta

    if proposals[0]["new_start"] != new_segment_start:
        return {
            "segment": name,
            "status": "skipped",
            "reason": "segment_header_mismatch",
            "segment_start_delta": segment_delta,
            "segment_start_source": segment_delta_source,
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
                "segment_start_delta": segment_delta,
                "segment_start_source": segment_delta_source,
                "proposals": proposals,
            }

    if proposals[-1]["new_start"] >= seg_end:
        return {
            "segment": name,
            "status": "skipped",
            "reason": "last_subsegment_crosses_segment_end",
            "segment_start_delta": segment_delta,
            "segment_start_source": segment_delta_source,
            "proposals": proposals,
        }

    changes = [
        item
        for item in proposals
        if item["new_start"] != item["old_start"]
    ]

    return {
        "segment": name,
        "status": "applied",
        "reason": None,
        "old_segment_start": old_segment_start,
        "new_segment_start": new_segment_start,
        "segment_start_delta": segment_delta,
        "segment_start_source": segment_delta_source,
        "segment_end": seg_end,
        "changes": len(changes),
        "direct_changes": sum(
            item["source"] == "direct_anchor"
            for item in changes
        ),
        "inferred_changes": sum(
            str(item["source"]).startswith("inferred_")
            for item in changes
        ),
        "segment_start_changes": sum(
            item["source"] == "inferred_segment_start"
            for item in changes
        ),
        "same_delta_inferred_changes": sum(
            item["source"] == "inferred_same_delta"
            for item in changes
        ),
        "tail_inferred_changes": sum(
            item["source"] == "inferred_tail_delta"
            for item in changes
        ),
        "proposals": proposals,
    }


def patch_yaml_text(
    original: str,
    applied: dict[str, dict[int, int]],
    segment_starts: dict[str, int],
    post_fragment_bin: tuple[int, int] | None,
) -> str:
    output: list[str] = []
    current_segment: str | None = None
    in_subsegments = False
    sub_index = 0
    segment_start_pending = False

    old_tail = None
    new_tail = None
    if post_fragment_bin is not None:
        old_tail, new_tail = post_fragment_bin

    for line in original.splitlines():
        segment_match = re.match(r"^  - name:\s*(.+?)\s*$", line)
        if segment_match:
            current_segment = (
                segment_match.group(1).strip().strip("\"'")
            )
            in_subsegments = False
            sub_index = 0
            segment_start_pending = True
            output.append(line)
            continue

        if segment_start_pending and current_segment is not None:
            start_match = SEGMENT_START_RE.match(line)
            if start_match:
                replacement = segment_starts.get(current_segment)
                if replacement is not None:
                    line = (
                        start_match.group("prefix")
                        + f"0x{replacement:X}"
                        + start_match.group("suffix")
                    )
                segment_start_pending = False
                output.append(line)
                continue

        if (
            current_segment is not None
            and re.match(r"^\s+subsegments:\s*$", line)
        ):
            in_subsegments = True
            sub_index = 0
            output.append(line)
            continue

        if in_subsegments and re.match(r"^  - ", line):
            in_subsegments = False

        if in_subsegments:
            match = SUBSEGMENT_LINE_RE.match(line)
            if match:
                replacement = applied.get(
                    current_segment, {}
                ).get(sub_index)
                if replacement is not None:
                    line = (
                        match.group("prefix")
                        + f"0x{replacement:X}"
                        + match.group("suffix")
                    )
                sub_index += 1
                output.append(line)
                continue

        if old_tail is not None and new_tail is not None:
            tail_match = re.match(
                r"^(?P<prefix>\s*-\s*\[\s*)"
                r"(?P<start>0x[0-9A-Fa-f]+|\d+)"
                r"(?P<suffix>\s*,\s*bin[^\]]*\].*)$",
                line,
            )
            if (
                tail_match
                and parse_int(tail_match.group("start"))
                == old_tail
            ):
                line = (
                    tail_match.group("prefix")
                    + f"0x{new_tail:X}"
                    + tail_match.group("suffix")
                )
                old_tail = None

        output.append(line)

    banner = [
        "# GENERATED SEGMENT-AWARE CANDIDATE.",
        "# Experimental: fragment starts may move when the first",
        "# reliable executable subsegment is exactly +0x20 from",
        "# the US fragment header and relocates by the same delta.",
        "# Source: yamls/fr/splat.seed.yaml",
        "",
    ]
    return "\n".join(banner + output) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build an experimental NP3F Splat candidate that applies "
            "reliable subsegment relocations and also relocates a fragment "
            "header when subsegment index 1 is executable, exactly +0x20 "
            "from the fragment start, and has a reliable direct anchor."
        )
    )
    parser.add_argument(
        "--yaml",
        type=Path,
        default=Path("yamls/fr/splat.seed.yaml"),
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
            "build/np3f/analysis/splat-segment-relocated.yaml"
        ),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "build/np3f/analysis/"
            "segment_relocation_application.json"
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
            "ERROR: relocation report does not contain a "
            "subsegments list."
        )

    segments = config.get("segments")
    if not isinstance(segments, list):
        raise SystemExit(
            "ERROR: YAML does not contain a segments list."
        )

    accepted, rejected_suspicious = collect_accepted(
        relocation_rows,
        args.min_good_ratio,
    )

    fragment_deltas: dict[str, int] = {}
    fragment_delta_sources: dict[str, str] = {}

    for segment in segments:
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
        delta, source = infer_fragment_start_delta(
            segment,
            direct,
        )
        fragment_deltas[name] = delta
        fragment_delta_sources[name] = source

    shifted_starts: list[tuple[str, int]] = []
    previous_name = None
    previous_start = None

    for segment in segments:
        if not isinstance(segment, dict):
            continue
        name = str(segment.get("name", ""))
        if not SEGMENT_RE.fullmatch(name):
            continue

        new_start = (
            parse_int(segment["start"])
            + fragment_deltas.get(name, 0)
        )
        shifted_starts.append((name, new_start))

        if previous_start is not None and new_start <= previous_start:
            raise SystemExit(
                "ERROR: shifted fragment starts are not monotonic: "
                f"{previous_name}=0x{previous_start:X}, "
                f"{name}=0x{new_start:X}"
            )

        previous_name = name
        previous_start = new_start

    applied_map: dict[str, dict[int, int]] = {}
    segment_start_map: dict[str, int] = {}
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
        seg_end, end_source = find_next_start(
            segments,
            seg_index,
            fragment_deltas,
            args.rom_size,
        )

        proposal = build_segment_proposal(
            segment,
            direct,
            seg_end,
            fragment_deltas.get(name, 0),
            fragment_delta_sources.get(name, "none"),
        )
        proposal["segment_end_source"] = end_source
        segment_results.append(proposal)

        if proposal["status"] != "applied":
            continue

        if proposal.get("segment_start_delta", 0):
            segment_start_map[name] = int(
                proposal["new_segment_start"]
            )

        applied_map[name] = {
            int(item["index"]): int(item["new_start"])
            for item in proposal["proposals"]
            if item["new_start"] != item["old_start"]
        }

    last_fragment_delta = fragment_deltas.get("fragment88", 0)
    post_fragment_bin: tuple[int, int] | None = None

    if last_fragment_delta:
        last_fragment_index = next(
            (
                index
                for index, segment in enumerate(segments)
                if isinstance(segment, dict)
                and str(segment.get("name", ""))
                == "fragment88"
            ),
            None,
        )
        if last_fragment_index is not None:
            for following in segments[last_fragment_index + 1 :]:
                if isinstance(following, list) and following:
                    old_tail = parse_int(following[0])
                    if (
                        len(following) >= 2
                        and str(following[1]) == "bin"
                    ):
                        post_fragment_bin = (
                            old_tail,
                            old_tail + last_fragment_delta,
                        )
                    break
                if isinstance(following, dict):
                    break

    output_text = patch_yaml_text(
        original_text,
        applied_map,
        segment_start_map,
        post_fragment_bin,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output_text, encoding="utf-8")

    applied_segments = [
        item
        for item in segment_results
        if item["status"] == "applied"
    ]
    skipped_segments = [
        item
        for item in segment_results
        if item["status"] != "applied"
    ]

    summary = {
        "input_yaml": str(args.yaml),
        "relocations": str(args.relocations),
        "output_yaml": str(args.output),
        "min_good_ratio": args.min_good_ratio,
        "accepted_direct_anchors": len(accepted),
        "rejected_suspicious_anchors": len(
            rejected_suspicious
        ),
        "shifted_fragment_starts": sum(
            delta != 0 for delta in fragment_deltas.values()
        ),
        "unshifted_fragment_starts": [
            name
            for name, delta in fragment_deltas.items()
            if delta == 0
        ],
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
        "segment_start_changes": sum(
            item.get("segment_start_changes", 0)
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
        "post_fragment_bin": (
            {
                "old_start": post_fragment_bin[0],
                "new_start": post_fragment_bin[1],
                "delta": post_fragment_bin[1]
                - post_fragment_bin[0],
            }
            if post_fragment_bin
            else None
        ),
    }

    report_payload = {
        "summary": summary,
        "fragment_start_deltas": [
            {
                "segment": name,
                "delta": fragment_deltas[name],
                "source": fragment_delta_sources[name],
            }
            for name in fragment_deltas
        ],
        "skipped_segments": [
            {
                "segment": item["segment"],
                "reason": item.get("reason"),
                "segment_start_delta": item.get(
                    "segment_start_delta", 0
                ),
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
