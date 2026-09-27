"""Read FRAGMENT relocation tables using the game's 800021E0 loader algorithm.

Only address metadata is emitted. Original code/data and ROM remain local.
Requires the cross-section symbol-reader adapter in patch_n64recomp_symbols.py.
"""
from pathlib import Path
import argparse
import collections
import json
import struct
import tomllib

def fragment_relocs(rom, section, targets):
    base = section['rom']
    def word(offset):
        if offset < 0 or base + offset + 4 > len(rom):
            raise ValueError('Relocation read outside ROM')
        return struct.unpack_from('>I', rom, base + offset)[0]
    if rom[base + 8:base + 16] != b'FRAGMENT':
        raise ValueError(f'Missing FRAGMENT header in {section["name"]}')
    table, extent = word(0x14), word(0x18)
    count = word(table)
    if table + 4 + count * 4 > extent or extent > section['size']:
        raise ValueError(f'Invalid relocation extent in {section["name"]}')
    high = {}
    relocs = {}
    def emit(offset, kind, address):
        slot = address & 0xFFF00000
        # Non-fragment targets are absolute and don't need generated relocation.
        if not 0x81000000 <= address < 0x90000000:
            return
        if slot not in targets:
            raise ValueError(f'Unknown fragment target 0x{address:08X} in {section["name"]}')
        relocs[offset] = dict(type=kind, vram=section['vram'] + offset,
                              target_vram=address, target_section=targets[slot])
    for index in range(count):
        entry = word(table + 4 + index * 4)
        kind, offset = (entry >> 24) & 0x7F, entry & 0xFFFFFF
        if offset % 4 or offset + 4 > table:
            raise ValueError(f'Invalid relocation site {offset:#x}')
        value = word(offset)
        if kind == 2:
            emit(offset, 'R_MIPS_32', value)
        elif kind == 4:
            emit(offset, 'R_MIPS_26', 0x80000000 | ((value << 2) & 0x0FFFFFFC))
        elif kind == 5:
            high[(value >> 16) & 31] = (offset, value & 0xFFFF)
        elif kind == 6:
            register = (value >> 21) & 31
            if register not in high:
                raise ValueError(f'LO16 without HI16 at {section["name"]}+{offset:#x}')
            hi_offset, hi_value = high[register]
            low = (value & 0x7FFF) - (value & 0x8000)
            address = ((hi_value << 16) + low) & 0xFFFFFFFF
            emit(hi_offset, 'R_MIPS_HI16', address)
            emit(offset, 'R_MIPS_LO16', address)
        else:
            raise ValueError(f'Unknown fragment relocation type {kind}')
    return sorted(relocs.values(), key=lambda r: r['vram'])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--rom', type=Path, default=Path('baseroms/fr/baserom.z64'))
    parser.add_argument('--symbols', type=Path, default=Path('build/np3f/recomp/np3f.syms.toml'))
    parser.add_argument('--report', type=Path, default=Path('build/np3f/analysis/native_relocations.json'))
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    sections = tomllib.loads(args.symbols.read_text())['section']
    targets = {s['vram']: i for i, s in enumerate(sections) if s['name'].startswith('fragment')}
    report = {}
    for section in sections:
        if section['name'].startswith('fragment'):
            section['relocs'] = fragment_relocs(rom, section, targets)
            report[section['name']] = dict(collections.Counter(r['type'] for r in section['relocs']))
    # Build the whole file before replacing it: validation failures leave it intact.
    lines = ['# NP3F symbols and relocations derived locally from the ROM.']
    for section in sections:
        lines += ['', '[[section]]', f'name = {json.dumps(section["name"])}']
        lines += [f'{key} = 0x{section[key]:X}' for key in ('rom', 'vram', 'size')]
        lines += ['functions = [']
        for func in section['functions']:
            lines += [f'  {{ name = {json.dumps(func["name"])}, vram = 0x{func["vram"]:X}, size = 0x{func["size"]:X} }},']
        lines += [']']
        if 'relocs' in section:
            lines += ['relocs = [']
            for reloc in section['relocs']:
                lines += ['  { ' + ', '.join(f'{k} = {json.dumps(v) if isinstance(v, str) else hex(v)}' for k, v in reloc.items()) + ' },']
            lines += [']']
    args.symbols.write_text('\n'.join(lines) + '\n', newline='\n')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(f'Added {sum(sum(v.values()) for v in report.values())} relocations in {len(report)} fragments.')

if __name__ == '__main__': main()
