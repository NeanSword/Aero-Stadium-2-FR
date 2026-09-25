#include <cstdint>
#include <cstdio>

#include "recomp.h"
#include "librecomp/addresses.hpp"
#include "librecomp/game.hpp"
#include "librecomp/helpers.hpp"
#include "librecomp/overlays.hpp"
#include <ultramodern/ultra64.h>

namespace {

constexpr s32 kPfsErrNoPack = 1;

constexpr uint32_t k1_to_phys(uint32_t addr) {
    return addr & 0x1FFFFFFFU;
}

void return_no_pack(recomp_context* ctx) {
    _return<s32>(ctx, kPfsErrNoPack);
}


void sync_rom_dma_overlays(uint32_t dev_addr, gpr dram_addr, uint32_t size, uint32_t direction) {
    if (direction != 0 || size == 0) {
        return;
    }

    const uint32_t physical_addr = k1_to_phys(dev_addr);
    if (physical_addr < recomp::rom_base) {
        return;
    }

    const uint32_t rom_offset = physical_addr - recomp::rom_base;
    uint32_t ram_low = static_cast<uint32_t>(dram_addr);
    if (ram_low >= 0xA0000000u && ram_low < 0xA0800000u) {
        ram_low -= 0x20000000u;
    }
    const int32_t ram_addr = static_cast<int32_t>(ram_low);

    std::fprintf(
        stderr,
        "[overlay-dma] ROM 0x%08X -> RAM 0x%08X size=0x%08X\n",
        rom_offset,
        static_cast<uint32_t>(ram_addr),
        size
    );
    std::fflush(stderr);

    // Generic PI DMA is also used for ordinary data transfers. Calling
    // unload_overlays() here is unsafe because a small data DMA can land
    // inside an already-loaded executable section and would look like a
    // partial overlay unload. load_overlays() is range-aware on the ROM side
    // and only registers executable sections actually covered by this DMA.
    load_overlays(rom_offset, ram_addr, size);
}

} // namespace

// N64ModernRuntime already models the high-level Controller Pak API as
// "no accessory present". NP3F's libultra build also references these
// lower-level variants, so preserve the same behavior for the link/runtime
// compatibility layer. Transfer Pak support will replace these stubs later.
extern "C" void __osContRamRead_recomp(uint8_t*, recomp_context* ctx) {
    return_no_pack(ctx);
}

extern "C" void __osContRamWrite_recomp(uint8_t*, recomp_context* ctx) {
    return_no_pack(ctx);
}

extern "C" void __osPfsGetStatus_recomp(uint8_t*, recomp_context* ctx) {
    return_no_pack(ctx);
}

extern "C" void osPfsIsPlug_recomp(uint8_t* rdram, recomp_context* ctx) {
    // libultra reports connected Controller Paks through the output bitmask,
    // while the function itself can still return success when no Pak exists.
    if (ctx->r5 != 0) {
        PTR(u8) pattern = _arg<1, PTR(u8)>(rdram, ctx);
        MEM_B(0, pattern) = 0;
    }
    _return<s32>(ctx, 0);
}

// The debug/exception helper is only used to query the emulated CPU cause
// register. Until exception forwarding is required, report no pending cause.
extern "C" void __osGetCause_recomp(uint8_t*, recomp_context* ctx) {
    _return<u32>(ctx, 0);
}

// NP3F references the non-handle PI PIO wrapper. Mirror the ROM-read path
// already implemented by N64ModernRuntime's osEPiReadIo_recomp.
extern "C" void osPiReadIo_recomp(uint8_t* rdram, recomp_context* ctx) {
    const uint32_t dev_addr = recomp::rom_base | static_cast<uint32_t>(ctx->r4);
    const gpr dram_addr = ctx->r5;
    const uint32_t physical_addr = k1_to_phys(dev_addr);

    if (physical_addr >= recomp::rom_base) {
        recomp::do_rom_pio(rdram, dram_addr, physical_addr);
    }

    _return<s32>(ctx, 0);
}

// NP3F's initialization path references osPiWriteIo. N64ModernRuntime has no
// generic cart PIO-write backend yet. Keep this as an explicit successful
// no-op for the bootstrap; if runtime tracing shows a meaningful device write,
// replace this shim with device-specific behavior rather than silently
// modifying the upstream runtime.
extern "C" void osPiWriteIo_recomp(uint8_t*, recomp_context* ctx) {
    _return<s32>(ctx, 0);
}


// N64ModernRuntime performs ROM PI DMA correctly, but its generic PI path
// does not update the recomp overlay lookup table for code copied after boot.
// Route NP3F's PI DMA calls through these wrappers so dynamically loaded code
// is registered at the RAM address where the game actually placed it.
extern "C" void osPiStartDma_recomp(uint8_t* rdram, recomp_context* ctx);
extern "C" void osEPiStartDma_recomp(uint8_t* rdram, recomp_context* ctx);

extern "C" void aerostadium2_osPiStartDma_recomp(uint8_t* rdram, recomp_context* ctx) {
    const uint32_t direction = static_cast<uint32_t>(ctx->r6);
    const uint32_t dev_addr = static_cast<uint32_t>(ctx->r7) | recomp::rom_base;
    const gpr dram_addr = MEM_W(0x10, ctx->r29);
    const uint32_t size = static_cast<uint32_t>(MEM_W(0x14, ctx->r29));

    // Register executable sections before the runtime sends the DMA-complete
    // message, otherwise a newly awakened thread may resolve a function before
    // the overlay has been added to func_map.
    sync_rom_dma_overlays(dev_addr, dram_addr, size, direction);
    osPiStartDma_recomp(rdram, ctx);
}

extern "C" void aerostadium2_osEPiStartDma_recomp(uint8_t* rdram, recomp_context* ctx) {
    OSPiHandle* handle = TO_PTR(OSPiHandle, ctx->r4);
    OSIoMesg* mb = TO_PTR(OSIoMesg, ctx->r5);

    const uint32_t direction = static_cast<uint32_t>(ctx->r6);
    const uint32_t dev_addr = handle->baseAddress | mb->devAddr;
    const gpr dram_addr = mb->dramAddr;
    const uint32_t size = mb->size;

    // Same ordering guarantee as the non-handle PI path.
    sync_rom_dma_overlays(dev_addr, dram_addr, size, direction);
    osEPiStartDma_recomp(rdram, ctx);
}
