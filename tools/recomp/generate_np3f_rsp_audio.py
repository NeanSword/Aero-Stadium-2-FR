#!/usr/bin/env python3
"""Generate the NP3F Pokemon Stadium 2 audio RSPRecomp configuration.

This script intentionally derives the French ucode-data ROM offset from the
canonical NP3F main-segment mapping instead of copying the US offset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

EXPECTED_SHA1 = "d7e13535b671024a92822db01507e87bd42f68ec"

MAIN_ROM_START = 0x001000
MAIN_VRAM_START = 0x80000400

AUDIO_TEXT_ROM = 0x001060
AUDIO_TEXT_SIZE = 0x1000
AUDIO_TEXT_ADDRESS = 0x04001000
AUDIO_TEXT_WORD0 = 0x340A0FC0
AUDIO_TEXT_WORD1 = 0x8D420018

# Observed directly from NP3F OSTask logging on 2026-09-27.
AUDIO_UCODE_DATA_VRAM = 0x80087010
AUDIO_UCODE_DATA_SIZE = 0x2DF

HANDLER_TABLE_START = 0x10
HANDLER_TABLE_END = 0x40
HANDLER_PC_MIN = 0x1000
HANDLER_PC_MAX = 0x2000


def vram_to_main_rom(vram: int) -> int:
    if vram < MAIN_VRAM_START:
        raise ValueError(f"VRAM 0x{vram:08X} is before the NP3F main segment")
    return MAIN_ROM_START + (vram - MAIN_VRAM_START)


def read_be_u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise ValueError(f"u32 read outside ROM at 0x{offset:X}")
    return struct.unpack_from(">I", data, offset)[0]


def read_be_u16(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 2 > len(data):
        raise ValueError(f"u16 read outside ROM at 0x{offset:X}")
    return struct.unpack_from(">H", data, offset)[0]


def toml_path(path: Path) -> str:
    # Forward slashes work with std::filesystem on Windows and avoid TOML
    # backslash escaping pitfalls.
    return path.resolve().as_posix().replace('"', '\\"')


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate NP3F audio RSPRecomp TOML from the local French ROM."
    )
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--output-config", type=Path, required=True)
    parser.add_argument("--output-cpp", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    args = parser.parse_args()

    rom_path = args.rom.resolve()
    if not rom_path.is_file():
        raise SystemExit(f"ROM not found: {rom_path}")

    rom = rom_path.read_bytes()
    sha1 = hashlib.sha1(rom).hexdigest()
    if sha1.lower() != EXPECTED_SHA1:
        raise SystemExit(
            "Unexpected NP3F ROM SHA-1: "
            f"{sha1} (expected {EXPECTED_SHA1})"
        )

    if AUDIO_TEXT_ROM + AUDIO_TEXT_SIZE > len(rom):
        raise SystemExit("Audio microcode range exceeds ROM size")

    word0 = read_be_u32(rom, AUDIO_TEXT_ROM)
    word1 = read_be_u32(rom, AUDIO_TEXT_ROM + 4)
    if word0 != AUDIO_TEXT_WORD0 or word1 != AUDIO_TEXT_WORD1:
        raise SystemExit(
            "NP3F audio microcode signature mismatch at ROM 0x1060: "
            f"got 0x{word0:08X} 0x{word1:08X}, "
            f"expected 0x{AUDIO_TEXT_WORD0:08X} 0x{AUDIO_TEXT_WORD1:08X}"
        )

    ucode_data_rom = vram_to_main_rom(AUDIO_UCODE_DATA_VRAM)
    if ucode_data_rom != 0x87C10:
        raise SystemExit(
            f"Internal NP3F mapping error: expected ucode_data ROM 0x87C10, "
            f"computed 0x{ucode_data_rom:X}"
        )

    if ucode_data_rom + AUDIO_UCODE_DATA_SIZE > len(rom):
        raise SystemExit("NP3F audio ucode_data range exceeds ROM size")

    targets: list[int] = []
    raw_targets: list[int] = []
    for rel in range(HANDLER_TABLE_START, HANDLER_TABLE_END, 2):
        pc = read_be_u16(rom, ucode_data_rom + rel)
        raw_targets.append(pc)
        if not (HANDLER_PC_MIN <= pc < HANDLER_PC_MAX):
            raise SystemExit(
                "Invalid NP3F audio handler PC "
                f"0x{pc:04X} at ROM 0x{ucode_data_rom + rel:X}; "
                "expected an IMEM address in [0x1000, 0x2000)."
            )
        if pc not in targets:
            targets.append(pc)

    args.output_config.parent.mkdir(parents=True, exist_ok=True)
    args.output_cpp.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.parent.mkdir(parents=True, exist_ok=True)

    target_lines = []
    for i in range(0, len(targets), 8):
        target_lines.append(
            "    " + " ".join(f"0x{pc:04X}," for pc in targets[i : i + 8])
        )

    config = f"""# Aero-Stadium-2-FR — NP3F audio microcode.
