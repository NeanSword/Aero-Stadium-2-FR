"""ROM-free regression checks for native relocation metadata."""
import struct
import unittest
from pathlib import Path
from types import SimpleNamespace
from add_np3f_relocations import fragment_relocs
from generate_np3f_symbols import inject_fragment_trampolines

class FragmentExportTests(unittest.TestCase):
    def test_export_to_another_fragment_and_unknown_target(self):
        rom = bytearray(0x100)
        struct.pack_into('>I', rom, 0x14, 0x80)
        struct.pack_into('>I', rom, 0x20, 0x09041439)  # J 0x841050E4
        struct.pack_into('>I', rom, 0x28, 0x0904143A)  # Unknown target
        section = SimpleNamespace(name='fragment26', rom=0, vram=0x81000000)
        funcs = [SimpleNamespace(section='fragment26', vram=0x81000030),
                 SimpleNamespace(section='fragment79', vram=0x841050E4)]
        added = inject_fragment_trampolines(rom, {'fragment26': section}, funcs)
        self.assertEqual(added, [dict(section='fragment26', vram=0x81000020, target=0x841050E4)])

class RecompHookTests(unittest.TestCase):
    def test_task_completion_poll_yields_only_when_not_ready(self):
        config = Path("recomp/np3f.toml").read_text(encoding="utf-8")
        expected = "\n".join([
            "[[patches.hook]]",
            'func = "func_8000201C"',
            "before_vram = 0x80002038",
            'text = "if ((int32_t)ctx->r3 <= 0) aero_poll_events(rdram);"',
        ])
        self.assertEqual(config.count(expected), 1)
        self.assertNotIn('func = "func_80003AC0"\nbefore_vram = 0x80003BB0', config)


class MemoryCompatTests(unittest.TestCase):
    def test_rdram_alias_normalization_covers_zero_extended_kseg0_and_kseg1(self):
        header = Path("cmake/np3f_generated_smoke/np3f_memory_compat.h").read_text(encoding="utf-8")
        self.assertIn("low >= 0x80000000u && low < 0x80800000u", header)
        self.assertIn("return (gpr)(int64_t)(int32_t)low;", header)
        self.assertIn("low >= 0xA0000000u && low < 0xA0800000u", header)
        self.assertIn("const uint32_t kseg0 = low - 0x20000000u;", header)
        self.assertNotIn("low & 0x1FFFFFFF", header)
        self.assertIn("static inline uint64_t aerostadium2_np3f_load_doubleword(", header)
        self.assertIn("#undef LD", header)
        self.assertIn("aerostadium2_np3f_load_doubleword(rdram", header)
        self.assertIn("MEM_W(offset + 4, reg)", header)
        self.assertNotIn("#define LD(offset, reg) \\\n    load_doubleword(rdram, offset, reg)", header)


class ManualFunctionBoundaryTests(unittest.TestCase):
    def test_fragment10_runtime_indirect_target_is_known(self):
        from generate_np3f_symbols import KNOWN_NP3F_MANUAL_FUNCTIONS
        self.assertEqual(
            KNOWN_NP3F_MANUAL_FUNCTIONS[("fragment10", 0x82800490)],
            ("func_82800490", 0x190),
        )


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
