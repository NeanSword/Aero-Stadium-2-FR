#include "np3f_rt64_renderer.h"
#include "aero_graphics_settings.h"

#include <atomic>
#include <cstdint>
#include <cstdio>
#include <memory>
#include <filesystem>

#if defined(_WIN32)
#include <Windows.h>
#include <objbase.h>
#include <oleauto.h>
#endif

#ifndef HLSL_CPU
#define HLSL_CPU
#endif

#include "hle/rt64_application.h"
#include "hle/rt64_state.h"
#include "render/rt64_texture_cache.h"

#include "ultramodern/config.hpp"
#include "ultramodern/ultramodern.hpp"

namespace aerostadium2 {
namespace {

constexpr uint32_t physical_address(uint32_t address) {
    return address & 0x03FFFFFFu;
}

void no_interrupts() {}

ultramodern::renderer::SetupResult map_setup_result(
    RT64::Application::SetupResult result
) {
    using From = RT64::Application::SetupResult;
    using To = ultramodern::renderer::SetupResult;

    switch (result) {
        case From::Success:                  return To::Success;
        case From::DynamicLibrariesNotFound: return To::DynamicLibrariesNotFound;
        case From::InvalidGraphicsAPI:       return To::InvalidGraphicsAPI;
        case From::GraphicsAPINotFound:      return To::GraphicsAPINotFound;
        case From::GraphicsDeviceNotFound:   return To::GraphicsDeviceNotFound;
    }

    return To::GraphicsDeviceNotFound;
}

ultramodern::renderer::GraphicsApi map_graphics_api(
    RT64::UserConfiguration::GraphicsAPI api
) {
    using From = RT64::UserConfiguration::GraphicsAPI;
    using To = ultramodern::renderer::GraphicsApi;

    switch (api) {
        case From::D3D12: return To::D3D12;
        case From::Vulkan: return To::Vulkan;
        case From::Metal: return To::Metal;
        case From::Automatic: return To::Auto;
    }

    return To::Auto;
}

const char* graphics_api_name(ultramodern::renderer::GraphicsApi api) {
    using Api = ultramodern::renderer::GraphicsApi;

    switch (api) {
        case Api::D3D12: return "D3D12";
        case Api::Vulkan: return "Vulkan";
        case Api::Metal: return "Metal";
        default: return "Auto";
    }
}

class AeroRt64Context final : public ultramodern::renderer::RendererContext {
public:
    AeroRt64Context(
        uint8_t* rdram,
        ultramodern::renderer::WindowHandle window_handle,
        bool developer_mode
    ) {
        RT64::Application::Core core{};

#if defined(_WIN32)
        core.window = window_handle.window;
#else
        core.window = window_handle;
#endif
        core.checkInterrupts = no_interrupts;

        core.HEADER = registers_.header;
        core.RDRAM = rdram;
        core.DMEM = registers_.dmem;
        core.IMEM = registers_.imem;

        core.MI_INTR_REG = &registers_.mi_intr;

        core.DPC_START_REG = &registers_.dpc[0];
        core.DPC_END_REG = &registers_.dpc[1];
        core.DPC_CURRENT_REG = &registers_.dpc[2];
        core.DPC_STATUS_REG = &registers_.dpc[3];
        core.DPC_CLOCK_REG = &registers_.dpc[4];
        core.DPC_BUFBUSY_REG = &registers_.dpc[5];
        core.DPC_PIPEBUSY_REG = &registers_.dpc[6];
        core.DPC_TMEM_REG = &registers_.dpc[7];

        ultramodern::renderer::ViRegs* vi = ultramodern::renderer::get_vi_regs();
        core.VI_STATUS_REG = &vi->VI_STATUS_REG;
        core.VI_ORIGIN_REG = &vi->VI_ORIGIN_REG;
        core.VI_WIDTH_REG = &vi->VI_WIDTH_REG;
        core.VI_INTR_REG = &vi->VI_INTR_REG;
        core.VI_V_CURRENT_LINE_REG = &vi->VI_V_CURRENT_LINE_REG;
        core.VI_TIMING_REG = &vi->VI_TIMING_REG;
        core.VI_V_SYNC_REG = &vi->VI_V_SYNC_REG;
        core.VI_H_SYNC_REG = &vi->VI_H_SYNC_REG;
        core.VI_LEAP_REG = &vi->VI_LEAP_REG;
        core.VI_H_START_REG = &vi->VI_H_START_REG;
        core.VI_V_START_REG = &vi->VI_V_START_REG;
        core.VI_V_BURST_REG = &vi->VI_V_BURST_REG;
        core.VI_X_SCALE_REG = &vi->VI_X_SCALE_REG;
        core.VI_Y_SCALE_REG = &vi->VI_Y_SCALE_REG;

        RT64::ApplicationConfiguration app_config{};
        app_config.appId = "aerostadium2";
        app_config.useConfigurationFile = false;
        app_config.detectDataPath = false;

        app_ = std::make_unique<RT64::Application>(core, app_config);

        const auto& gfx = graphics::current();

        app_->userConfig.graphicsAPI =
            RT64::UserConfiguration::GraphicsAPI::Automatic;
        app_->userConfig.resolution =
            (gfx.preset == graphics::ResolutionPreset::Original)
                ? RT64::UserConfiguration::Resolution::Original
                : RT64::UserConfiguration::Resolution::Manual;
        app_->userConfig.resolutionMultiplier = graphics::resolution_multiplier();
        app_->userConfig.downsampleMultiplier = 1;

        switch (gfx.msaa) {
            case 8:
                app_->userConfig.antialiasing = RT64::UserConfiguration::Antialiasing::MSAA8X;
                break;
            case 4:
                app_->userConfig.antialiasing = RT64::UserConfiguration::Antialiasing::MSAA4X;
                break;
            case 2:
                app_->userConfig.antialiasing = RT64::UserConfiguration::Antialiasing::MSAA2X;
                break;
            default:
                app_->userConfig.antialiasing = RT64::UserConfiguration::Antialiasing::None;
                break;
        }

        switch (gfx.filtering) {
            case graphics::FilteringMode::Nearest:
                app_->userConfig.filtering = RT64::UserConfiguration::Filtering::Nearest;
                break;
            case graphics::FilteringMode::Linear:
                app_->userConfig.filtering = RT64::UserConfiguration::Filtering::Linear;
                break;
            case graphics::FilteringMode::AntiAliasedPixelScaling:
            default:
                app_->userConfig.filtering = RT64::UserConfiguration::Filtering::AntiAliasedPixelScaling;
                break;
        }

        switch (gfx.upscale_2d) {
            case graphics::Upscale2DMode::Original:
                app_->userConfig.upscale2D = RT64::UserConfiguration::Upscale2D::Original;
                break;
            case graphics::Upscale2DMode::ScaledOnly:
                app_->userConfig.upscale2D = RT64::UserConfiguration::Upscale2D::ScaledOnly;
                break;
            case graphics::Upscale2DMode::All:
            default:
                app_->userConfig.upscale2D = RT64::UserConfiguration::Upscale2D::All;
                break;
        }

        app_->userConfig.threePointFiltering = gfx.three_point_filtering;

        switch (gfx.aspect) {
            case graphics::AspectMode::Expand:
                app_->userConfig.aspectRatio = RT64::UserConfiguration::AspectRatio::Expand;
                break;
            case graphics::AspectMode::Widescreen16x9:
                app_->userConfig.aspectRatio = RT64::UserConfiguration::AspectRatio::Manual;
                app_->userConfig.aspectTarget = 16.0 / 9.0;
                break;
            case graphics::AspectMode::Original:
            default:
                app_->userConfig.aspectRatio = RT64::UserConfiguration::AspectRatio::Original;
                break;
        }
        app_->userConfig.extAspectRatio = RT64::UserConfiguration::AspectRatio::Original;

        app_->userConfig.displayBuffering =
            (gfx.buffering == graphics::BufferingMode::Triple)
                ? RT64::UserConfiguration::DisplayBuffering::Triple
                : RT64::UserConfiguration::DisplayBuffering::Double;

        switch (gfx.color) {
            case graphics::ColorMode::Standard:
                app_->userConfig.internalColorFormat = RT64::UserConfiguration::InternalColorFormat::Standard;
                break;
            case graphics::ColorMode::Automatic:
                app_->userConfig.internalColorFormat = RT64::UserConfiguration::InternalColorFormat::Automatic;
                break;
            case graphics::ColorMode::High:
            default:
                app_->userConfig.internalColorFormat = RT64::UserConfiguration::InternalColorFormat::High;
                break;
        }

        app_->userConfig.refreshRate =
            RT64::UserConfiguration::RefreshRate::Original;
        app_->userConfig.hardwareResolve =
            RT64::UserConfiguration::HardwareResolve::Automatic;
        app_->userConfig.developerMode = developer_mode;

#if defined(_WIN32)
        const uint32_t setup_thread_id = window_handle.thread_id;
#else
        const uint32_t setup_thread_id = 0;
#endif

        setup_result = map_setup_result(app_->setup(setup_thread_id));
        chosen_api = map_graphics_api(app_->chosenGraphicsAPI);

        if (setup_result == ultramodern::renderer::SetupResult::Success) {
            const auto& gfx = graphics::current();
            const std::filesystem::path pack = graphics::texture_pack_path();
            const bool pack_is_file = !pack.empty() && std::filesystem::is_regular_file(pack);
            const bool pack_is_directory =
                !pack.empty() &&
                std::filesystem::is_directory(pack) &&
                std::filesystem::is_regular_file(pack / L"rt64.json");

            if (gfx.texture_replacements && (pack_is_file || pack_is_directory) && app_->textureCache != nullptr) {
                const bool loaded = app_->textureCache->loadReplacementDirectory(
                    RT64::ReplacementDirectory(pack)
                );
                app_->textureCache->textureMap.replacementMapEnabled = loaded;
                std::printf(
                    "[rt64] Texture pack HD: %s (%ls)\n",
                    loaded ? "charge" : "echec",
                    pack.c_str()
                );
            }

            if (gfx.dump_textures && app_->state != nullptr) {
                const std::filesystem::path dump_dir = graphics::texture_dump_path();
                std::error_code ec;
                std::filesystem::create_directories(dump_dir, ec);
                if (!ec) {
                    app_->state->dumpingTexturesDirectory = dump_dir;
                    std::printf("[rt64] Dump textures actif: %ls\n", dump_dir.c_str());
                }
                else {
                    std::fprintf(
                        stderr,
                        "[rt64] Impossible de creer le dossier de dump textures: %ls\n",
                        dump_dir.c_str()
                    );
                }
            }
        }

        if (setup_result != ultramodern::renderer::SetupResult::Success) {
            std::fprintf(
                stderr,
                "[rt64] Echec initialisation: result=%d api=%s\n",
                static_cast<int>(setup_result),
                graphics_api_name(chosen_api)
            );
            std::fflush(stderr);
            app_.reset();
            return;
        }

        const auto& gfx = graphics::current();
        const char* aspect_name =
            gfx.aspect == graphics::AspectMode::Original ? "4:3" :
            (gfx.aspect == graphics::AspectMode::Expand ? "expand" : "16:9");
        std::printf(
            "[rt64] Renderer initialise: api=%s, preset=%s, scale=%.2fx, MSAA=%dx, "
            "2D=%s, aspect=%s, cadence=originale.\n",
            graphics_api_name(chosen_api),
            graphics::preset_name(),
            graphics::resolution_multiplier(),
            gfx.msaa,
            gfx.upscale_2d == graphics::Upscale2DMode::All ? "all" :
                (gfx.upscale_2d == graphics::Upscale2DMode::ScaledOnly ? "scaled" : "original"),
            aspect_name
        );
        std::fflush(stdout);
    }

