#include "runtime_host.h"

namespace aero {

RuntimeHost::RuntimeHost(RuntimeHooks hooks)
    : hooks_(hooks) {}

FixedStepClock::StepResult RuntimeHost::frame(
    std::int64_t elapsed_nanoseconds) {
    const auto result = clock_.advance(elapsed_nanoseconds);

    if (hooks_.simulation_tick != nullptr) {
        for (std::uint32_t tick = 0; tick < result.ticks_run; ++tick) {
            hooks_.simulation_tick(hooks_.user);
        }
    }

    if (hooks_.render_frame != nullptr) {
        hooks_.render_frame(hooks_.user, result.alpha);
    }

    return result;
}

} // namespace aero
