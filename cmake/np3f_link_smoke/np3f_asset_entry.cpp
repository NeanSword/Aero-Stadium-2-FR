#include "recomp.h"
#include <cstdint>
#include <cstring>

namespace {
thread_local uint32_t asset_result;

uint32_t word(const uint8_t* rdram, uint32_t offset) {
    uint32_t result;
    std::memcpy(&result, rdram + offset, sizeof(result));
    return result;
}

// Native translation of the verified seven-instruction asset accessor.
// It saves a1 to the argument area and returns the descriptor only for a0=0.
void asset_accessor(uint8_t* rdram, recomp_context* ctx) {
    MEM_W(4, ctx->r29) = static_cast<int32_t>(ctx->r5);
    ctx->r3 = ctx->r4 == 0 ? static_cast<int32_t>(asset_result) : 0;
    ctx->r2 = ctx->r3;
}
}

extern "C" recomp_func_t* aero_lookup_asset(uint8_t* rdram, int32_t target) {
    const uint32_t address = static_cast<uint32_t>(target);
    if (address < 0x80000020u || address > 0x807FFFE4u || (address & 3)) return nullptr;
    const uint32_t offset = address - 0x80000000u;
    const uint32_t base = offset - 0x20;
    if (word(rdram, base + 8) != 0x46524147 || word(rdram, base + 12) != 0x4D454E54)
        return nullptr;
    // All instructions except the relocated address halves must match exactly.
    if (word(rdram, offset) != 0xAFA50004 || word(rdram, offset + 4) != 0x14800003 ||
        word(rdram, offset + 8) != 0x00001825 ||
        (word(rdram, offset + 12) & 0xFFFF0000) != 0x3C030000 ||
        (word(rdram, offset + 16) & 0xFFFF0000) != 0x24630000 ||
        word(rdram, offset + 20) != 0x03E00008 || word(rdram, offset + 24) != 0x00601025)
        return nullptr;
    const uint32_t result = (word(rdram, offset + 12) << 16) +
        static_cast<int16_t>(word(rdram, offset + 16));
    const uint64_t end = uint64_t(0x80000000u + base) + word(rdram, base + 0x1C);
    if (end > 0x80800000ULL || result < address + 28 || uint64_t(result) + 0x18 > end)
        return nullptr;
    asset_result = result;
    return asset_accessor;
}