    ~AeroRt64Context() override = default;

    bool valid() override {
        return app_ != nullptr;
    }

    bool update_config(
        const ultramodern::renderer::GraphicsConfig&,
        const ultramodern::renderer::GraphicsConfig&
    ) override {
        // Runtime graphics menus come later. Keep the first RT64 milestone
        // deterministic while the game's display lists are being validated.
        return false;
    }

    void enable_instant_present() override {
        // Deliberately disabled for the first rendering milestone.
    }

    void send_dl(const OSTask* task) override {
        if (app_ == nullptr || task == nullptr) {
            return;
        }

        static std::atomic_bool first_display_list{true};
        if (first_display_list.exchange(false)) {
            std::printf(
                "[rt64] Premiere display list NP3F: ucode=0x%08X ucode_data=0x%08X data=0x%08X size=0x%08X\n",
                task->t.ucode,
                task->t.ucode_data,
                task->t.data_ptr,
                task->t.data_size
            );
            std::fflush(stdout);
        }

        app_->state->rsp->reset();
        app_->interpreter->loadUCodeGBI(
            physical_address(task->t.ucode),
            physical_address(task->t.ucode_data),
            true
        );
        app_->processDisplayLists(
            app_->core.RDRAM,
            physical_address(task->t.data_ptr),
            0,
            true
        );
        mark_rt64_display_list_seen();
        if (++completed_lists_ == 1) {
            std::fprintf(stderr, "[rt64] First display list completed.\n");
        }
    }

