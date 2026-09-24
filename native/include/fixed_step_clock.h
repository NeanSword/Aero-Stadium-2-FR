#pragma once

#include <cstdint>

namespace aero {

class FixedStepClock {
public:
    struct StepResult {
        std::uint32_t ticks_run{};
        double alpha{};
    };

    explicit FixedStepClock(std::uint32_t tick_rate_hz = 60,
                            std::uint32_t max_ticks_per_render = 8);

    StepResult advance(std::int64_t elapsed_nanoseconds);

    [[nodiscard]] std::uint32_t tick_rate_hz() const noexcept {
        return tick_rate_hz_;
    }

    [[nodiscard]] std::uint64_t accumulator_units() const noexcept {
        return accumulator_units_;
    }

    void reset() noexcept {
        accumulator_units_ = 0;
    }

private:
    std::uint32_t tick_rate_hz_;
    std::uint32_t max_ticks_per_render_;
    std::uint64_t accumulator_units_{};
};

} // namespace aero
