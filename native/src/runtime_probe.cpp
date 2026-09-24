#include "fixed_step_clock.h"

#include <cassert>
#include <iostream>

int main() {
    aero::FixedStepClock clock{60, 8};

    // 120 Hz presentation: each render advances half a simulation tick.
    auto first = clock.advance(8'333'333);
    assert(first.ticks_run == 0);
    assert(first.alpha > 0.49 && first.alpha < 0.51);

    auto second = clock.advance(8'333'334);
    assert(second.ticks_run == 1);
    assert(second.alpha >= 0.0 && second.alpha < 0.01);

    // 240 Hz presentation must not make simulation run 4x faster.
    clock.reset();

    std::uint32_t ticks = 0;
    for (int frame = 0; frame < 4; ++frame) {
        ticks += clock.advance(4'166'667).ticks_run;
    }
    assert(ticks == 1);

    // A long stall is bounded so the simulation cannot consume an
    // unbounded number of ticks in one render callback.
    clock.reset();
    auto stalled = clock.advance(1'000'000'000);
    assert(stalled.ticks_run == 8);

    std::cout << "Aero fixed-step runtime probe: OK\n";
    return 0;
}
