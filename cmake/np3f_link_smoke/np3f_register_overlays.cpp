#include "librecomp/overlays.hpp"
#include "recomp_overlays.inl"
#include <array>
#include <cstdio>
#include <cstdlib>

namespace {
std::array<int, 240> fragment_sections;
std::array<bool, 240> fragment_loaded{};
uint8_t* guest_rdram = nullptr;
}

namespace aerostadium2 {
void set_overlay_rdram(uint8_t* rdram) { guest_rdram = rdram; }
}

extern "C" void unload_overlay_by_id(uint32_t id);

extern "C" void aero_unmap_fragment(uint32_t slot) {
    if (slot < fragment_loaded.size() && fragment_loaded[slot]) {
        unload_overlay_by_id(slot);
        fragment_loaded[slot] = false;
    }
}

extern "C" void aero_map_fragment(uint32_t slot, int32_t ram, uint32_t size) {
    if (slot >= fragment_sections.size() ||
        uint32_t(ram) < 0x80000000u || uint64_t(uint32_t(ram)) + size > 0x80800000ULL) {
        std::fprintf(stderr, "[fragment-map] Invalid slot=%u ram=%08X size=%08X\n", slot, uint32_t(ram), size);
        std::_Exit(23);
    }
    // Model assets share the fragment registry. Their exact accessor template
    // is handled by aero_lookup_asset; all guest data relocation still runs.
    if (fragment_sections[slot] < 0) {
        std::fprintf(stderr, "[fragment-map] No compiled section for slot=%u ram=%08X size=%08X\n",
            slot, uint32_t(ram), size);
        if (guest_rdram != nullptr && std::getenv("AERO_DUMP_FRAGMENTS") != nullptr) {
            const uint32_t offset = uint32_t(ram) - 0x80000000u;
            std::fprintf(stderr, "[fragment-header]");
            for (uint32_t i = 0; i < 32 && i < size; ++i)
                std::fprintf(stderr, " %02X", guest_rdram[(offset + i) ^ 3]);
            std::fprintf(stderr, "\n");
            char filename[80];
            std::snprintf(filename, sizeof(filename), "uncompiled_fragment_%03u.bin", slot);
            if (FILE* file = std::fopen(filename, "wb")) {
                for (uint32_t i = 0; i < size; ++i)
                    std::fputc(guest_rdram[(offset + i) ^ 3], file);
                std::fclose(file);
            }
        }
        return;
    }
    aero_unmap_fragment(slot);
    const auto& section = section_table[fragment_sections[slot]];
    // Map when Stadium registers the complete allocation, after all chunked
    // DMAs. A 0x1000-byte DMA is insufficient to register a larger code section.
    unload_overlays(ram, size);
    load_overlays(section.rom_addr, ram, section.size);
    fragment_loaded[slot] = true;
    std::fprintf(stderr, "[fragment-map] slot=%u rom=%08X ram=%08X size=%08X\n",
        slot, section.rom_addr, uint32_t(ram), size);
}

namespace aerostadium2 {

void register_np3f_overlays() {
    fragment_sections.fill(-1);
    for (size_t i = 1; i < ARRLEN(section_table); ++i) {
        const auto address = section_table[i].ram_addr;
        if (address < 0x81000000u || address >= 0x90000000u || (address & 0xFFFFFu)) {
            std::fprintf(stderr, "[fragment-map] Invalid link address %08X\n", address);
            std::exit(23);
        }
        fragment_sections[(address - 0x81000000u) >> 20] = static_cast<int>(i);
    }
    recomp::overlays::overlay_section_table_data_t sections {
        .code_sections = section_table,
        .num_code_sections = ARRLEN(section_table),
        .total_num_sections = num_sections,
    };

    recomp::overlays::overlays_by_index_t overlays {
        .table = fragment_sections.data(),
        .len = fragment_sections.size(),
    };

    recomp::overlays::register_overlays(sections, overlays);
}

} // namespace aerostadium2
