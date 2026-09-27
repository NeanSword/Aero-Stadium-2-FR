#pragma once

#include <stdint.h>
#include <stdio.h>
#include "recomp.h"

#ifdef __cplusplus
extern "C" {
#endif
extern recomp_func_t* aero_lookup_asset(uint8_t* rdram, int32_t target);
#ifdef __cplusplus
}
#endif

// Pokemon Stadium 2 FR reaches RDRAM through both KSEG0 and KSEG1 aliases.
// N64Recomp's MEM_* macros subtract the sign-extended KSEG0 base
// 0xFFFFFFFF80000000, so a zero-extended guest pointer such as 0x80204894
// would otherwise become an 0x80204894-byte host offset instead of 0x00204894.
// KSEG1 aliases have the analogous +0x20000000 problem.
//
// Normalize only the two 8 MiB windows that alias physical RDRAM. Do not
// normalize other KSEG0/KSEG1 addresses: fragment VRAM lives outside this
// window and addresses such as 0xA4000000 are MMIO.
static inline gpr aerostadium2_np3f_normalize_rdram_alias(gpr address) {
    const uint32_t low = (uint32_t)address;

    if (low >= 0x80000000u && low < 0x80800000u) {
        return (gpr)(int64_t)(int32_t)low;
    }

    if (low >= 0xA0000000u && low < 0xA0800000u) {
        const uint32_t kseg0 = low - 0x20000000u;
        return (gpr)(int64_t)(int32_t)kseg0;
    }

    return address;
}

#define AEROSTADIUM2_NP3F_MEM_ADDR(offset, reg) \
    aerostadium2_np3f_normalize_rdram_alias((gpr)((reg) + (offset)))

static inline int32_t* aerostadium2_np3f_mem_w_ptr(
    uint8_t* rdram,
    gpr address,
    const char* caller
) {
    const uint32_t low = (uint32_t)address;

    // PI_STATUS_REG: N64ModernRuntime models the PI as idle for this path.
    if (low == 0xA4600010u) {
        static int32_t pi_status_dummy = 0;
        pi_status_dummy = 0;
        return &pi_status_dummy;
    }

    const gpr normalized = aerostadium2_np3f_normalize_rdram_alias(address);
    return (int32_t*)(rdram + (normalized - 0xFFFFFFFF80000000ULL));
}

#undef MEM_W
#define MEM_W(offset, reg) \
    (*aerostadium2_np3f_mem_w_ptr(rdram, (gpr)((reg) + (offset)), __func__))

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

// recomp.h defines load_doubleword() before this compatibility header can
// replace MEM_W, so that helper permanently captures the raw KSEG0 subtraction.
// Override LD itself and rebuild the 64-bit load from our normalized MEM_W.
static inline uint64_t aerostadium2_np3f_load_doubleword(
    uint8_t* rdram,
    gpr offset,
    gpr reg
) {
    const uint64_t lo = (uint64_t)(uint32_t)MEM_W(offset + 4, reg);
    const uint64_t hi = (uint64_t)(uint32_t)MEM_W(offset + 0, reg);
    return lo | (hi << 32);
}

#undef LD
#define LD(offset, reg) \
    aerostadium2_np3f_load_doubleword(rdram, (gpr)(offset), (gpr)(reg))



static inline void aerostadium2_np3f_sprintf_prout_recomp(
    uint8_t* rdram,
    recomp_context* ctx
) {
    const gpr dst = ctx->r4;
    const gpr src = ctx->r5;
    const uint32_t count = (uint32_t)ctx->r6;

    // proutSprintf(dst, src, count) is a tiny static libultra helper:
    // memcpy(dst, src, count); return dst + count;
    //
    // Use MEM_B/MEM_BU rather than raw host memcpy so N64 byte addressing
    // (the XOR-3 byte lane mapping) remains correct for any alignment.
    for (uint32_t i = 0; i < count; ++i) {
        MEM_B((gpr)i, dst) = (int8_t)MEM_BU((gpr)i, src);
    }

    ctx->r2 = dst + (gpr)count;
}

static inline recomp_func_t* aerostadium2_np3f_lookup_func(uint8_t* rdram, gpr target, recomp_context* ctx, const char* caller) {
    const int32_t target32 = (int32_t)target;

    const uint32_t target_low = (uint32_t)target32;
    const int target_is_rdram =
        (target_low >= 0x80000000u && target_low < 0x80800000u) ||
        (target_low >= 0xA0000000u && target_low < 0xA0800000u);

    if (!target_is_rdram) {
        return get_function(target32);
    }

    const gpr base = aerostadium2_np3f_normalize_rdram_alias((gpr)(int64_t)target32);

    if ((uint32_t)target32 == 0x8007BFA8u) {
        static int reported_debug_prout = 0;
        if (!reported_debug_prout) {
            fprintf(
                stderr,
                "[sprintf-bridge] caller=%s target=0x%08X -> host proutSprintf\n",
                caller,
                (uint32_t)target32
            );
            fflush(stderr);
            reported_debug_prout = 1;
        }
        return aerostadium2_np3f_sprintf_prout_recomp;
    }
    const uint32_t word0 = (uint32_t)MEM_W(0x00, base);
    const uint32_t word1 = (uint32_t)MEM_W(0x04, base);
    const uint32_t magic0 = (uint32_t)MEM_W(0x08, base);
    const uint32_t magic1 = (uint32_t)MEM_W(0x0C, base);

    // Pokémon Stadium 2 fragment headers begin with an 8-byte executable
    // trampoline followed by the ASCII magic "FRAGMENT". These stubs contain
    // a pseudo-direct MIPS J whose target is encoded for the fragment's
    // runtime load address, so they cannot be compiled as ordinary static
    // functions at the fragment's nominal VRAM. Resolve the stub dynamically
    // and jump straight to the already-recompiled inner overlay function.
    if (magic0 == 0x46524147u && magic1 == 0x4D454E54u &&
        (word0 >> 26) == 0x02u && word1 == 0u) {
        const uint32_t runtime_pc = (uint32_t)target32;
        const uint32_t jump_target =
            ((runtime_pc + 4u) & 0xF0000000u) |
            ((word0 & 0x03FFFFFFu) << 2);

        recomp_func_t* asset = aero_lookup_asset(rdram, (int32_t)jump_target);
        if (asset != NULL) return asset;
        return get_function((int32_t)jump_target);
    }

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
        fprintf(
            stderr,
            "[lookup-header] %08X %08X %08X %08X %08X %08X %08X %08X\n",
            word0,
            word1,
            magic0,
            magic1,
            (uint32_t)MEM_W(0x10, base),
            (uint32_t)MEM_W(0x14, base),
            (uint32_t)MEM_W(0x18, base),
            (uint32_t)MEM_W(0x1C, base)
        );
        fflush(stderr);
    }

    recomp_func_t* asset = aero_lookup_asset(rdram, target32);
    if (asset != NULL) return asset;
    return get_function(target32);
}

#undef LOOKUP_FUNC
#define LOOKUP_FUNC(val) \
    aerostadium2_np3f_lookup_func(rdram, (val), ctx, __func__)
