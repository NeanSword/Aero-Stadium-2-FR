"""Extract one generated N64Recomp function and summarize its memory accesses."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def extract_function(text: str, name: str) -> str | None:
    match = re.search(
        rf"(?m)^\s*(?:RECOMP_FUNC\s+)?void\s+{re.escape(name)}\s*\([^\n]*\)\s*\{{",
        text,
    )
    if match is None:
        return None

    start = match.start()
    brace = text.find("{", match.start(), match.end())
    if brace < 0:
        return None

    depth = 0
    in_string = False
    escaped = False
    for i in range(brace, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("name", nargs="?", default="func_81801420")
    parser.add_argument(
        "--generated-dir",
        type=Path,
        default=Path("generated/recomp/np3f"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/np3f/logs/generated_func_81801420.log"),
    )
    args = parser.parse_args()

    if not args.generated_dir.is_dir():
        raise SystemExit(f"Generated directory not found: {args.generated_dir}")

    found_path: Path | None = None
    function: str | None = None
    for source in sorted(args.generated_dir.glob("funcs_*.c")):
        text = source.read_text(encoding="utf-8", errors="replace")
        if args.name not in text:
            continue
        candidate = extract_function(text, args.name)
        if candidate is not None:
            found_path = source
            function = candidate
            break

    if found_path is None or function is None:
        raise SystemExit(
            f"Function {args.name} not found under {args.generated_dir}"
        )

    lines = function.splitlines()
    memory_patterns = re.compile(
        r"\b(?:MEM_[A-Z]+|LD|SD|do_(?:lwl|lwr|ldl|ldr|swl|swr|sdl|sdr))\s*\("
        r"|rdram\s*\+"
    )
    memory_lines = [
        (index + 1, line)
        for index, line in enumerate(lines)
        if memory_patterns.search(line)
    ]

    out: list[str] = []
    out.append(f"function={args.name}")
    out.append(f"source={found_path.as_posix()}")
    out.append(f"line_count={len(lines)}")
    out.append("")
    out.append("=== memory operations ===")
    if memory_lines:
        out.extend(f"{number:4}: {line}" for number, line in memory_lines)
    else:
        out.append("(none matched)")
    out.append("")
    out.append("=== complete generated function ===")
    out.extend(f"{index + 1:4}: {line}" for index, line in enumerate(lines))
    out.append("")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(out), encoding="utf-8")
    print(f"Generated function diagnostic written to: {args.output}")
    print(f"Source: {found_path}")
    print(f"Memory operations found: {len(memory_lines)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
