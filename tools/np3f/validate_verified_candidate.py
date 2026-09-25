from __future__ import annotations

import argparse
import json
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
    from .build_relocated_candidate import eligible_anchor, parse_int
except ImportError:
    from build_relocated_candidate import eligible_anchor, parse_int


VALIDATOR_VERSION = 2


def collect_candidate(config: dict[str, Any]) -> tuple[
    dict[str, int],
    dict[tuple[str, int], dict[str, Any]],
]:
    segments = config.get("segments")
    if not isinstance(segments, list):
        raise SystemExit("ERROR: candidate YAML has no segments list.")

    headers: dict[str, int] = {}
    subsegments: dict[tuple[str, int], dict[str, Any]] = {}

    for segment in segments:
        if not isinstance(segment, dict):
            continue

        name = str(segment.get("name", ""))
        if not name.startswith("fragment"):
            continue

        if "start" not in segment:
            continue
        headers[name] = parse_int(segment["start"])

        items = segment.get("subsegments")
        if not isinstance(items, list):
            continue

        previous: int | None = None
        for index, item in enumerate(items):
            if not isinstance(item, list) or len(item) < 2:
                continue

            start = parse_int(item[0])
            seg_type = str(item[1])
            sub_name = (
                str(item[2])
                if len(item) >= 3 and item[2] is not None
                else None
            )

            if previous is not None and start <= previous:
                raise SystemExit(
                    f"ERROR: non-monotonic candidate subsegments in {name}: "
                    f"index {index - 1}=0x{previous:X}, index {index}=0x{start:X}"
                )
            previous = start

            subsegments[(name, index)] = {
                "segment": name,
                "subsegment_index": index,
                "start": start,
                "type": seg_type,
                "name": sub_name,
            }

    return headers, subsegments


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the verified NP3F candidate against all accepted direct "
            "relocation anchors plus the ROM-verified header/internal overrides."
        )
    )
    parser.add_argument(
        "--candidate",
        type=Path,
        default=Path("build/np3f/analysis/splat-segment-verified.yaml"),
    )
    parser.add_argument(
        "--relocations",
        type=Path,
        default=Path("build/np3f/analysis/subsegment_relocations.json"),
    )
    parser.add_argument(
        "--overrides",
        type=Path,
        default=Path("build/np3f/analysis/verified_fragment_overrides.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "build/np3f/analysis/verified_candidate_validation.json"
        ),
    )
    parser.add_argument("--min-good-ratio", type=float, default=0.75)
    args = parser.parse_args()

    for path, label in (
        (args.candidate, "candidate"),
        (args.relocations, "relocations"),
        (args.overrides, "verified overrides"),
    ):
        if not path.is_file():
            raise SystemExit(f"ERROR: {label} file not found: {path}")

    config = yaml.safe_load(args.candidate.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise SystemExit("ERROR: candidate YAML root must be a mapping.")

    candidate_headers, candidate_subsegments = collect_candidate(config)

    relocation_payload = json.loads(
        args.relocations.read_text(encoding="utf-8")
    )
    rows = relocation_payload.get("subsegments")
    if not isinstance(rows, list):
        raise SystemExit(
            "ERROR: relocation report does not contain a subsegments list."
        )

    override_payload = json.loads(
        args.overrides.read_text(encoding="utf-8")
    )
    verified_headers = override_payload.get("headers")
    if not isinstance(verified_headers, dict):
        raise SystemExit(
            "ERROR: verified override report does not contain headers."
        )

    internal_raw = override_payload.get("verified_internal_starts", {})
    verified_internal_keys: set[tuple[str, int]] = set()
    if isinstance(internal_raw, dict):
        for verified_segment, entries in internal_raw.items():
            if not isinstance(entries, dict):
                continue
            for verified_index in entries:
                verified_internal_keys.add(
                    (str(verified_segment), int(verified_index))
                )

    direct_checks: list[dict[str, Any]] = []
    unresolved_code: list[dict[str, Any]] = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        segment = str(row.get("segment", ""))
        index = int(row.get("subsegment_index", -1))
        key = (segment, index)
        actual = candidate_subsegments.get(key)

        if actual is None:
            continue

        is_eligible = eligible_anchor(row, args.min_good_ratio)

        if is_eligible:
            old_start = int(row["start"])
            delta = int(row["best_delta"])
            expected = old_start + delta
            actual_start = int(actual["start"])

            direct_checks.append(
                {
                    "segment": segment,
                    "subsegment_index": index,
                    "name": actual.get("name"),
                    "type": actual.get("type"),
                    "reference_start": old_start,
                    "best_delta": delta,
                    "expected_fr_start": expected,
                    "candidate_fr_start": actual_start,
                    "match": actual_start == expected,
                    "status": row.get("status"),
                    "support_ratio": row.get("support_ratio"),
                    "aligned_equal_ratio": row.get(
                        "aligned_equal_ratio"
                    ),
                }
            )
        elif str(actual.get("type")) in {"c", "asm", "hasm", "lib"} and key not in verified_internal_keys:
            unresolved_code.append(
                {
                    "segment": segment,
                    "subsegment_index": index,
                    "name": actual.get("name"),
                    "type": actual.get("type"),
                    "candidate_fr_start": actual.get("start"),
                    "status": row.get("status"),
                    "best_delta": row.get("best_delta"),
                    "best_delta_hits": row.get("best_delta_hits"),
                    "support_ratio": row.get("support_ratio"),
                    "aligned_equal_ratio": row.get(
                        "aligned_equal_ratio"
                    ),
                }
            )

    header_checks: list[dict[str, Any]] = []
    for segment, expected_raw in verified_headers.items():
        expected = int(expected_raw)
        actual = candidate_headers.get(str(segment))
        header_checks.append(
            {
                "segment": str(segment),
                "expected": expected,
                "actual": actual,
                "match": actual == expected,
            }
        )

    internal_checks: list[dict[str, Any]] = []
    if isinstance(internal_raw, dict):
        for segment, entries in internal_raw.items():
            if not isinstance(entries, dict):
                continue
            for index_raw, expected_raw in entries.items():
                index = int(index_raw)
                expected = int(expected_raw)
                actual_entry = candidate_subsegments.get(
                    (str(segment), index)
                )
                actual = (
                    int(actual_entry["start"])
                    if actual_entry is not None
                    else None
                )
                internal_checks.append(
                    {
                        "segment": str(segment),
                        "subsegment_index": index,
                        "expected": expected,
                        "actual": actual,
                        "match": actual == expected,
                    }
                )

    direct_mismatches = [
        item for item in direct_checks if not item["match"]
    ]
    header_mismatches = [
        item for item in header_checks if not item["match"]
    ]
    internal_mismatches = [
        item for item in internal_checks if not item["match"]
    ]

    summary = {
        "validator_version": VALIDATOR_VERSION,
        "candidate": str(args.candidate),
        "relocations": str(args.relocations),
        "verified_overrides": str(args.overrides),
        "candidate_fragment_headers": len(candidate_headers),
        "verified_header_checks": len(header_checks),
        "verified_header_matches": len(header_checks)
        - len(header_mismatches),
        "verified_internal_checks": len(internal_checks),
        "verified_internal_matches": len(internal_checks)
        - len(internal_mismatches),
        "eligible_direct_anchor_checks": len(direct_checks),
        "eligible_direct_anchor_matches": len(direct_checks)
        - len(direct_mismatches),
        "direct_anchor_mismatches": len(direct_mismatches),
        "unresolved_code_boundaries": len(unresolved_code),
        "validation_ok": not (
            direct_mismatches
            or header_mismatches
            or internal_mismatches
            or unresolved_code
            or len(candidate_headers) != 88
        ),
    }

    payload = {
        "summary": summary,
        "direct_anchor_mismatches": direct_mismatches,
        "header_mismatches": header_mismatches,
        "internal_override_mismatches": internal_mismatches,
        "unresolved_code_boundaries": unresolved_code,
        "direct_anchor_checks": direct_checks,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))
    print()
    if direct_mismatches:
        print("Direct-anchor mismatches:")
        for item in direct_mismatches:
            print(
                f"  {item['segment']}[{item['subsegment_index']}]: "
                f"candidate=0x{item['candidate_fr_start']:X}, "
                f"expected=0x{item['expected_fr_start']:X}"
            )
        print()

    if unresolved_code:
        print("Code boundaries still lacking an accepted direct anchor:")
        for item in unresolved_code:
            delta = item.get("best_delta")
            delta_text = (
                f"{int(delta):+#x}"
                if delta is not None
                else "none"
            )
            print(
                f"  {item['segment']}[{item['subsegment_index']}]: "
                f"{item.get('status')} / best_delta={delta_text}"
            )
        print()

    print(f"Report: {args.output}")
    return 0 if summary["validation_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
