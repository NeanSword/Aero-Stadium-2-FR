#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

FUNC_HEADER = re.compile(r'^\s*(?:RECOMP_FUNC\s+)?void\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(')

def extract_function(lines: list[str], name: str):
    start = None
    depth = 0
    seen_open = False
    for i, line in enumerate(lines):
        m = FUNC_HEADER.search(line)
        if start is None:
            if m and m.group(1) == name:
                start = i
        if start is not None:
            depth += line.count("{")
            if "{" in line:
                seen_open = True
            depth -= line.count("}")
            if seen_open and depth == 0:
                return start, i
    return None

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--generated-dir", type=Path, default=Path("generated/recomp/np3f"))
    p.add_argument("--output", type=Path, default=Path("build/np3f/analysis/boot_functions.txt"))
    p.add_argument(
        "--functions",
        nargs="+",
        default=["func_80009EBC", "func_80009DE4", "func_80001460"],
    )
    args = p.parse_args()

    sources = sorted(args.generated_dir.glob("funcs_*.c"))
    if not sources:
        raise SystemExit(f"No generated funcs_*.c in {args.generated_dir}")

    found = {}
    for path in sources:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for name in args.functions:
            if name in found:
                continue
            span = extract_function(lines, name)
            if span:
                a, b = span
                found[name] = (path, a + 1, b + 1, lines[a:b+1])

    out = []
    out.append("=== Aero-Stadium-2-FR / NP3F exact boot function extraction ===")
    out.append(f"Generated directory: {args.generated_dir.resolve()}")
    out.append("")
    for name in args.functions:
        out.append("=" * 90)
        out.append(f"FUNCTION {name}")
        item = found.get(name)
        if item is None:
            out.append("NOT FOUND")
            out.append("")
            continue
        path, a, b, body = item
        out.append(f"Source: {path.name}:{a}-{b}")
        out.append("-" * 90)
        for lineno, line in enumerate(body, a):
            out.append(f"{lineno:6}: {line}")
        out.append("")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Report written: {args.output}")
    for name in args.functions:
        print(f"{name}: {'FOUND' if name in found else 'NOT FOUND'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
