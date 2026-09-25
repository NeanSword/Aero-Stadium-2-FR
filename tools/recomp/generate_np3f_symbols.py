from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GENERATOR_VERSION = "2026-09-25.9"

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
UPSTREAM_FUNC_SYMBOL_RE = re.compile(
    r"^\s*([A-Za-z_.$][A-Za-z0-9_.$]*)\s*=\s*(0x[0-9A-Fa-f]+)\s*;.*\btype:func\b"
)

# Pinned pret/pokestadiumgs US libultra text range. NP3F keeps this block
# byte-identical but relocates the whole range by +0x120.
US_LIBULTRA_ROM_START = 0x746D0
US_LIBULTRA_ROM_END = 0x85DA0
US_TEXT_ROM_START = 0x1000
US_TEXT_VRAM_START = 0x80000400
ROM_DEFAULT_PATH = Path("baseroms/fr/baserom.z64")


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

# Some hand-written routines contain inline literal words after their actual
# return sequence. Splat/spimdisasm can decode those literals as instructions
# when generating a symbol-clean disassembly, which makes N64Recomp try to
# compile data. Keep the executable extent explicit for these verified NP3F
# routines while leaving the literal bytes in ROM for PC-relative data access.
KNOWN_NP3F_FUNCTION_SIZES: dict[tuple[str, int], int] = {
    # FR ROM 0x22060: executable code ends at VRAM 0x8002154C.
    # The following words C7D7E3E7 F1F3F5F7 are inline data, not CPU code.
    ("text", 0x80021460): 0xEC,
    # The next hand-written routine ends at 0x80021608, followed by another
    # 8-byte inline table (0CCD2CCD 53337FFF).
    ("text", 0x80021554): 0xB4,
}

