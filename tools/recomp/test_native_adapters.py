"""ROM-free regression checks for native relocation metadata."""
import struct
import unittest
from add_np3f_relocations import fragment_relocs

class FragmentRelocationTests(unittest.TestCase):
    def fixture(self):
        rom = bytearray(0x100)
        rom[8:16] = b'FRAGMENT'
        def put(offset, value): struct.pack_into('>I', rom, offset, value)
        put(0x14, 0x80)
        put(0x18, 0x100)
        put(0x20, 0x3C088311) # lui t0, 0x8311
        put(0x24, 0x8D098004) # lw t1, -0x7FFC(t0) -> 0x83108004
        put(0x28, 0x0C000000 | ((0x82200020 & 0x0FFFFFFF) >> 2))
        put(0x30, 0x82200040)
        put(0x80, 4)
        for index, value in enumerate((0x85000020, 0x86000024, 0x04000028, 0x82000030)):
            put(0x84 + index * 4, value)
        return rom, dict(name='fragment_test', rom=0, vram=0x83100000, size=0x100)

    def test_signed_low_half_and_external_targets(self):
        rom, section = self.fixture()
        relocs = fragment_relocs(rom, section, {0x83100000: 1, 0x82200000: 2})
        self.assertEqual([r['target_vram'] for r in relocs], [0x83108004, 0x83108004, 0x82200020, 0x82200040])
        self.assertEqual([r['target_section'] for r in relocs], [1, 1, 2, 2])
        self.assertEqual([r['type'] for r in relocs], ['R_MIPS_HI16', 'R_MIPS_LO16', 'R_MIPS_26', 'R_MIPS_32'])

    def test_unknown_fragment_fails(self):
        rom, section = self.fixture()
        with self.assertRaisesRegex(ValueError, 'Unknown fragment target'):
            fragment_relocs(rom, section, {0x83100000: 1})

    def test_missing_high_half_fails(self):
        rom, section = self.fixture()
        struct.pack_into('>I', rom, 0x84, 0x86000024)
        with self.assertRaisesRegex(ValueError, 'LO16 without HI16'):
            fragment_relocs(rom, section, {0x83100000: 1, 0x82200000: 2})

    def test_invalid_table_extent_fails(self):
        rom, section = self.fixture()
        struct.pack_into('>I', rom, 0x80, 999)
        with self.assertRaisesRegex(ValueError, 'Invalid relocation extent'):
            fragment_relocs(rom, section, {})

if __name__ == '__main__': unittest.main()
