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


def parse_int(value: Any) -> int:
    return value if isinstance(value, int) else int(str(value), 0)


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
    asm_files = sorted(args.asm_root.rglob("*.s"))
    if not asm_files:
        raise SystemExit("ERROR: no assembly files found. Run extraction with -DisassembleAll.")

    funcs: list[Function] = []
    files_without_funcs: list[str] = []

    for asm_path in asm_files:
        parsed = parse_asm_file(asm_path, section_for_asm(asm_path))
        if parsed:
            funcs.extend(parsed)
        else:
            files_without_funcs.append(asm_path.as_posix())

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

    name_counts = Counter(func.original_name for func in valid)
    used_names: set[str] = set()

    for func in sorted(valid, key=lambda x: (x.section, x.vram, x.original_name)):
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
        "rejected_functions": rejected,
        "asm_files_without_function_labels": files_without_funcs,
        "per_section": {name: len(by_section[name]) for name in sections},
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print("NP3F N64Recomp symbol generation:")
    print(f"  asm files scanned        : {len(asm_files)}")
    print(f"  functions emitted        : {len(valid)}")
    print(f"  sections with functions : {report['sections_with_functions']} / {len(sections)}")
    print(f"  rejected functions       : {len(rejected)}")
    print(f"  symbol map               : {args.output}")
    print(f"  report                   : {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
