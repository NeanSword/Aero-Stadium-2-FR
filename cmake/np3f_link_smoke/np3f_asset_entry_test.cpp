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
    std::puts("Asset accessor: branch, signed address, stack effect and rejection checks passed.");
}
