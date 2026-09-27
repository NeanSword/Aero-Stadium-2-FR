#include "aero_graphics_settings.h"

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <fstream>
#include <string>
#include <string_view>

namespace aerostadium2::graphics {
namespace {

Settings g_settings{};
std::filesystem::path g_config_root;

std::string trim(std::string value) {
    const auto is_space = [](unsigned char c) { return std::isspace(c) != 0; };
    value.erase(value.begin(), std::find_if(value.begin(), value.end(),
        [&](char c) { return !is_space(static_cast<unsigned char>(c)); }));
    value.erase(std::find_if(value.rbegin(), value.rend(),
        [&](char c) { return !is_space(static_cast<unsigned char>(c)); }).base(), value.end());
    return value;
}

std::string lower(std::string value) {
    std::transform(value.begin(), value.end(), value.begin(),
        [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return value;
}

bool parse_bool(const std::string& value, bool fallback) {
    const std::string v = lower(trim(value));
    if (v == "1" || v == "true" || v == "yes" || v == "on" || v == "oui") {
        return true;
    }
    if (v == "0" || v == "false" || v == "no" || v == "off" || v == "non") {
        return false;
    }
    return fallback;
}

int parse_int(const std::string& value, int fallback) {
    try {
        size_t consumed = 0;
        const int parsed = std::stoi(trim(value), &consumed, 10);
        if (consumed == trim(value).size()) {
            return parsed;
        }
    }
    catch (...) {
    }
    return fallback;
}

void apply_entry(const std::string& raw_key, const std::string& raw_value) {
    const std::string key = lower(trim(raw_key));
    const std::string value = lower(trim(raw_value));

    if (key == "preset") {
        if (value == "original") g_settings.preset = ResolutionPreset::Original;
        else if (value == "1080p") g_settings.preset = ResolutionPreset::HD1080p;
        else if (value == "1440p") g_settings.preset = ResolutionPreset::QHD1440p;
        else if (value == "4k" || value == "2160p") g_settings.preset = ResolutionPreset::UHD4K;
    }
    else if (key == "msaa") {
        const int samples = parse_int(raw_value, g_settings.msaa);
        if (samples == 0 || samples == 2 || samples == 4 || samples == 8) {
            g_settings.msaa = samples;
        }
    }
    else if (key == "upscale_2d") {
        if (value == "original") g_settings.upscale_2d = Upscale2DMode::Original;
        else if (value == "scaled" || value == "scaled_only") g_settings.upscale_2d = Upscale2DMode::ScaledOnly;
        else if (value == "all") g_settings.upscale_2d = Upscale2DMode::All;
    }
    else if (key == "filtering") {
        if (value == "nearest") g_settings.filtering = FilteringMode::Nearest;
        else if (value == "linear") g_settings.filtering = FilteringMode::Linear;
        else if (value == "antialiased" || value == "aa_pixel") g_settings.filtering = FilteringMode::AntiAliasedPixelScaling;
    }
    else if (key == "aspect") {
        if (value == "original" || value == "4:3") g_settings.aspect = AspectMode::Original;
        else if (value == "expand") g_settings.aspect = AspectMode::Expand;
        else if (value == "16:9" || value == "widescreen") g_settings.aspect = AspectMode::Widescreen16x9;
    }
    else if (key == "three_point_filtering") {
        g_settings.three_point_filtering = parse_bool(raw_value, g_settings.three_point_filtering);
    }
    else if (key == "color") {
        if (value == "standard") g_settings.color = ColorMode::Standard;
        else if (value == "high") g_settings.color = ColorMode::High;
        else if (value == "automatic" || value == "auto") g_settings.color = ColorMode::Automatic;
    }
    else if (key == "buffering") {
        if (value == "double") g_settings.buffering = BufferingMode::Double;
        else if (value == "triple") g_settings.buffering = BufferingMode::Triple;
    }
    else if (key == "fullscreen") {
        g_settings.fullscreen = parse_bool(raw_value, g_settings.fullscreen);
    }
    else if (key == "window_width") {
        g_settings.window_width = std::clamp(parse_int(raw_value, g_settings.window_width), 640, 7680);
    }
    else if (key == "window_height") {
        g_settings.window_height = std::clamp(parse_int(raw_value, g_settings.window_height), 480, 4320);
    }
    else if (key == "texture_replacements") {
        g_settings.texture_replacements = parse_bool(raw_value, g_settings.texture_replacements);
    }
    else if (key == "texture_pack") {
        g_settings.texture_pack = std::filesystem::path(trim(raw_value));
    }
}

void write_default_file(const std::filesystem::path& path) {
    std::ofstream out(path, std::ios::out | std::ios::trunc);
    if (!out.is_open()) {
        return;
    }

    out <<
        "# Aero Stadium 2 - reglages graphiques\n"
        "# preset: original | 1080p | 1440p | 4k\n"
        "# 1440p correspond a un rendu interne RT64 6x (240 -> 1440).\n"
        "preset=1440p\n"
        "msaa=4\n"
        "upscale_2d=all\n"
        "filtering=antialiased\n"
        "three_point_filtering=true\n"
        "color=high\n"
        "buffering=triple\n"
        "aspect=original\n"
        "fullscreen=false\n"
        "window_width=1280\n"
        "window_height=960\n"
        "texture_replacements=true\n"
        "texture_pack=textures\n";
}

} // namespace

void initialize(const std::filesystem::path& root) {
    g_config_root = root;
    g_settings = Settings{};

    std::error_code ec;
    std::filesystem::create_directories(g_config_root, ec);

    const std::filesystem::path path = config_file_path();
    if (!std::filesystem::exists(path)) {
        write_default_file(path);
    }

    std::ifstream in(path);
    if (in.is_open()) {
        std::string line;
        while (std::getline(in, line)) {
            line = trim(line);
            if (line.empty() || line[0] == '#' || line[0] == ';') {
                continue;
            }

            const size_t equals = line.find('=');
            if (equals == std::string::npos) {
                continue;
            }

            apply_entry(line.substr(0, equals), line.substr(equals + 1));
        }
    }

    if (g_settings.texture_pack.is_relative()) {
        const std::filesystem::path dir = g_config_root / g_settings.texture_pack;
        std::filesystem::create_directories(dir, ec);
    }

    std::printf(
        "[graphics] config=%ls preset=%s target=%dp scale=%.2fx MSAA=%dx upscale2D=%s textures=%s\n",
        path.c_str(),
        preset_name(),
        target_render_height(),
        resolution_multiplier(),
        g_settings.msaa,
        g_settings.upscale_2d == Upscale2DMode::All ? "all" :
            (g_settings.upscale_2d == Upscale2DMode::ScaledOnly ? "scaled" : "original"),
        g_settings.texture_replacements ? "on" : "off"
    );
}

const Settings& current() {
    return g_settings;
}

const std::filesystem::path& config_root() {
    return g_config_root;
}

std::filesystem::path config_file_path() {
    return g_config_root / L"graphics.ini";
}

std::filesystem::path texture_pack_path() {
    if (g_settings.texture_pack.empty()) {
        return {};
    }
    if (g_settings.texture_pack.is_absolute()) {
        return g_settings.texture_pack;
    }
    return g_config_root / g_settings.texture_pack;
}

double resolution_multiplier() {
    switch (g_settings.preset) {
        case ResolutionPreset::Original: return 1.0;
        case ResolutionPreset::HD1080p: return 4.5;
        case ResolutionPreset::QHD1440p: return 6.0;
        case ResolutionPreset::UHD4K: return 9.0;
    }
    return 6.0;
}

int target_render_height() {
    switch (g_settings.preset) {
        case ResolutionPreset::Original: return 240;
        case ResolutionPreset::HD1080p: return 1080;
        case ResolutionPreset::QHD1440p: return 1440;
        case ResolutionPreset::UHD4K: return 2160;
    }
    return 1440;
}

const char* preset_name() {
    switch (g_settings.preset) {
        case ResolutionPreset::Original: return "original";
        case ResolutionPreset::HD1080p: return "1080p";
        case ResolutionPreset::QHD1440p: return "1440p";
        case ResolutionPreset::UHD4K: return "4k";
    }
    return "1440p";
}

} // namespace aerostadium2::graphics
