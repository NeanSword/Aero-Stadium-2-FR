#pragma once

#include <stdint.h>
#include <stdio.h>
#include "recomp.h"

extern void aerostadium2_osPiStartDma_recomp(uint8_t* rdram, recomp_context* ctx);
extern void aerostadium2_osEPiStartDma_recomp(uint8_t* rdram, recomp_context* ctx);

#define osPiStartDma_recomp aerostadium2_osPiStartDma_recomp
#define osEPiStartDma_recomp aerostadium2_osEPiStartDma_recomp

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

static inline int32_t* aerostadium2_np3f_mem_w_ptr(uint8_t* rdram, gpr address) {
    const uint32_t low = (uint32_t)address;

    // N64ModernRuntime models both status reads as idle/complete:
    //   AI_STATUS_REG 0xA450000C -> 0 (audio DMA FIFO not full)
    //   PI_STATUS_REG 0xA4600010 -> 0 (PI DMA/IO not busy)
    // Writes to these status registers only acknowledge/clear interrupts on
    // hardware, so treating them as disposable no-ops matches the current
    // host runtime model as well.
    if (low == 0xA450000Cu || low == 0xA4600010u) {
        static int32_t status_dummy = 0;
        status_dummy = 0;
        return &status_dummy;
    }

    const gpr normalized = aerostadium2_np3f_normalize_rdram_alias(address);
    return (int32_t*)(rdram + (normalized - 0xFFFFFFFF80000000ULL));
}

#undef MEM_W
#define MEM_W(offset, reg) \
    (*aerostadium2_np3f_mem_w_ptr(rdram, (gpr)((reg) + (offset))))

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


static inline recomp_func_t* aerostadium2_np3f_lookup_func(uint8_t* rdram, gpr target, recomp_context* ctx, const char* caller) {
    const int32_t target32 = (int32_t)target;

    if (target32 == (int32_t)0x80145230) {
        fprintf(
            stderr,
            "[lookup-trace] caller=%s target=0x%08X ra=0x%08X sp=0x%08X a0=0x%08X a1=0x%08X\n",
            caller,
            (uint32_t)target32,
            (uint32_t)ctx->r31,
            (uint32_t)ctx->r29,
            (uint32_t)ctx->r4,
            (uint32_t)ctx->r5
        );

        const gpr base = (gpr)(int64_t)target32;
        fprintf(
            stderr,
            "[lookup-header] %08X %08X %08X %08X %08X %08X %08X %08X\n",
            (uint32_t)MEM_W(0x00, base),
            (uint32_t)MEM_W(0x04, base),
            (uint32_t)MEM_W(0x08, base),
            (uint32_t)MEM_W(0x0C, base),
            (uint32_t)MEM_W(0x10, base),
            (uint32_t)MEM_W(0x14, base),
            (uint32_t)MEM_W(0x18, base),
            (uint32_t)MEM_W(0x1C, base)
        );
        fflush(stderr);
    }

    return get_function(target32);
}

#undef LOOKUP_FUNC
#define LOOKUP_FUNC(val) \
    aerostadium2_np3f_lookup_func(rdram, (val), ctx, __func__)