# Executable helpers that begin after an inline-data gap and therefore may not
# receive a standalone glabel in Splat's symbol-clean disassembly.
KNOWN_NP3F_MANUAL_FUNCTIONS: dict[tuple[str, int], tuple[str, int]] = {
    # Continuation/helper after the 0x80021608..0x80021610 inline table.
    # It runs through the delay slot at 0x800217D0; the next glabel is 0x800217D4.
    ("text", 0x80021610): ("func_80021610", 0x1C4),
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


def collect_fr_libultra_range(
    config: dict[str, Any],
) -> tuple[int, int]:
    segments = config.get("segments")
    if not isinstance(segments, list):
        raise SystemExit("ERROR: canonical YAML has no segments list.")

    for segment in segments:
        if not isinstance(segment, dict) or str(segment.get("name", "")) != "text":
            continue

        subsegments = segment.get("subsegments")
        if not isinstance(subsegments, list):
            continue

        starts: list[tuple[int, list[Any]]] = []
        for subsegment in subsegments:
            if isinstance(subsegment, list) and len(subsegment) >= 2:
                try:
                    starts.append((parse_int(subsegment[0]), subsegment))
                except (TypeError, ValueError):
                    pass

        starts.sort(key=lambda item: item[0])

        first_lib_index: int | None = None
        for index, (_, subsegment) in enumerate(starts):
            if (
                len(subsegment) >= 4
                and str(subsegment[1]) == "lib"
                and str(subsegment[2]) == "libultra"
            ):
                first_lib_index = index
                break

        if first_lib_index is None:
            break

        fr_start = starts[first_lib_index][0]
        fr_end: int | None = None

        for index in range(first_lib_index + 1, len(starts)):
            start, subsegment = starts[index]
            is_libultra = (
                len(subsegment) >= 4
                and str(subsegment[1]) == "lib"
                and str(subsegment[2]) == "libultra"
            )
            is_pad = len(subsegment) >= 2 and str(subsegment[1]) == "pad"

            if not is_libultra and not is_pad:
                fr_end = start
                break

        if fr_end is None:
            raise SystemExit("ERROR: could not determine NP3F libultra end.")

        return fr_start, fr_end

    raise SystemExit("ERROR: could not locate NP3F libultra range in canonical YAML.")


def load_relocated_libultra_symbols(
    symbol_path: Path,
    fr_rom_start: int,
    fr_rom_end: int,
) -> list[dict[str, Any]]:
    if not symbol_path.is_file():
        raise SystemExit(
            "ERROR: vendored libultra symbol table not found: "
            f"{symbol_path}\n"
            "Download config/np3f_libultra_symbols_us.json from the project repo."
        )

    payload = json.loads(symbol_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"ERROR: invalid libultra symbol table: {symbol_path}")

    raw_symbols = payload.get("symbols")
    if not isinstance(raw_symbols, list):
        raise SystemExit(
            f"ERROR: libultra symbol table has no symbols array: {symbol_path}"
        )

    expected_size = US_LIBULTRA_ROM_END - US_LIBULTRA_ROM_START
    actual_size = fr_rom_end - fr_rom_start
    if actual_size != expected_size:
        raise SystemExit(
            "ERROR: NP3F libultra extent does not match pinned NP3E extent: "
            f"FR=0x{actual_size:X}, US=0x{expected_size:X}."
        )

    declared_count = payload.get("symbol_count")
    if declared_count is not None and int(declared_count) != len(raw_symbols):
        raise SystemExit(
            "ERROR: libultra symbol table count mismatch: "
            f"declared={declared_count}, actual={len(raw_symbols)}."
        )

    delta = fr_rom_start - US_LIBULTRA_ROM_START
    us_vram_start = US_TEXT_VRAM_START + (
        US_LIBULTRA_ROM_START - US_TEXT_ROM_START
    )
    us_vram_end = US_TEXT_VRAM_START + (
        US_LIBULTRA_ROM_END - US_TEXT_ROM_START
    )

    symbols: list[dict[str, Any]] = []
    for raw in raw_symbols:
        if not isinstance(raw, dict):
            continue

        name = str(raw.get("name", ""))
        us_vram_raw = raw.get("us_vram")
        if not name or us_vram_raw is None:
            continue

        us_vram = parse_int(us_vram_raw)
        if us_vram_start <= us_vram < us_vram_end:
            fr_vram = us_vram + delta

            generic_match = re.fullmatch(r"func_[0-9A-Fa-f]{8}", name)
            if generic_match:
                name = f"func_{fr_vram:08X}"

            symbols.append(
                {
                    "name": name,
                    "us_vram": us_vram,
                    "fr_vram": fr_vram,
                    "delta": delta,
                }
            )

    symbols.sort(key=lambda item: int(item["fr_vram"]))

    if not symbols:
        raise SystemExit(
            f"ERROR: no libultra function symbols recovered from {symbol_path}."
        )

    for index, item in enumerate(symbols):
        next_vram = (
            int(symbols[index + 1]["fr_vram"])
            if index + 1 < len(symbols)
            else US_TEXT_VRAM_START + (fr_rom_end - US_TEXT_ROM_START)
        )
        item["size"] = next_vram - int(item["fr_vram"])

    return symbols


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


def collect_hasm_expected_vrams(config: dict[str, Any]) -> dict[str, int]:
    expected: dict[str, int] = {}
    segments = config.get("segments")
    if not isinstance(segments, list):
        return expected

    for segment in segments:
        if not isinstance(segment, dict) or str(segment.get("name", "")) != "text":
            continue
        if "start" not in segment or "vram" not in segment:
            continue

        seg_rom = parse_int(segment["start"])
        seg_vram = parse_int(segment["vram"])
        subsegments = segment.get("subsegments")
        if not isinstance(subsegments, list):
            continue

        for subsegment in subsegments:
            if not isinstance(subsegment, list) or len(subsegment) < 3:
                continue
            if str(subsegment[1]) != "hasm":
                continue
            sub_rom = parse_int(subsegment[0])
            source_stem = Path(str(subsegment[2])).stem
            expected[source_stem] = seg_vram + (sub_rom - seg_rom)

    return expected


def sanitize_c_identifier(name: str) -> str:
    name = name.replace(".", "_").replace("$", "_")
    name = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not name:
        name = "func"
    if name[0].isdigit():
        name = "_" + name
    return name


def parse_asm_file(
    path: Path,
    section_name: str,
    expected_hasm_vram: int | None = None,
) -> list[Function]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    found: list[Function] = []
    file_vram_delta: int | None = None

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
                raw_vram = int(instr_match.group(2), 16)
                if expected_hasm_vram is not None and file_vram_delta is None:
                    file_vram_delta = expected_hasm_vram - raw_vram
                vram = raw_vram + (file_vram_delta or 0)
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


def read_be_u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"ROM read out of range at 0x{offset:X}")
    return int.from_bytes(data[offset:offset + 4], "big")


