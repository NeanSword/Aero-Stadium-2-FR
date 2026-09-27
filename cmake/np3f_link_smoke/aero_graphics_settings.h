#pragma once

#include <filesystem>

namespace aerostadium2::graphics {

enum class ResolutionPreset {
    Original,
    HD1080p,
    QHD1440p,
    UHD4K,
};

enum class Upscale2DMode {
    Original,
    ScaledOnly,
    All,
};

enum class FilteringMode {
    Nearest,
    Linear,
    AntiAliasedPixelScaling,
};

enum class AspectMode {
    Original,
    Expand,
    Widescreen16x9,
};

enum class ColorMode {
    Standard,
    High,
    Automatic,
};

enum class BufferingMode {
    Double,
    Triple,
};

struct Settings {
    ResolutionPreset preset = ResolutionPreset::QHD1440p;
    int msaa = 4;
    Upscale2DMode upscale_2d = Upscale2DMode::All;
    FilteringMode filtering = FilteringMode::AntiAliasedPixelScaling;
    AspectMode aspect = AspectMode::Original;
    bool three_point_filtering = true;
    ColorMode color = ColorMode::High;
    BufferingMode buffering = BufferingMode::Triple;
    bool fullscreen = false;
    int window_width = 1280;
    int window_height = 960;
    bool texture_replacements = true;
    std::filesystem::path texture_pack = L"textures";
};

void initialize(const std::filesystem::path& config_root);
const Settings& current();
const std::filesystem::path& config_root();
std::filesystem::path config_file_path();
std::filesystem::path texture_pack_path();
double resolution_multiplier();
int target_render_height();
const char* preset_name();

} // namespace aerostadium2::graphics
