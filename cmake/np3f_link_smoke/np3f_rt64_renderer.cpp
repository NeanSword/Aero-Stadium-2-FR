#include "np3f_rt64_renderer.h"

#include <atomic>
#include <cstdint>
#include <cstdio>
#include <memory>

#ifndef HLSL_CPU
#define HLSL_CPU
#endif

#include "hle/rt64_application.h"

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

        app_ = std::make_unique<RT64::Application>(core, app_config);

        // First graphical milestone: preserve the original presentation and
        // remove optional enhancements until Stadium's display lists are
        // validated end-to-end.
        app_->userConfig.graphicsAPI =
            RT64::UserConfiguration::GraphicsAPI::Automatic;
        app_->userConfig.resolution =
            RT64::UserConfiguration::Resolution::WindowIntegerScale;
        app_->userConfig.downsampleMultiplier = 1;
        app_->userConfig.aspectRatio =
            RT64::UserConfiguration::AspectRatio::Original;
        app_->userConfig.antialiasing =
            RT64::UserConfiguration::Antialiasing::None;
        app_->userConfig.refreshRate =
            RT64::UserConfiguration::RefreshRate::Original;
        app_->userConfig.internalColorFormat =
            RT64::UserConfiguration::InternalColorFormat::Automatic;
        app_->userConfig.developerMode = developer_mode;

#if defined(_WIN32)
        const uint32_t setup_thread_id = window_handle.thread_id;
#else
        const uint32_t setup_thread_id = 0;
#endif

        setup_result = map_setup_result(app_->setup(setup_thread_id));
        chosen_api = map_graphics_api(app_->chosenGraphicsAPI);

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

        std::printf(
            "[rt64] Renderer initialise: api=%s, presentation=4:3, AA=off, cadence=originale.\n",
            graphics_api_name(chosen_api)
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
            mark_rt64_display_list_seen();
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
        return 1.0f;
    }

private:
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