    void send_dummy_workload(uint32_t) override {}

    void update_screen() override {
        if (app_ == nullptr) {
            return;
        }

        static std::atomic_bool first_screen{true};
        if (first_screen.exchange(false)) {
            ultramodern::renderer::ViRegs* vi =
                ultramodern::renderer::get_vi_regs();
            std::printf(
                "[rt64] Premier scanout: VI_ORIGIN=0x%08X VI_WIDTH=%u VI_STATUS=0x%08X\n",
                vi->VI_ORIGIN_REG,
                vi->VI_WIDTH_REG,
                vi->VI_STATUS_REG
            );
            std::fflush(stdout);
        }

        app_->updateScreen();
        if (++screen_updates_ % 300 == 0) {
            auto* vi = ultramodern::renderer::get_vi_regs();
            std::fprintf(stderr,
                "[rt64-progress] screens=%u lists=%u VI_ORIGIN=%08X VI_WIDTH=%u VI_STATUS=%08X X_SCALE=%08X Y_SCALE=%08X H_START=%08X V_START=%08X\n",
                screen_updates_, completed_lists_, vi->VI_ORIGIN_REG,
                vi->VI_WIDTH_REG, vi->VI_STATUS_REG, vi->VI_X_SCALE_REG,
                vi->VI_Y_SCALE_REG, vi->VI_H_START_REG, vi->VI_V_START_REG);
        }
    }

    void shutdown() override {
        if (app_ != nullptr) {
            std::printf("[rt64] Arret du renderer.\n");
            std::fflush(stdout);
            app_->end();
        }
    }

    uint32_t get_display_framerate() const override {
        // The first milestone keeps original PAL timing. A later graphics
        // settings layer will expose the actual swap-chain rate.
        return 50;
    }

    float get_resolution_scale() const override {
        return static_cast<float>(graphics::resolution_multiplier());
    }

private:
    uint32_t completed_lists_ = 0;
    uint32_t screen_updates_ = 0;
    struct {
        uint8_t header[0x40]{};
        uint8_t dmem[0x1000]{};
        uint8_t imem[0x1000]{};
        uint32_t mi_intr = 0;
        uint32_t dpc[8]{};
    } registers_;

    std::unique_ptr<RT64::Application> app_;
};

} // namespace

std::unique_ptr<ultramodern::renderer::RendererContext> create_rt64_renderer_context(
    uint8_t* rdram,
    ultramodern::renderer::WindowHandle window_handle,
    bool developer_mode
) {
    return std::make_unique<AeroRt64Context>(
        rdram,
        window_handle,
        developer_mode
    );
}

} // namespace aerostadium2
