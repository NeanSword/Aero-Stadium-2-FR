#include "runtime_host.h"

#include <cassert>
#include <cstdint>
#include <iostream>

namespace {

struct ProbeState {
    std::uint32_t simulation_ticks{};
    std::uint32_t render_frames{};
    double last_alpha{};
};

void simulation_tick(void* user) {
    auto* state = static_cast<ProbeState*>(user);
    ++state->simulation_ticks;
}

void render_frame(void* user, double alpha) {
    auto* state = static_cast<ProbeState*>(user);
    ++state->render_frames;
    state->last_alpha = alpha;
}

} // namespace

int main() {
    ProbeState state{};

    aero::RuntimeHost host{
        aero::RuntimeHooks{
            &state,
            simulation_tick,
            render_frame,
        }
    };

    // Simulate a 120 Hz renderer for eight frames.
    for (int frame = 0; frame < 8; ++frame) {
        host.frame(8'333'333);
    }

    assert(state.simulation_ticks == 3);
    assert(state.render_frames == 8);
    assert(state.last_alpha > 0.99 && state.last_alpha <= 1.0);

    // The render callback is once-per-presentation frame, while simulation
    // callbacks are generated exclusively by the fixed-step clock.
    std::cout << "Aero runtime host probe: OK\n";
    return 0;
}
