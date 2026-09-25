#include <cstdio>
#include <cstdint>
#include "recomp.h"

gpr get_entrypoint_address();
const char* get_rom_name();

int main() {
    const gpr entrypoint = get_entrypoint_address();
    std::printf("Aero Stadium 2 - bootstrap Windows NP3F\n");
    std::printf("Linkage du code recompile et de N64ModernRuntime: OK\n");
    std::printf("Point d entree NP3F: 0x%08X\n", static_cast<std::uint32_t>(entrypoint));
    std::printf("Nom ROM N64Recomp: %s\n", get_rom_name());
    return 0;
}