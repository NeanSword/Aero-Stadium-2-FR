#pragma once

#include <memory>

#include "ultramodern/renderer_context.hpp"

namespace aerostadium2 {

std::unique_ptr<ultramodern::renderer::RendererContext> create_rt64_renderer_context(
    uint8_t* rdram,
    ultramodern::renderer::WindowHandle window_handle,
    bool developer_mode
);

// Implemented by np3f_runtime_probe.cpp so the existing watchdog can keep
// reporting whether the native renderer has received a display list.
void mark_rt64_display_list_seen();

} // namespace aerostadium2
