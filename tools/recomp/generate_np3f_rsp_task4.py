"""Configure recompilation of the second NP3F RSP task from the user's ROM.

The OSTask advertises a 0x1000-byte DMA, but executable instructions occupy
only 0xAF0 bytes. The remainder is unrelated ROM data, not RSP instructions.
No instruction emulation or replacement of task results is used.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct

ROM_SHA1 = "d7e13535b671024a92822db01507e87bd42f68ec"
TEXT_SHA256 = "0f56b7fd8dbe334877b26a0bba5e7e536ed0c21ff898841e77af6cdf30989b9e"
TEXT_OFFSET, TEXT_SIZE, TEXT_PC = 0x85F90, 0xAF0, 0x1080


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--output-config", type=Path, required=True)
    parser.add_argument("--output-cpp", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    if hashlib.sha1(rom).hexdigest() != ROM_SHA1:
        raise SystemExit("Unexpected ROM: the verified French NP3F ROM is required")
    code = rom[TEXT_OFFSET:TEXT_OFFSET + TEXT_SIZE]
    if hashlib.sha256(code).hexdigest() != TEXT_SHA256:
        raise SystemExit("Unexpected task-4 microcode")
    # Prove that the boot prefix is unnecessary: all static branches stay in
    # this range, and the only computed jumps are ordinary subroutine returns.
    for offset in range(0, len(code), 4):
        word = struct.unpack_from(">I", code, offset)[0]
        opcode = word >> 26
        target = None
        if opcode in (2, 3):
            target = (word << 2) & 0x1FFF
        elif opcode in (1, 4, 5, 6, 7):
            target = TEXT_PC + offset + 4 + struct.unpack_from(">h", code, offset + 2)[0] * 4
        elif opcode == 0 and (word & 63) in (8, 9):
            if word != 0x03E00008:
                raise SystemExit(f"Unexpected indirect branch at {TEXT_PC + offset:04X}")
        if target is not None and not TEXT_PC <= target < TEXT_PC + TEXT_SIZE:
            raise SystemExit(f"Branch outside compiled microcode: {target:04X}")
    for path in (args.output_config, args.output_cpp, args.output_report):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output_config.write_text(
        f'text_offset = 0x{TEXT_OFFSET:X}\ntext_size = 0x{TEXT_SIZE:X}\n'
        f'text_address = 0x0400{TEXT_PC:04X}\n'
        f'rom_file_path = "{args.rom.resolve().as_posix()}"\n'
        f'output_file_path = "{args.output_cpp.resolve().as_posix()}"\n'
        'output_function_name = "task4_np3f"\nextra_indirect_branch_targets = []\n',
        encoding="utf-8", newline="\n")
    args.output_report.write_text(json.dumps({
        "rom_sha1": ROM_SHA1, "text_sha256": TEXT_SHA256,
        "text_rom": hex(TEXT_OFFSET), "text_size": hex(TEXT_SIZE),
        "entry_pc": hex(TEXT_PC), "task_type": 4,
        "task_ucode": "0x80085390", "task_ucode_data": "0x800A7E40",
        "task_ucode_data_size": "0x800",
    }, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("NP3F task-4 RSP configuration verified and generated (0xAF0 bytes).")


if __name__ == "__main__":
    main()
