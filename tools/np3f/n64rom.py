from __future__ import annotations

from pathlib import Path


MAGICS = {
    b"\x80\x37\x12\x40": "z64",
    b"\x37\x80\x40\x12": "v64",
    b"\x40\x12\x37\x80": "n64",
}


class RomFormatError(ValueError):
    pass


def detect_byte_order(path: Path) -> str:
    with path.open("rb") as stream:
        magic = stream.read(4)
    try:
        return MAGICS[magic]
    except KeyError as exc:
        raise RomFormatError(
            f"Unknown N64 byte order/header magic: {magic.hex(' ')}"
        ) from exc


def normalize_to_z64(data: bytes, byte_order: str) -> bytes:
    if byte_order == "z64":
        return data
    if len(data) % 4:
        raise RomFormatError("ROM size must be divisible by 4.")

    buf = bytearray(data)

    if byte_order == "v64":
        for i in range(0, len(buf), 2):
            buf[i], buf[i + 1] = buf[i + 1], buf[i]
        return bytes(buf)

    if byte_order == "n64":
        for i in range(0, len(buf), 4):
            a, b, c, d = buf[i:i + 4]
            buf[i:i + 4] = bytes((d, c, b, a))
        return bytes(buf)

    raise RomFormatError(f"Unsupported byte order: {byte_order}")


def read_normalized(path: Path) -> bytes:
    data = path.read_bytes()
    return normalize_to_z64(data, detect_byte_order(path))
