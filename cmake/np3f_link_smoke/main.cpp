#include <cstdio>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <vector>

#include "recomp.h"
#include "xxHash/xxh3.h"

namespace aerostadium2 { void register_np3f_overlays(); }

gpr get_entrypoint_address();
const char* get_rom_name();

static bool read_file(const std::filesystem::path& path, std::vector<uint8_t>& out) {
    std::ifstream file(path, std::ios::binary);
    if (!file.good()) {
        return false;
    }
    file.seekg(0, std::ios::end);
    const auto size = file.tellg();
    if (size <= 0) {
        return false;
    }
    out.resize(static_cast<size_t>(size));
    file.seekg(0, std::ios::beg);
    file.read(reinterpret_cast<char*>(out.data()), static_cast<std::streamsize>(out.size()));
    return file.good() || file.eof();
}

int main() {
    aerostadium2::register_np3f_overlays();
    const gpr entrypoint = get_entrypoint_address();

    std::printf("Aero Stadium 2 - bootstrap Windows NP3F\n");
    std::printf("Linkage du code recompile et de N64ModernRuntime: OK\n");
    std::printf("Overlays NP3F enregistres: OK\n");
    std::printf("Point d entree NP3F: 0x%08X\n", static_cast<std::uint32_t>(entrypoint));
    std::printf("Nom ROM N64Recomp: %s\n", get_rom_name());

    const auto rom_path = std::filesystem::current_path() / "baseroms" / "fr" / "baserom.z64";
    std::vector<uint8_t> rom;
    if (read_file(rom_path, rom)) {
        const uint64_t xxh3 = XXH3_64bits(rom.data(), rom.size());
        std::printf("ROM NP3F locale: %s\n", rom_path.string().c_str());
        std::printf("Taille ROM: %llu octets\n", static_cast<unsigned long long>(rom.size()));
        std::printf("XXH3-64 NP3F: 0x%016llX\n", static_cast<unsigned long long>(xxh3));
    }
    else {
        std::printf("ROM NP3F locale introuvable pour le probe XXH3: %s\n", rom_path.string().c_str());
    }

    return 0;
}