def inject_missing_leaf_jal_targets(
    rom: bytes,
    sections: dict[str, CodeSection],
    funcs: list[Function],
) -> list[dict[str, Any]]:
    # Some tiny hand-written helpers are valid jal targets but are absent from
    # upstream symbol files and may not receive a glabel from Splat. Only
    # auto-inject the safest pattern: a missing target in main text whose first
    # instruction is exactly "jr ra". Such helpers are 2-instruction leaf
    # thunks (jr ra + delay slot), so an 8-byte extent is unambiguous.
    text = sections["text"]
    text_start = text.vram
    text_end = text.vram + text.size

    starts = {(func.section, func.vram) for func in funcs}
    discovered: dict[int, dict[str, Any]] = {}

    for func in list(funcs):
        section = sections.get(func.section)
        if section is None:
            continue

        func_rom = section.rom + (func.vram - section.vram)
        for index in range(0, func.size, 4):
            rom_offset = func_rom + index
            if rom_offset + 4 > len(rom):
                break

            word = read_be_u32(rom, rom_offset)
            opcode = (word >> 26) & 0x3F
            if opcode != 0x03:  # jal
                continue

            pc = (func.vram + index) & 0xFFFFFFFF
            target = ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)

            if not (text_start <= target < text_end):
                continue
            if ("text", target) in starts:
                continue

            target_rom = text.rom + (target - text.vram)
            if target_rom + 8 > len(rom):
                continue

            first_word = read_be_u32(rom, target_rom)
            if first_word != 0x03E00008:  # jr ra
                continue

            delay_word = read_be_u32(rom, target_rom + 4)
            discovered.setdefault(
                target,
                {
                    "vram": target,
                    "rom": target_rom,
                    "first_word": first_word,
                    "delay_word": delay_word,
                    "called_from": [],
                },
            )
            discovered[target]["called_from"].append(
                {
                    "function": func.original_name,
                    "section": func.section,
                    "jal_vram": pc,
                }
            )

    injected: list[dict[str, Any]] = []
    for target in sorted(discovered):
        item = discovered[target]
        name = f"func_{target:08X}"
        funcs.append(
            Function(
                original_name=name,
                name=name,
                vram=target,
                size=8,
                asm_path=f"auto-leaf-jal-target:{name}",
                section="text",
            )
        )
        starts.add(("text", target))
        injected.append(
            {
                "name": name,
                **item,
                "size": 8,
            }
        )

    return injected


