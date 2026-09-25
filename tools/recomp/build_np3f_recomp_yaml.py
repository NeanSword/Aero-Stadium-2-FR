from __future__ import annotations

import argparse
from pathlib import Path


STALE_CODE_SYMBOL_MARKER = "upstream/pokestadiumgs/linker_scripts/us/symbol_addrs_code.txt"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build an NP3F Splat YAML for static recompilation. "
            "The canonical layout is preserved, but stale NP3E function symbols "
            "are removed so Splat can detect NP3F function boundaries."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("yamls/fr/splat.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/np3f/recomp/splat.recomp.yaml"),
    )
    args = parser.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"ERROR: canonical YAML not found: {args.input}")

    text = args.input.read_text(encoding="utf-8")
    lines = text.splitlines()

    removed = [
        line for line in lines
        if STALE_CODE_SYMBOL_MARKER in line
    ]

    if len(removed) != 1:
        raise SystemExit(
            "ERROR: expected exactly one stale NP3E code-symbol entry in "
            f"{args.input}, found {len(removed)}."
        )

    output_lines: list[str] = []
    inserted_banner = False

    for line in lines:
        if STALE_CODE_SYMBOL_MARKER in line:
            continue

        output_lines.append(line)

        if not inserted_banner and line.startswith("# Aero-Stadium-2-FR"):
            output_lines.append(
                "# N64Recomp extraction variant: NP3E code function symbols removed."
            )
            output_lines.append(
                "# Function boundaries are redetected directly from NP3F machine code."
            )
            inserted_banner = True

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "\n".join(output_lines) + "\n",
        encoding="utf-8",
    )

    print("NP3F recompilation Splat YAML generated:")
    print(f"  source  : {args.input}")
    print(f"  output  : {args.output}")
    print("  removed : upstream NP3E symbol_addrs_code.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
