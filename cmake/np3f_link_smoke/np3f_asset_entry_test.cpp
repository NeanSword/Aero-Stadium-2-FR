#include "recomp.h"
#include <cstdio>
#include <cstring>
#include <vector>

extern "C" recomp_func_t* aero_lookup_asset(uint8_t*, int32_t);
#define CHECK(x) do { if (!(x)) { std::fprintf(stderr, "Failed: %s\n", #x); return 1; } } while (0)

int main() {
    std::vector<uint8_t> ram(8 * 1024 * 1024);
    auto put = [&](uint32_t offset, uint32_t value) { std::memcpy(ram.data() + offset, &value, 4); };
    put(0x108, 0x46524147); put(0x10C, 0x4D454E54); put(0x11C, 0x9000);
    const uint32_t instructions[] = {0xAFA50004, 0x14800003, 0x00001825,
        0x3C038001, 0x24638004, 0x03E00008, 0x00601025};
    for (unsigned i = 0; i < 7; ++i) put(0x120 + i * 4, instructions[i]);
    auto function = aero_lookup_asset(ram.data(), static_cast<int32_t>(0x80000120));
    CHECK(function != nullptr);
    recomp_context ctx{};
    ctx.r29 = static_cast<int32_t>(0x807FFF00); ctx.r5 = 0x12345678;
    function(ram.data(), &ctx);
    CHECK(ctx.r2 == static_cast<int64_t>(static_cast<int32_t>(0x80008004)));
    CHECK(ctx.r3 == ctx.r2);
    uint32_t saved; std::memcpy(&saved, ram.data() + 0x7FFF04, 4);
    CHECK(saved == 0x12345678);
    ctx.r4 = 1; function(ram.data(), &ctx);
    CHECK(ctx.r2 == 0 && ctx.r3 == 0 && ctx.r5 == 0x12345678);
    put(0x124, 0x10800003); // A changed branch must not use this translation.
    CHECK(aero_lookup_asset(ram.data(), static_cast<int32_t>(0x80000120)) == nullptr);
    put(0x124, instructions[1]); put(0x12C, 0x3C038080);
    CHECK(aero_lookup_asset(ram.data(), static_cast<int32_t>(0x80000120)) == nullptr);
    CHECK(aero_lookup_asset(ram.data(), static_cast<int32_t>(0xA4500000)) == nullptr);
    const uint32_t typed_instructions[] = {0x10800006, 0xAFA50004, 0x24010001,
        0x10810006, 0x24030001, 0x03E00008, 0x00001025, 0x3C038001,
        0x03E00008, 0x24628004, 0x03E00008, 0x00601025};
    for (unsigned i = 0; i < 12; ++i) put(0x120 + i * 4, typed_instructions[i]);
    function = aero_lookup_asset(ram.data(), static_cast<int32_t>(0x80000120));
    CHECK(function != nullptr);
    ctx.r4 = 0; ctx.r1 = 42; ctx.r5 = 123;
    function(ram.data(), &ctx);
    CHECK(ctx.r2 == static_cast<int32_t>(0x80008004));
    CHECK(ctx.r3 == static_cast<int32_t>(0x80010000) && ctx.r1 == 42);
    std::memcpy(&saved, ram.data() + 0x7FFF04, 4); CHECK(saved == 123);
    ctx.r4 = 1; function(ram.data(), &ctx);
    CHECK(ctx.r2 == 1 && ctx.r3 == 1 && ctx.r1 == 1);
    ctx.r4 = -1; function(ram.data(), &ctx);
    CHECK(ctx.r2 == 0 && ctx.r3 == 1 && ctx.r1 == 1);
    put(0x144, 0x24628100); put(0x11C, 0x8000);
    CHECK(aero_lookup_asset(ram.data(), static_cast<int32_t>(0x80000120)) == nullptr);
    put(0x11C, 0x9000); put(0x130, 0x24030002);
    CHECK(aero_lookup_asset(ram.data(), static_cast<int32_t>(0x80000120)) == nullptr);
    std::puts("Asset accessor: branch, signed address, stack effect and rejection checks passed.");
}