def toml_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def main() -> int:
    print(f"NP3F symbol generator version: {GENERATOR_VERSION}")
    parser = argparse.ArgumentParser()
    parser.add_argument("--yaml", type=Path, default=Path("yamls/fr/splat.yaml"))
    parser.add_argument("--asm-root", type=Path, default=Path("build/np3f/asm"))
    parser.add_argument("--output", type=Path, default=Path("build/np3f/recomp/np3f.syms.toml"))
    parser.add_argument("--report", type=Path, default=Path("build/np3f/analysis/recomp_symbols_report.json"))
    parser.add_argument(
        "--libultra-symbols",
        type=Path,
        default=Path("config/np3f_libultra_symbols_us.json"),
    )
    parser.add_argument(
        "--rom",
        type=Path,
        default=ROM_DEFAULT_PATH,
    )
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

    if not args.rom.is_file():
        raise SystemExit(f"ERROR: NP3F ROM not found: {args.rom}")
    rom_bytes = args.rom.read_bytes()

    sections = collect_sections(config)
    cpu_exclusions = collect_cpu_exclusions(config)
    fr_libultra_start, fr_libultra_end = collect_fr_libultra_range(config)
    relocated_libultra_symbols = load_relocated_libultra_symbols(
        args.libultra_symbols,
        fr_libultra_start,
        fr_libultra_end,
    )

    asm_files = sorted(args.asm_root.rglob("*.s"))
    if not asm_files:
        raise SystemExit("ERROR: no assembly files found. Run extraction with -DisassembleAll.")

    funcs: list[Function] = []
    files_without_funcs: list[str] = []
    unlabeled_code_chunks: list[UnlabeledCodeChunk] = []
    hasm_expected_vrams = collect_hasm_expected_vrams(config)
    hasm_vram_relocations: list[dict[str, Any]] = []

    for asm_path in asm_files:
        section_name = section_for_asm(asm_path)
        expected_hasm_vram = hasm_expected_vrams.get(asm_path.stem)
        parsed = parse_asm_file(asm_path, section_name, expected_hasm_vram)
        if expected_hasm_vram is not None and parsed:
            raw_first: int | None = None
            for raw_line in asm_path.read_text(encoding="utf-8", errors="replace").splitlines():
                raw_match = INSTR_RE.search(raw_line)
                if raw_match:
                    raw_first = int(raw_match.group(2), 16)
                    break
            if raw_first is not None:
                delta = expected_hasm_vram - raw_first
                if delta != 0:
                    hasm_vram_relocations.append(
                        {
                            "path": asm_path.as_posix(),
                            "stem": asm_path.stem,
                            "expected_vram": expected_hasm_vram,
                            "raw_first_vram": raw_first,
                            "delta": delta,
                        }
                    )
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

    manual_functions_injected: list[dict[str, Any]] = []
    known_starts = {(func.section, func.vram) for func in funcs}
    for (section_name, vram), (name, size) in KNOWN_NP3F_MANUAL_FUNCTIONS.items():
        if (section_name, vram) in known_starts:
            continue
        funcs.append(
            Function(
                original_name=name,
                name=name,
                vram=vram,
                size=size,
                asm_path=f"known-inline-helper:{name}",
                section=section_name,
            )
        )
        known_starts.add((section_name, vram))
        manual_functions_injected.append(
            {
                "section": section_name,
                "vram": vram,
                "name": name,
                "size": size,
            }
        )

    valid: list[Function] = []
    rejected: list[dict[str, Any]] = []
    verified_size_overrides: list[dict[str, Any]] = []

    for func in funcs:
        verified_size = KNOWN_NP3F_FUNCTION_SIZES.get((func.section, func.vram))
        if verified_size is not None and func.size != verified_size:
            verified_size_overrides.append(
                {
                    "section": func.section,
                    "vram": func.vram,
                    "name": func.original_name,
                    "detected_size": func.size,
                    "verified_size": verified_size,
                }
            )
            func.size = verified_size

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

    # Overlay calls can target libultra functions that Splat does not emit as
    # glabels in --disassemble-all output. Recover the complete pinned NP3E
    # libultra symbol set, relocate it by the NP3F block delta, then either
    # rename the detected function at that address or inject the missing one.
    relocated_libultra_applied: list[dict[str, Any]] = []
    valid_by_text_vram: dict[int, Function] = {
        func.vram: func for func in valid if func.section == "text"
    }

    for symbol in relocated_libultra_symbols:
        fr_vram = int(symbol["fr_vram"])
        known = valid_by_text_vram.get(fr_vram)

        if known is not None:
            old_name = known.original_name
            known.original_name = str(symbol["name"])
            relocated_libultra_applied.append(
                {
                    **symbol,
                    "action": "renamed_existing",
                    "detected_name": old_name,
                }
            )
            continue

        injected = Function(
            original_name=str(symbol["name"]),
            name=str(symbol["name"]),
            vram=fr_vram,
            size=int(symbol["size"]),
            asm_path=f"relocated-libultra:{symbol['name']}",
            section="text",
        )
        valid.append(injected)
        valid_by_text_vram[fr_vram] = injected
        relocated_libultra_applied.append(
            {
                **symbol,
                "action": "injected_missing",
            }
        )

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

        # A verified hand-written function boundary can be followed by inline
        # literal data that spimdisasm emits as an unlabeled code chunk. Do not
        # merge that chunk back into a function whose executable size was
        # explicitly verified above.
        if (preceding.section, preceding.vram) in KNOWN_NP3F_FUNCTION_SIZES:
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

    injected_leaf_jal_targets = inject_missing_leaf_jal_targets(
        rom_bytes,
        sections,
        valid,
    )

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
        "verified_size_overrides": verified_size_overrides,
        "hasm_vram_relocations": hasm_vram_relocations,
        "manual_functions_injected": manual_functions_injected,
        "relocated_libultra": {
            "symbol_table": str(args.libultra_symbols),
            "us_rom_start": US_LIBULTRA_ROM_START,
            "us_rom_end": US_LIBULTRA_ROM_END,
            "fr_rom_start": fr_libultra_start,
            "fr_rom_end": fr_libultra_end,
            "delta": fr_libultra_start - US_LIBULTRA_ROM_START,
            "symbols_considered": len(relocated_libultra_symbols),
            "symbols_applied": len(relocated_libultra_applied),
            "injected_missing": sum(
                item["action"] == "injected_missing"
                for item in relocated_libultra_applied
            ),
            "renamed_existing": sum(
                item["action"] == "renamed_existing"
                for item in relocated_libultra_applied
            ),
        },
        "relocated_libultra_symbols": relocated_libultra_applied,
        "merged_unlabeled_code_chunks": merged_unlabeled_code_chunks,
        "injected_leaf_jal_targets": injected_leaf_jal_targets,
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
    print(f"  verified size overrides  : {len(verified_size_overrides)}")
    print(f"  relocated hasm sources   : {len(hasm_vram_relocations)}")
    for relocation in hasm_vram_relocations:
        sign = "+" if relocation["delta"] >= 0 else "-"
        print(
            "    - "
            f"{relocation['stem']}: "
            f"{sign}0x{abs(relocation['delta']):X} -> "
            f"0x{relocation['expected_vram']:08X}"
        )
    for override in verified_size_overrides:
        print(
            "    - "
            f"0x{override['vram']:08X}: "
            f"0x{override['detected_size']:X} -> "
            f"0x{override['verified_size']:X}"
        )
    print(f"  manual funcs injected    : {len(manual_functions_injected)}")
    for manual in manual_functions_injected:
        print(
            "    - "
            f"0x{manual['vram']:08X}: "
            f"{manual['name']} size 0x{manual['size']:X}"
        )
    print(
        "  relocated libultra funcs : "
        f"{len(relocated_libultra_applied)} "
        f"(+0x{fr_libultra_start - US_LIBULTRA_ROM_START:X})"
    )
    print(
        "    injected / renamed      : "
        f"{sum(item['action'] == 'injected_missing' for item in relocated_libultra_applied)} / "
        f"{sum(item['action'] == 'renamed_existing' for item in relocated_libultra_applied)}"
    )
    print(f"  merged code continuations: {len(merged_unlabeled_code_chunks)}")
    print(f"  injected leaf jal funcs  : {len(injected_leaf_jal_targets)}")
    for leaf in injected_leaf_jal_targets:
        print(
            "    - "
            f"0x{leaf['vram']:08X} "
            f"(delay 0x{leaf['delay_word']:08X}, "
            f"callers {len(leaf['called_from'])})"
        )
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