#
# Generated from the verified French NP3F ROM.
# Runtime evidence:
#   task type       = 2 (M_AUDTASK)
#   task ucode      = 0x80000460
#   task ucode size = 0x1000
#   task ucode_data = 0x80087010
#   ucode_data size = 0x2DF
#
# Canonical NP3F mapping:
#   ROM 0x1000 <-> VRAM 0x80000400
# therefore VRAM 0x80087010 maps to ROM 0x87C10.
#
# Do not replace the FR handler table with the US table. The US reference uses
# a different ucode_data ROM offset.
text_offset = 0x{AUDIO_TEXT_ROM:X}
text_size = 0x{AUDIO_TEXT_SIZE:X}
text_address = 0x{AUDIO_TEXT_ADDRESS:08X}
rom_file_path = "{toml_path(rom_path)}"
output_file_path = "{toml_path(args.output_cpp)}"
output_function_name = "aspMain_np3f"

extra_indirect_branch_targets = [
{chr(10).join(target_lines)}
]
"""

    args.output_config.write_text(config, encoding="utf-8", newline="\n")

    report = {
        "rom": str(rom_path),
        "sha1": sha1,
        "text_rom": f"0x{AUDIO_TEXT_ROM:X}",
        "text_size": f"0x{AUDIO_TEXT_SIZE:X}",
        "text_address": f"0x{AUDIO_TEXT_ADDRESS:08X}",
        "text_word0": f"0x{word0:08X}",
        "text_word1": f"0x{word1:08X}",
        "ucode_data_vram": f"0x{AUDIO_UCODE_DATA_VRAM:08X}",
        "ucode_data_rom": f"0x{ucode_data_rom:X}",
        "ucode_data_size": f"0x{AUDIO_UCODE_DATA_SIZE:X}",
        "handler_table_raw": [f"0x{x:04X}" for x in raw_targets],
        "handler_targets_unique": [f"0x{x:04X}" for x in targets],
        "handler_target_count": len(targets),
        "config": str(args.output_config.resolve()),
        "output_cpp": str(args.output_cpp.resolve()),
    }
    args.output_report.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print("NP3F audio RSP configuration generated.")
    print(f"ROM SHA-1        : {sha1}")
    print(f"Audio text       : ROM 0x{AUDIO_TEXT_ROM:X}, size 0x{AUDIO_TEXT_SIZE:X}")
    print(
        "Audio ucode_data : "
        f"VRAM 0x{AUDIO_UCODE_DATA_VRAM:08X} -> ROM 0x{ucode_data_rom:X}"
    )
    print(f"Handler targets  : {len(targets)} unique")
    print("  " + " ".join(f"0x{x:04X}" for x in targets))
    print(f"Config           : {args.output_config.resolve()}")
    print(f"Report           : {args.output_report.resolve()}")
    print(f"Generated C++    : {args.output_cpp.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
