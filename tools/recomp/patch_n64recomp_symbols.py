"""Enable explicit cross-section relocations in the pinned symbol-file reader."""
from pathlib import Path
import argparse

TARGET_LOOKUP = '''const toml::table* target_table = (*config_sections)[target_index].as_table();
                                if (target_table == nullptr) {
                                    throw toml::parse_error("Reloc target is not a section table", reloc_el.source());
                                }
                                auto target_base = (*target_table)["vram"].value<uint32_t>();'''

def patch(source):
    path = source / 'src/config.cpp'
    text = path.read_text()
    if '// AERO_CROSS_SECTION_RELOCS_V1' in text:
        updated = text
        for qualifier in ('', 'template '):
            updated = updated.replace(f'auto target_base = (*config_sections)[target_index]["vram"].{qualifier}value<uint32_t>();', TARGET_LOOKUP)
        if updated != text:
            path.write_text(updated, newline='\n')
        return
    replacements = [
        ('[&ret, &rom, with_relocs](auto&& el)', '[&ret, &rom, with_relocs, config_sections](auto&& el)'),
        ('[&ret, &rom, &section, section_index](auto&& reloc_el)',
         '[&ret, &rom, &section, section_index, config_sections](auto&& reloc_el)'),
        ('cur_reloc.target_section_offset = target_vram.value() - section.ram_addr;', '''// AERO_CROSS_SECTION_RELOCS_V1
                                uint32_t target_index = reloc_el["target_section"].template value<uint32_t>().value_or(section_index);
                                if (target_index >= config_sections->size()) {
                                    throw toml::parse_error("Reloc target section out of bounds", reloc_el.source());
                                }
                                TARGET_LOOKUP_PLACEHOLDER
                                if (!target_base.has_value()) {
                                    throw toml::parse_error("Reloc target section missing vram", reloc_el.source());
                                }
                                cur_reloc.target_section_offset = target_vram.value() - target_base.value();'''),
        ('cur_reloc.target_section = section_index;', 'cur_reloc.target_section = static_cast<uint16_t>(target_index);'),
    ]
    for old, new in replacements:
        if text.count(old) != 1:
            raise SystemExit(f'Unexpected pinned N64Recomp source near {old}')
        text = text.replace(old, new.replace('TARGET_LOOKUP_PLACEHOLDER', TARGET_LOOKUP))
    path.write_text(text, newline='\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path('.local/n64recomp/src'))
    patch(parser.parse_args().source)
    print('N64Recomp cross-section symbol adapter installed.')
