#pragma once

#include <stdint.h>
#include "recomp.h"

// Pokemon Stadium 2 FR uses KSEG1 aliases of main RDRAM in a few runtime
// paths. N64Recomp's generic MEM_* macros currently treat all generated
// addresses relative to KSEG0, so an address such as 0xA00DB122 would land
// 0x20000000 bytes past its KSEG0 alias and hit the runtime's guard region.
//
// Only normalize the KSEG1 window that aliases the console's 8 MiB RDRAM.
// Do not normalize the rest of KSEG1: addresses such as 0xA4000000 are MMIO
// and must remain visible as unsupported accesses until they receive a
// dedicated runtime translation.
static inline gpr aerostadium2_np3f_normalize_rdram_alias(gpr address) {
    const uint32_t low = (uint32_t)address;
    if (low >= 0xA0000000u && low < 0xA0800000u) {
        const uint32_t kseg0 = low - 0x20000000u;
        return (gpr)(int64_t)(int32_t)kseg0;
    }

    return address;
}

#define AEROSTADIUM2_NP3F_MEM_ADDR(offset, reg) \
    aerostadium2_np3f_normalize_rdram_alias((gpr)((reg) + (offset)))

#undef MEM_W
#define MEM_W(offset, reg) \
    (*(int32_t*)(rdram + (AEROSTADIUM2_NP3F_MEM_ADDR((offset), (reg)) - 0xFFFFFFFF80000000ULL)))

#undef MEM_H
#define MEM_H(offset, reg) \
    (*(int16_t*)(rdram + ((AEROSTADIUM2_NP3F_MEM_ADDR((offset), (reg)) ^ 2) - 0xFFFFFFFF80000000ULL)))

#undef MEM_B
#define MEM_B(offset, reg) \
    (*(int8_t*)(rdram + ((AEROSTADIUM2_NP3F_MEM_ADDR((offset), (reg)) ^ 3) - 0xFFFFFFFF80000000ULL)))

#undef MEM_HU
#define MEM_HU(offset, reg) \
    (*(uint16_t*)(rdram + ((AEROSTADIUM2_NP3F_MEM_ADDR((offset), (reg)) ^ 2) - 0xFFFFFFFF80000000ULL)))

#undef MEM_BU
#define MEM_BU(offset, reg) \
    (*(uint8_t*)(rdram + ((AEROSTADIUM2_NP3F_MEM_ADDR((offset), (reg)) ^ 3) - 0xFFFFFFFF80000000ULL)))

#undef SD
#define SD(val, offset, reg) { \
    const gpr aerostadium2_np3f_sd_addr = AEROSTADIUM2_NP3F_MEM_ADDR((offset), (reg)); \
    *(uint32_t*)(rdram + ((aerostadium2_np3f_sd_addr + 4) - 0xFFFFFFFF80000000ULL)) = (uint32_t)((gpr)(val) >> 0); \
    *(uint32_t*)(rdram + ((aerostadium2_np3f_sd_addr + 0) - 0xFFFFFFFF80000000ULL)) = (uint32_t)((gpr)(val) >> 32); \
}
