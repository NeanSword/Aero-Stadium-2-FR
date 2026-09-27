"""Build an RT64 development texture pack for the NP3F title screen.

The tool discovers RT64 hash mappings from a texture-dump ZIP captured from
Aero Stadium 2. It does not contain or redistribute game texture bytes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import zipfile
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:
    raise SystemExit(
        "Pillow is required. Install it in the project venv with: "
        "python -m pip install Pillow"
    ) from exc

TITLE_ANCHOR_HASH = "dd04fe928a08d2c1"

LAYOUT = {
    "background": {
        "start": 0x1A5360,
        "count": 300,
        "stride": 0x200,
        "size": (16, 16),
        "master": (320, 240),
        "columns": 20,
        "time_window_seconds": 2,
    },
    "logo": {
        "start": 0x215CC0,
        "count": 49,
        "stride": 0xBC0,
        "size": (376, 4),
        "master": (376, 196),
        "columns": 1,
    },
    "legal": {
        "start": 0x23A280,
        "count": 8,
        "stride": 0xD00,
        "size": (416, 8),
        "master": (416, 64),
        "columns": 1,
    },
}

SINGLETONS = {
    "press_start": {
        "hash": "8ddd84322afffbe2",
        "size": (200, 20),
        "path": "Title/UI/PressStart",
    },
    "dolby": {
        "hash": "f59608edae6d8d5a",
        "size": (88, 34),
        "path": "Title/UI/Dolby",
    },
    "expansion_pak": {
        "hash": "811653c2eab64947",
        "size": (216, 18),
        "path": "Title/UI/ExpansionPak",
    },
}


def _hash_from_name(name: str) -> str:
    return Path(name).name.split(".v5.", 1)[0]


def _timestamp(info: zipfile.ZipInfo) -> dt.datetime:
    return dt.datetime(*info.date_time)


def discover_dump(zip_path: Path) -> tuple[dict[int, list[dict]], dict[str, dict]]:
    by_address: dict[int, list[dict]] = {}
    by_hash: dict[str, dict] = {}

    with zipfile.ZipFile(zip_path) as archive:
        infos = {info.filename: info for info in archive.infolist()}
        for info in archive.infolist():
            if not info.filename.endswith(".v5.tile.json"):
                continue

            texture_hash = _hash_from_name(info.filename)
            tile = json.loads(archive.read(info.filename))
            rice_name = info.filename.replace(".tile.json", ".rice.json")
            if rice_name not in infos:
                continue

            rice = json.loads(archive.read(rice_name))
            record = {
                "hash": texture_hash,
                "address": int(rice["texture"]["address"]),
                "width": int(tile["width"]),
                "height": int(tile["height"]),
                "fmt": int(tile["tile"]["fmt"]),
                "siz": int(tile["tile"]["siz"]),
                "timestamp": _timestamp(info),
            }
            by_hash[texture_hash] = record
            by_address.setdefault(record["address"], []).append(record)

    return by_address, by_hash


def select_layout_records(
    by_address: dict[int, list[dict]],
    spec: dict,
    *,
    anchor_time: dt.datetime | None = None,
) -> list[dict]:
    records: list[dict] = []
    expected_size = tuple(spec["size"])
    max_delta = spec.get("time_window_seconds")

    for index in range(spec["count"]):
        address = spec["start"] + index * spec["stride"]
        candidates = [
            rec
            for rec in by_address.get(address, [])
            if (rec["width"], rec["height"]) == expected_size
        ]

        if anchor_time is not None and max_delta is not None:
            candidates = [
                rec
                for rec in candidates
                if 0 <= (rec["timestamp"] - anchor_time).total_seconds() <= max_delta
            ]

        if len(candidates) != 1:
            raise SystemExit(
                f"Expected exactly one texture at 0x{address:08X} "
                f"for size {expected_size}, found {len(candidates)}"
            )

        records.append(candidates[0])

    return records


def load_scaled_master(
    path: Path,
    base_size: tuple[int, int],
) -> tuple[Image.Image, int]:
    image = Image.open(path).convert("RGBA")
    base_width, base_height = base_size

    if image.width % base_width != 0 or image.height % base_height != 0:
        raise SystemExit(
            f"{path}: {image.width}x{image.height} is not an integer scale "
            f"of {base_width}x{base_height}"
        )

    scale_x = image.width // base_width
    scale_y = image.height // base_height
    if scale_x != scale_y or scale_x < 1:
        raise SystemExit(
            f"{path}: expected uniform integer scale, got {scale_x}x{scale_y}"
        )

    return image, scale_x


def add_entry(
    entries: list[dict],
    texture_hash: str,
    relative_path: str,
) -> None:
    entries.append(
        {
            "hashes": {"rt64": texture_hash},
            "path": relative_path,
            "operation": "preload",
        }
    )


def split_master(
    master_path: Path,
    base_size: tuple[int, int],
    records: list[dict],
    columns: int,
    output: Path,
    relative_dir: str,
    entries: list[dict],
) -> int:
    image, scale = load_scaled_master(master_path, base_size)

    for index, record in enumerate(records):
        x = (index % columns) * record["width"] * scale
        y = (index // columns) * record["height"] * scale
        crop = image.crop(
            (
                x,
                y,
                x + record["width"] * scale,
                y + record["height"] * scale,
            )
        )

        relative_path = f"{relative_dir}/{index:03d}_{record['hash']}"
        destination = output / f"{relative_path}.png"
        destination.parent.mkdir(parents=True, exist_ok=True)
        crop.save(destination)
        add_entry(entries, record["hash"], relative_path)

    return scale


def save_single(
    source: Path,
    spec: dict,
    output: Path,
    entries: list[dict],
) -> int:
    image, scale = load_scaled_master(source, tuple(spec["size"]))
    destination = output / f"{spec['path']}.png"
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)
    add_entry(entries, spec["hash"], spec["path"])
    return scale


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dump-zip", type=Path, required=True)
    parser.add_argument("--background", type=Path, required=True)
    parser.add_argument("--logo", type=Path, required=True)
    parser.add_argument("--legal-text", type=Path)
    parser.add_argument("--press-start", type=Path)
    parser.add_argument("--dolby", type=Path)
    parser.add_argument("--expansion-pak", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/np3f/hd_texture_pack"),
    )
    args = parser.parse_args()

    by_address, by_hash = discover_dump(args.dump_zip)
    anchor = by_hash.get(TITLE_ANCHOR_HASH)
    if anchor is None:
        raise SystemExit(
            f"Title-screen anchor hash {TITLE_ANCHOR_HASH} not found in dump"
        )

    background_records = select_layout_records(
        by_address,
        LAYOUT["background"],
        anchor_time=anchor["timestamp"],
    )
    logo_records = select_layout_records(by_address, LAYOUT["logo"])
    legal_records = select_layout_records(by_address, LAYOUT["legal"])

    args.output.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []

    background_scale = split_master(
        args.background,
        LAYOUT["background"]["master"],
        background_records,
        LAYOUT["background"]["columns"],
        args.output,
        "Title/Background",
        entries,
    )
    logo_scale = split_master(
        args.logo,
        LAYOUT["logo"]["master"],
        logo_records,
        LAYOUT["logo"]["columns"],
        args.output,
        "Title/Logo",
        entries,
    )

    if args.legal_text:
        split_master(
            args.legal_text,
            LAYOUT["legal"]["master"],
            legal_records,
            LAYOUT["legal"]["columns"],
            args.output,
            "Title/Legal",
            entries,
        )

    for argument_name, spec in SINGLETONS.items():
        source = getattr(args, argument_name)
        if source is not None:
            save_single(source, spec, args.output, entries)

    database = {
        "configuration": {
            "autoPath": "rt64",
            "configurationVersion": 3,
            "hashVersion": 5,
            "defaultOperation": "stream",
            "defaultShift": "half",
        },
        "operationFilters": [
            {"wildcard": "Title/*", "operation": "preload"},
        ],
        "textures": entries,
    }

    (args.output / "rt64.json").write_text(
        json.dumps(database, indent=4) + "\n",
        encoding="utf-8",
    )

    print(
        f"Background textures: {len(background_records)} "
        f"({background_scale}x)"
    )
    print(f"Logo textures: {len(logo_records)} ({logo_scale}x)")
    print(f"Legal strips discovered: {len(legal_records)}")
    print(f"RT64 entries written: {len(entries)}")
    print(f"Output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
