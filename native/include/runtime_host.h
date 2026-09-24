#pragma once

#include "fixed_step_clock.h"

#include <cstdint>

namespace aero {

using SimulationTickFn = void (*)(void* user);
using RenderFrameFn = void (*)(void* user, double alpha);

struct RuntimeHooks {
    void* user{};
    SimulationTickFn simulation_tick{};
    RenderFrameFn render_frame{};
};

class RuntimeHost {
public:
    explicit RuntimeHost(RuntimeHooks hooks = {});

    FixedStepClock::StepResult frame(std::int64_t elapsed_nanoseconds);

    [[nodiscard]] const FixedStepClock& clock() const noexcept {
        return clock_;
    }

private:
    FixedStepClock clock_;
    RuntimeHooks hooks_;
};

} // namespace aero
