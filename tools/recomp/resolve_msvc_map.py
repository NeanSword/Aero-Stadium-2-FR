#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

PREFERRED_RE = re.compile(r"Preferred load address is\s+([0-9A-Fa-f]+)")
SYMBOL_RE = re.compile(
    r"^\s*[0-9A-Fa-f]{4}:[0-9A-Fa-f]{8,16}\s+"
    r"(?P<name>\S+)\s+"
    r"(?P<abs>[0-9A-Fa-f]{8,16})\b"
)

def parse_int(text: str) -> int:
    return int(text, 0)

def main() -> int:
    ap = argparse.ArgumentParser(description="Resolve an AeroStadium2.exe RVA against an MSVC linker .map file.")
    ap.add_argument("map_file", type=Path)
    ap.add_argument("rva", type=parse_int, help="RVA such as 0x47BE09")
    ap.add_argument("--context", type=int, default=5, help="Number of nearby symbols to show")
    args = ap.parse_args()

    text = args.map_file.read_text(encoding="utf-8", errors="replace")
    preferred_match = PREFERRED_RE.search(text)
    if not preferred_match:
        raise SystemExit("Preferred load address not found in map file.")

    preferred_base = int(preferred_match.group(1), 16)
    target_abs = preferred_base + args.rva

    symbols: list[tuple[int, str, str]] = []
    for line in text.splitlines():
        m = SYMBOL_RE.match(line)
        if not m:
            continue
        symbols.append((int(m.group("abs"), 16), m.group("name"), line.rstrip()))

    if not symbols:
        raise SystemExit("No public/static symbols parsed from map file.")

    symbols.sort(key=lambda x: x[0])

    best_index = -1
    for i, (addr, _, _) in enumerate(symbols):
        if addr <= target_abs:
            best_index = i
        else:
            break

    print("=== Aero-Stadium-2-FR / MSVC crash RVA resolver ===")
    print(f"Map              : {args.map_file.resolve()}")
    print(f"Preferred base   : 0x{preferred_base:X}")
    print(f"Crash RVA        : 0x{args.rva:X}")
    print(f"Preferred address: 0x{target_abs:X}")
    print()

    if best_index < 0:
        print("No symbol exists before the requested address.")
        return 2

    best_addr, best_name, best_line = symbols[best_index]
    delta = target_abs - best_addr
    print(f"Nearest symbol   : {best_name}")
    print(f"Symbol address   : 0x{best_addr:X}")
    print(f"Offset in symbol : +0x{delta:X}")
    print(f"Map line         : {best_line}")
    print()
    print("Nearby symbols:")

    lo = max(0, best_index - args.context)
    hi = min(len(symbols), best_index + args.context + 1)
    for i in range(lo, hi):
        addr, name, line = symbols[i]
        mark = ">>" if i == best_index else "  "
        rel = target_abs - addr
        print(f"{mark} 0x{addr:X}  {name}  delta={rel:+#x}")
        print(f"   {line}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
