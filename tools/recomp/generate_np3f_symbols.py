from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise SystemExit("ERROR: PyYAML is required. Install the Splat environment first.") from exc

FRAGMENT_PATH_RE = re.compile(r"(?:^|[\\/])fragments[\\/](\d+)(?:[\\/]|$)")
GLABEL_RE = re.compile(r"^\s*(?:glabel|\.glabel)\s+([A-Za-z_.$][A-Za-z0-9_.$]*)\s*$")
SECTION_RE = re.compile(r"^\s*\.section\s+([^\s,]+)")
INSTR_RE = re.compile(
    r"/\*\s*([0-9A-Fa-f]{6,8})\s+([0-9A-Fa-f]{8})\s+([0-9A-Fa-f]{8})\s*\*/"
)


@dataclass
class CodeSection:
    name: str
    rom: int
    vram: int
    size: int


@dataclass
class Function:
    original_name: str
    name: str
    vram: int
    size: int
    asm_path: str
    section: str


@dataclass
class UnlabeledCodeChunk:
    path: str
    section: str
    start_vram: int
    end_vram: int


def parse_int(value: Any) -> int:
    return value if isinstance(value, int) else int(str(value), 0)


RSP_CPU_EXCLUDED_SUBSEGMENTS = {"pre_main"}

# Verified NP3F names for tiny hand-written assembly helpers whose upstream
# NP3E names were intentionally removed from the recompilation Splat pass.
# The NP3F exception_set subsegment is ROM 0xC280..0xC2A0:
#   0x8000B680 -> set_watch_lohi
#   0x8000B690 -> trigger_fault
KNOWN_NP3F_FUNCTION_NAMES: dict[tuple[str, int], str] = {
    ("text", 0x8000B680): "set_watch_lohi",
    ("text", 0x8000B690): "trigger_fault",
}


