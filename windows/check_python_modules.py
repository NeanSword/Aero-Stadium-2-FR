import importlib
import sys

REQUIRED = ("splat", "rabbitizer", "spimdisasm")


def main() -> int:
    missing = []
    for name in REQUIRED:
        try:
            module = importlib.import_module(name)
        except Exception as exc:
            missing.append((name, f"{type(exc).__name__}: {exc}"))
        else:
            version = getattr(module, "__version__", None)
            suffix = f" ({version})" if version else ""
            print(f"{name}: OK{suffix}")

    if missing:
        print("\nMissing/broken Python modules:", file=sys.stderr)
        for name, reason in missing:
            print(f"  - {name}: {reason}", file=sys.stderr)
        return 1

    print("splat/rabbitizer/spimdisasm: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
