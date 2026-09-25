#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

CALL_TOKEN = "osCreateThread_recomp"
FUNC_PATTERNS = [
    re.compile(r'^\s*RECOMP_FUNC\s+void\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('),
    re.compile(r'^\s*void\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('),
]

INTERESTING = (
    "ctx->r4",
    "ctx->r5",
    "ctx->r6",
    "ctx->r7",
    "ctx->r29",
    "MEM_W(0x10",
    "MEM_W(0x14",
    "MEM_W(16",
    "MEM_W(20",
    "0x800D05D0",
    "0x800D0F70",
    "0x800A82A0",
    "0x800A8840",
)

def find_function_name(lines: list[str], call_index: int) -> str:
    for i in range(call_index, -1, -1):
        line = lines[i]
        for pattern in FUNC_PATTERNS:
            match = pattern.search(line)
            if match:
                return match.group(1)
    return "<fonction inconnue>"

def collect_register_context(lines: list[str], call_index: int, lookback: int) -> list[tuple[int, str]]:
    start = max(0, call_index - lookback)
    selected: list[tuple[int, str]] = []

    for i in range(start, call_index + 1):
        line = lines[i]
        if i == call_index or any(token in line for token in INTERESTING):
            selected.append((i + 1, line.rstrip()))

    # If register filtering was too sparse, preserve a compact raw tail.
    if len(selected) <= 2:
        selected = [(i + 1, lines[i].rstrip()) for i in range(max(start, call_index - 20), call_index + 1)]

    return selected

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Locate NP3F osCreateThread_recomp callsites in generated N64Recomp C."
    )
    parser.add_argument(
        "--generated-dir",
        type=Path,
        default=Path("generated/recomp/np3f"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/np3f/analysis/thread_boot_callsites.txt"),
    )
    parser.add_argument("--lookback", type=int, default=120)
    args = parser.parse_args()

    generated_dir = args.generated_dir
    if not generated_dir.is_dir():
        raise SystemExit(f"Generated NP3F directory not found: {generated_dir}")

    sources = sorted(generated_dir.glob("funcs_*.c"))
    if not sources:
        raise SystemExit(f"No funcs_*.c files found in: {generated_dir}")

    matches: list[tuple[Path, int, str, list[tuple[int, str]]]] = []

    for path in sources:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines):
            if CALL_TOKEN not in line:
                continue
            func_name = find_function_name(lines, i)
            context = collect_register_context(lines, i, args.lookback)
            matches.append((path, i + 1, func_name, context))

    args.output.parent.mkdir(parents=True, exist_ok=True)

    out: list[str] = []
    out.append("=== Aero-Stadium-2-FR / NP3F thread boot callsite analysis ===")
    out.append(f"Generated directory: {generated_dir.resolve()}")
    out.append(f"C translation units: {len(sources)}")
    out.append(f"osCreateThread_recomp callsites: {len(matches)}")
    out.append("")
    out.append("Observed runtime threads:")
    out.append("  #1 id=1 pri=100 thread=0x800A82A0 sp=0x800A8840")
    out.append("  #2 id=2 pri=128 thread=0x800D05D0 sp=0x800D0F70")
    out.append("")
    out.append("osCreateThread ABI used by N64ModernRuntime:")
    out.append("  r4 = OSThread*, r5 = id, r6 = entrypoint, r7 = arg")
    out.append("  stack+0x10 = initial SP, stack+0x14 = priority")
    out.append("")

    for n, (path, line_no, func_name, context) in enumerate(matches, 1):
        out.append("=" * 78)
        out.append(f"[{n}] {path.name}:{line_no}")
        out.append(f"Caller: {func_name}")
        out.append("-" * 78)
        for ctx_line_no, text in context:
            out.append(f"{ctx_line_no:6}: {text}")
        out.append("")

    if not matches:
        out.append("No osCreateThread_recomp call was found.")
        out.append("This would indicate that thread creation is emitted through a different symbol name.")

    args.output.write_text("\n".join(out) + "\n", encoding="utf-8")

    print(f"Report written: {args.output}")
    print(f"Callsites found: {len(matches)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