def collect_cpu_exclusions(
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    exclusions: list[dict[str, Any]] = []
    segments = config.get("segments")
    if not isinstance(segments, list):
        return exclusions

    for segment in segments:
        if not isinstance(segment, dict):
            continue

        seg_name = str(segment.get("name", ""))
        if seg_name != "text":
            continue

        if "start" not in segment or "vram" not in segment:
            continue

        seg_rom = parse_int(segment["start"])
        seg_vram = parse_int(segment["vram"])
        subsegments = segment.get("subsegments")
        if not isinstance(subsegments, list):
            continue

        linear: list[tuple[int, list[Any]]] = []
        for subsegment in subsegments:
            if (
                isinstance(subsegment, list)
                and len(subsegment) >= 2
                and isinstance(subsegment[0], (int, str))
            ):
                try:
                    linear.append((parse_int(subsegment[0]), subsegment))
                except (TypeError, ValueError):
                    pass

        linear.sort(key=lambda item: item[0])

        for index, (start_rom, subsegment) in enumerate(linear):
            sub_name = str(subsegment[2]) if len(subsegment) >= 3 else ""
            if sub_name not in RSP_CPU_EXCLUDED_SUBSEGMENTS:
                continue

            if index + 1 >= len(linear):
                continue

            end_rom = linear[index + 1][0]
            start_vram = seg_vram + (start_rom - seg_rom)
            end_vram = seg_vram + (end_rom - seg_rom)

            exclusions.append(
                {
                    "name": sub_name,
                    "reason": "rsp_microcode_not_cpu_code",
                    "rom_start": start_rom,
                    "rom_end": end_rom,
                    "vram_start": start_vram,
                    "vram_end": end_vram,
                }
            )

    return exclusions


def function_hits_exclusion(
    func: Function,
    exclusions: list[dict[str, Any]],
) -> dict[str, Any] | None:
    func_end = func.vram + func.size
    for exclusion in exclusions:
        if (
            func.vram < int(exclusion["vram_end"])
            and func_end > int(exclusion["vram_start"])
        ):
            return exclusion
    return None


def collect_sections(config: dict[str, Any]) -> dict[str, CodeSection]:
    segments = config.get("segments")
    if not isinstance(segments, list):
        raise SystemExit("ERROR: canonical YAML has no segments list.")

    executable: list[tuple[int, str, int]] = []
    for item in segments:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", ""))
        if name == "text" or name.startswith("fragment"):
            if "start" in item and "vram" in item:
                executable.append(
                    (parse_int(item["start"]), name, parse_int(item["vram"]))
                )

    executable.sort()
    sections: dict[str, CodeSection] = {}

    for index, (rom, name, vram) in enumerate(executable):
        end = executable[index + 1][0] if index + 1 < len(executable) else 0x438280
        if end <= rom:
            raise SystemExit(
                f"ERROR: invalid section extent for {name}: 0x{rom:X}..0x{end:X}"
            )
        sections[name] = CodeSection(name, rom, vram, end - rom)

    expected = {"text", *(f"fragment{i}" for i in range(1, 89))}
    missing = sorted(expected - set(sections))
    if missing:
        raise SystemExit("ERROR: missing executable sections: " + ", ".join(missing))

    return sections


def section_for_asm(path: Path) -> str:
    match = FRAGMENT_PATH_RE.search(path.as_posix())
    return f"fragment{int(match.group(1))}" if match else "text"


def sanitize_c_identifier(name: str) -> str:
    name = name.replace(".", "_").replace("$", "_")
    name = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not name:
        name = "func"
    if name[0].isdigit():
        name = "_" + name
    return name


def parse_asm_file(path: Path, section_name: str) -> list[Function]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    found: list[Function] = []

    current_name: str | None = None
    current_start: int | None = None
    last_vram: int | None = None
    in_text = True
    saw_section_directive = False

    def flush() -> None:
        nonlocal current_name, current_start, last_vram
        if current_name is not None and current_start is not None and last_vram is not None:
            size = last_vram + 4 - current_start
            if size > 0 and size % 4 == 0:
                found.append(
                    Function(
                        original_name=current_name,
                        name=current_name,
                        vram=current_start,
                        size=size,
                        asm_path=path.as_posix(),
                        section=section_name,
                    )
                )
        current_name = None
        current_start = None
        last_vram = None

    for line in lines:
        section_match = SECTION_RE.match(line)
        if section_match:
            saw_section_directive = True
            new_text = ".text" in section_match.group(1)
            if in_text and not new_text:
                flush()
            in_text = new_text
            continue

        label_match = GLABEL_RE.match(line)
        if label_match and (in_text or not saw_section_directive):
            flush()
            current_name = label_match.group(1)
            continue

        if current_name is not None and (in_text or not saw_section_directive):
            instr_match = INSTR_RE.search(line)
            if instr_match:
                vram = int(instr_match.group(2), 16)
                if current_start is None:
                    current_start = vram
                if last_vram is None or vram >= last_vram:
                    last_vram = vram

    flush()
    return found


def parse_unlabeled_code_chunk(
    path: Path,
    section_name: str,
) -> UnlabeledCodeChunk | None:
    # Splat can emit extra nonmatchings/*.s files for internal labels used by
    # jump tables. Those files may contain real instructions but no glabel, so
    # parse_asm_file() intentionally returns no Function for them.
    #
    # Only consider nonmatchings code files here. This prevents data/header
    # assembly from being mistaken for executable continuations.
    if "nonmatchings" not in path.parts:
        return None

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    if any(GLABEL_RE.match(line) for line in lines):
        return None

    vrams: list[int] = []
    in_text = True
    saw_section_directive = False

    for line in lines:
        section_match = SECTION_RE.match(line)
        if section_match:
            saw_section_directive = True
            in_text = ".text" in section_match.group(1)
            continue

        if in_text or not saw_section_directive:
            instr_match = INSTR_RE.search(line)
            if instr_match:
                vrams.append(int(instr_match.group(2), 16))

    if not vrams:
        return None

    vrams.sort()
    return UnlabeledCodeChunk(
        path=path.as_posix(),
        section=section_name,
        start_vram=vrams[0],
        end_vram=vrams[-1] + 4,
    )


def toml_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml", type=Path, default=Path("yamls/fr/splat.yaml"))
    parser.add_argument("--asm-root", type=Path, default=Path("build/np3f/asm"))
    parser.add_argument("--output", type=Path, default=Path("build/np3f/recomp/np3f.syms.toml"))
    parser.add_argument("--report", type=Path, default=Path("build/np3f/analysis/recomp_symbols_report.json"))
    args = parser.parse_args()

    if not args.yaml.is_file():
        raise SystemExit(f"ERROR: canonical YAML not found: {args.yaml}")
    if not args.asm_root.is_dir():
        raise SystemExit(
            f"ERROR: Splat asm directory not found: {args.asm_root}\n"
            "Run windows\\run_np3f_extract.ps1 -DisassembleAll first."
        )

    config = yaml.safe_load(args.yaml.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise SystemExit("ERROR: canonical YAML root is not a mapping.")

    sections = collect_sections(config)
    cpu_exclusions = collect_cpu_exclusions(config)

    asm_files = sorted(args.asm_root.rglob("*.s"))
    if not asm_files:
        raise SystemExit("ERROR: no assembly files found. Run extraction with -DisassembleAll.")

    funcs: list[Function] = []
    files_without_funcs: list[str] = []
    unlabeled_code_chunks: list[UnlabeledCodeChunk] = []

    for asm_path in asm_files:
        section_name = section_for_asm(asm_path)
        parsed = parse_asm_file(asm_path, section_name)
        if parsed:
            funcs.extend(parsed)
        else:
            files_without_funcs.append(asm_path.as_posix())
            chunk = parse_unlabeled_code_chunk(asm_path, section_name)
            if chunk is not None:
                unlabeled_code_chunks.append(chunk)

    unique_by_key: dict[tuple[str, int, str], Function] = {}
    for func in funcs:
        key = (func.section, func.vram, func.original_name)
        old = unique_by_key.get(key)
        if old is None or func.size > old.size:
            unique_by_key[key] = func
    funcs = list(unique_by_key.values())

    valid: list[Function] = []
    rejected: list[dict[str, Any]] = []

    for func in funcs:
        exclusion = function_hits_exclusion(func, cpu_exclusions)
        if exclusion is not None:
            rejected.append(
                {
                    "path": func.asm_path,
                    "name": func.original_name,
                    "section": func.section,
                    "vram": func.vram,
                    "size": func.size,
                    "reason": "excluded_rsp_microcode",
                    "excluded_subsegment": exclusion["name"],
                }
            )
            continue

        section = sections.get(func.section)
        if section is None:
            rejected.append({"path": func.asm_path, "name": func.original_name, "reason": "unknown_section"})
            continue

        offset = func.vram - section.vram
        if offset < 0 or offset + func.size > section.size or offset % 4 != 0:
            rejected.append(
                {
                    "path": func.asm_path,
                    "name": func.original_name,
                    "section": func.section,
                    "vram": func.vram,
                    "size": func.size,
                    "section_vram": section.vram,
                    "section_size": section.size,
                    "reason": "outside_section",
                }
            )
            continue
        valid.append(func)

    if not valid:
        raise SystemExit("ERROR: no valid functions recovered from Splat assembly.")

    # Merge unlabeled nonmatchings code chunks into the preceding function when
    # they are exactly contiguous. Splat emits these for internal jump-table
    # labels; treating them as separate functions would truncate the parent
    # function and cause N64Recomp jump-table analysis to fail.
    merged_unlabeled_code_chunks: list[dict[str, Any]] = []

    funcs_by_section_start: dict[str, list[Function]] = {}
    for func in valid:
        funcs_by_section_start.setdefault(func.section, []).append(func)

    for entries in funcs_by_section_start.values():
        entries.sort(key=lambda x: (x.vram, x.original_name))

    for chunk in sorted(
        unlabeled_code_chunks,
        key=lambda x: (x.section, x.start_vram, x.end_vram, x.path),
    ):
        entries = funcs_by_section_start.get(chunk.section, [])
        preceding: Function | None = None

        for func in entries:
            if func.vram > chunk.start_vram:
                break
            preceding = func

        if preceding is None:
            continue

        current_end = preceding.vram + preceding.size
        if chunk.start_vram != current_end:
            continue

        preceding.size = chunk.end_vram - preceding.vram
        merged_unlabeled_code_chunks.append(
            {
                "path": chunk.path,
                "section": chunk.section,
                "start_vram": chunk.start_vram,
                "end_vram": chunk.end_vram,
                "merged_into": preceding.original_name,
                "merged_function_vram": preceding.vram,
                "merged_function_new_size": preceding.size,
            }
        )

    merged_paths = {
        item["path"] for item in merged_unlabeled_code_chunks
    }
    files_without_funcs = [
        path for path in files_without_funcs if path not in merged_paths
    ]

    name_counts = Counter(func.original_name for func in valid)
    used_names: set[str] = set()

    verified_name_overrides: list[dict[str, Any]] = []

    for func in sorted(valid, key=lambda x: (x.section, x.vram, x.original_name)):
        verified_name = KNOWN_NP3F_FUNCTION_NAMES.get((func.section, func.vram))
        if verified_name is not None:
            candidate = sanitize_c_identifier(verified_name)
            verified_name_overrides.append(
                {
                    "section": func.section,
                    "vram": func.vram,
                    "detected_name": func.original_name,
                    "verified_name": verified_name,
                }
            )
        else:
            candidate = sanitize_c_identifier(
                func.original_name
                if name_counts[func.original_name] == 1
                else f"{func.section}__{func.original_name}"
            )
        base = candidate
        serial = 2
        while candidate in used_names:
            candidate = f"{base}__{serial}"
            serial += 1
        func.name = candidate
        used_names.add(candidate)

    by_section: dict[str, list[Function]] = {name: [] for name in sections}
    for func in valid:
        by_section[func.section].append(func)

    clipped = 0
    for entries in by_section.values():
        entries.sort(key=lambda x: (x.vram, x.name))
        for index, func in enumerate(entries[:-1]):
            next_func = entries[index + 1]
            if next_func.vram > func.vram and next_func.vram < func.vram + func.size:
                func.size = next_func.vram - func.vram
                clipped += 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", encoding="utf-8", newline="\n") as out:
        out.write("# Generated from canonical NP3F Splat output.\n\n")
        order = ["text"] + [f"fragment{i}" for i in range(1, 89)]
        for section_name in order:
            section = sections[section_name]
            entries = by_section[section_name]
            if not entries:
                continue

            out.write("[[section]]\n")
            out.write(f'name = "{toml_quote(section.name)}"\n')
            out.write(f"rom = 0x{section.rom:08X}\n")
            out.write(f"vram = 0x{section.vram:08X}\n")
            out.write(f"size = 0x{section.size:X}\n")
            out.write("functions = [\n")
            for func in entries:
                out.write(
                    "    { "
                    f'name = "{toml_quote(func.name)}", '
                    f"vram = 0x{func.vram:08X}, "
                    f"size = 0x{func.size:X} "
                    "},\n"
                )
            out.write("]\n\n")

    report = {
        "canonical_yaml": str(args.yaml),
        "asm_root": str(args.asm_root),
        "output": str(args.output),
        "asm_files_scanned": len(asm_files),
        "functions_found": len(funcs),
        "functions_emitted": len(valid),
        "sections_with_functions": sum(bool(entries) for entries in by_section.values()),
        "expected_sections": len(sections),
        "duplicate_function_names": sorted(name for name, count in name_counts.items() if count > 1),
        "clipped_overlapping_functions": clipped,
        "verified_name_overrides": verified_name_overrides,
        "merged_unlabeled_code_chunks": merged_unlabeled_code_chunks,
        "rejected_functions": rejected,
        "cpu_exclusions": cpu_exclusions,
        "rsp_microcode_functions_excluded": sum(
            item.get("reason") == "excluded_rsp_microcode"
            for item in rejected
        ),
        "asm_files_without_function_labels": files_without_funcs,
        "per_section": {name: len(by_section[name]) for name in sections},
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("NP3F N64Recomp symbol generation:")
    print(f"  asm files scanned        : {len(asm_files)}")
    print(f"  functions emitted        : {len(valid)}")
    print(f"  sections with functions : {report['sections_with_functions']} / {len(sections)}")
    print(f"  rejected functions       : {len(rejected)}")
    print(f"  verified name overrides  : {len(verified_name_overrides)}")
    print(f"  merged code continuations: {len(merged_unlabeled_code_chunks)}")
    for continuation in merged_unlabeled_code_chunks:
        print(
            "    - "
            f"0x{continuation['start_vram']:08X}-"
            f"0x{continuation['end_vram']:08X} -> "
            f"{continuation['merged_into']}"
        )
    for override in verified_name_overrides:
        print(
            "    - "
            f"0x{override['vram']:08X}: "
            f"{override['detected_name']} -> {override['verified_name']}"
        )
    print(
        "  RSP functions excluded   : "
        f"{report['rsp_microcode_functions_excluded']}"
    )
    for exclusion in cpu_exclusions:
        print(
            "    - "
            f"{exclusion['name']}: "
            f"ROM 0x{exclusion['rom_start']:X}-0x{exclusion['rom_end']:X}, "
            f"VRAM 0x{exclusion['vram_start']:08X}-0x{exclusion['vram_end']:08X}"
        )
    print(f"  symbol map               : {args.output}")
    print(f"  report                   : {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
