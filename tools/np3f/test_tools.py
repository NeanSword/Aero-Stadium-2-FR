from n64rom import RomFormatError, normalize_to_z64
from relocate_offset import fragment_delta


def test_byte_order_normalization() -> None:
    assert normalize_to_z64(bytes.fromhex("80 37 12 40"), "z64") == bytes.fromhex("80 37 12 40")
    assert normalize_to_z64(bytes.fromhex("37 80 40 12"), "v64") == bytes.fromhex("80 37 12 40")
    assert normalize_to_z64(bytes.fromhex("40 12 37 80"), "n64") == bytes.fromhex("80 37 12 40")


def test_fragment_deltas() -> None:
    ranges = [
        {"first": 1, "last": 11, "delta_bytes": 32},
        {"first": 12, "last": 31, "delta_bytes": 48},
        {"first": 86, "last": 88, "delta_bytes": 3184},
    ]
    assert fragment_delta(1, ranges) == 32
    assert fragment_delta(31, ranges) == 48
    assert fragment_delta(88, ranges) == 3184

    try:
        fragment_delta(89, ranges)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for an unknown fragment")


def test_bad_byte_order() -> None:
    try:
        normalize_to_z64(b"\x00\x00\x00\x00", "invalid")
    except RomFormatError:
        pass
    else:
        raise AssertionError("Expected RomFormatError")


if __name__ == "__main__":
    test_byte_order_normalization()
    test_fragment_deltas()
    test_bad_byte_order()
    print("NP3F tool self-tests: OK")
