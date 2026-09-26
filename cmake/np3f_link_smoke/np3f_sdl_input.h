#pragma once

#include <cstdint>

#include "ultramodern/input.hpp"

namespace aerostadium2::input {

bool initialize_controllers();
void shutdown_controllers();

// Called from the Win32/graphics update path. This keeps SDL's device list
// current and handles controllers connected or removed while the game runs.
void pump_controller_events();

// Called by N64ModernRuntime immediately before reading controller data.
void poll_controllers();

bool get_controller_input(
    int controller_num,
    uint16_t* buttons,
    float* x,
    float* y
);

void set_controller_rumble(int controller_num, bool rumble);

ultramodern::input::connected_device_info_t get_connected_controller_info(
    int controller_num
);

} // namespace aerostadium2::input
