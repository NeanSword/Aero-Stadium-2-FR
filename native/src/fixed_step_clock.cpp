#include "fixed_step_clock.h"

#include <algorithm>
#include <limits>
#include <stdexcept>

namespace aero {

FixedStepClock::FixedStepClock(std::uint32_t tick_rate_hz,
                               std::uint32_t max_ticks_per_render)
    : tick_rate_hz_(tick_rate_hz),
      max_ticks_per_render_(max_ticks_per_render) {
    if (tick_rate_hz_ == 0) {
        throw std::invalid_argument("tick_rate_hz must be non-zero");
    }
    if (max_ticks_per_render_ == 0) {
        throw std::invalid_argument("max_ticks_per_render must be non-zero");
    }
}

FixedStepClock::StepResult FixedStepClock::advance(
    std::int64_t elapsed_nanoseconds) {
    if (elapsed_nanoseconds <= 0) {
        return {};
    }

    constexpr std::uint64_t kNanosecondsPerSecond = 1'000'000'000ULL;

    const auto elapsed = static_cast<std::uint64_t>(elapsed_nanoseconds);

    // Store time as rational units:
    // accumulator = elapsed_nanoseconds * tick_rate_hz
    // One complete simulation tick consumes exactly one second worth
    // of these units, avoiding a rounded 16.666... ms tick duration.
    const std::uint64_t max_add =
        (std::numeric_limits<std::uint64_t>::max() -
         accumulator_units_) /
        tick_rate_hz_;

    accumulator_units_ +=
        std::min(elapsed, max_add) * static_cast<std::uint64_t>(tick_rate_hz_);

    std::uint32_t ticks = 0;
    while (ticks < max_ticks_per_render_ &&
           accumulator_units_ >= kNanosecondsPerSecond) {
        accumulator_units_ -= kNanosecondsPerSecond;
        ++ticks;
    }

    const double alpha =
        static_cast<double>(accumulator_units_) /
        static_cast<double>(kNanosecondsPerSecond);

    return StepResult{ticks, alpha};
}

} // namespace aero
