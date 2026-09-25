#include <atomic>
#include <cstdio>
#include <memory>
#include <string>

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#include "librecomp/game.hpp"
#include "librecomp/rsp.hpp"
#include "ultramodern/ultramodern.hpp"

namespace {

std::atomic_bool g_logged_display_list = false;
std::atomic_bool g_logged_rsp_task = false;

LRESULT CALLBACK probe_window_proc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    switch (msg) {
        case WM_CLOSE:
            DestroyWindow(hwnd);
            return 0;
        case WM_DESTROY:
            PostQuitMessage(0);
            return 0;
        default:
            return DefWindowProcW(hwnd, msg, wparam, lparam);
    }
}

void* create_gfx() {
    return nullptr;
}

ultramodern::renderer::WindowHandle create_window(void*) {
    constexpr wchar_t kClassName[] = L"AeroStadium2RuntimeProbeWindow";

    WNDCLASSEXW wc{};
    wc.cbSize = sizeof(wc);
    wc.style = CS_HREDRAW | CS_VREDRAW | CS_OWNDC;
    wc.lpfnWndProc = probe_window_proc;
    wc.hInstance = GetModuleHandleW(nullptr);
    wc.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    wc.lpszClassName = kClassName;

    RegisterClassExW(&wc);

    HWND hwnd = CreateWindowExW(
        0,
        kClassName,
        L"Aero Stadium 2 - Runtime NP3F",
        WS_OVERLAPPEDWINDOW,
        CW_USEDEFAULT,
        CW_USEDEFAULT,
        960,
        720,
        nullptr,
        nullptr,
        wc.hInstance,
        nullptr
    );

    if (hwnd == nullptr) {
        std::fprintf(stderr, "[runtime-probe] CreateWindowExW a echoue (%lu)\n", GetLastError());
        return {};
    }

    ShowWindow(hwnd, SW_SHOW);
    UpdateWindow(hwnd);

    std::printf("[runtime-probe] Fenetre Win32 creee.\n");
    return ultramodern::renderer::WindowHandle{ hwnd, GetCurrentThreadId() };
}

void update_gfx(void*) {
    MSG msg{};
    while (PeekMessageW(&msg, nullptr, 0, 0, PM_REMOVE)) {
        if (msg.message == WM_QUIT) {
            std::printf("[runtime-probe] Fermeture demandee.\n");
            ultramodern::quit();
            return;
        }
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }
}

class ProbeRendererContext final : public ultramodern::renderer::RendererContext {
public:
    ProbeRendererContext() {
        setup_result = ultramodern::renderer::SetupResult::Success;
        chosen_api = ultramodern::renderer::GraphicsApi::Auto;
    }

    bool valid() override {
        return true;
    }

    bool update_config(
        const ultramodern::renderer::GraphicsConfig&,
        const ultramodern::renderer::GraphicsConfig&
    ) override {
        return true;
    }

    void enable_instant_present() override {}

    void send_dl(const OSTask*) override {
        if (!g_logged_display_list.exchange(true)) {
            std::printf("[runtime-probe] Premiere display list recue par le renderer factice.\n");
        }
    }

    void send_dummy_workload(uint32_t) override {}
    void update_screen() override {}
    void shutdown() override {}

    uint32_t get_display_framerate() const override {
        return 60;
    }

    float get_resolution_scale() const override {
        return 1.0f;
    }
};

std::unique_ptr<ultramodern::renderer::RendererContext> create_render_context(
    uint8_t*,
    ultramodern::renderer::WindowHandle,
    bool
) {
    std::printf("[runtime-probe] Renderer factice initialise.\n");
    return std::make_unique<ProbeRendererContext>();
}

RspExitReason probe_rsp_ucode(uint8_t*, uint32_t) {
    return RspExitReason::Broke;
}

RspUcodeFunc* get_rsp_microcode(const OSTask* task) {
    if (!g_logged_rsp_task.exchange(true)) {
        std::printf(
            "[runtime-probe] Premiere tache RSP recue: type=%u ucode=0x%08X data=0x%08X\n",
            task->t.type,
            task->t.ucode,
            task->t.ucode_data
        );
        std::printf("[runtime-probe] RSP temporairement acquitte en mode diagnostic.\n");
    }
    return probe_rsp_ucode;
}

void queue_samples(int16_t*, size_t) {}

size_t get_frames_remaining() {
    return 0;
}

void set_frequency(uint32_t frequency) {
    static std::atomic_bool logged = false;
    if (!logged.exchange(true)) {
        std::printf("[runtime-probe] Frequence audio demandee: %u Hz\n", frequency);
    }
}

void poll_input() {}

bool get_input(int, uint16_t* buttons, float* x, float* y) {
    if (buttons != nullptr) {
        *buttons = 0;
    }
    if (x != nullptr) {
        *x = 0.0f;
    }
    if (y != nullptr) {
        *y = 0.0f;
    }
    return true;
}

void set_rumble(int, bool) {}

ultramodern::input::connected_device_info_t get_connected_device_info(int controller_num) {
    if (controller_num == 0) {
        return {
            .connected_device = ultramodern::input::Device::Controller,
            .connected_pak = ultramodern::input::Pak::None,
        };
    }

    return {
        .connected_device = ultramodern::input::Device::None,
        .connected_pak = ultramodern::input::Pak::None,
    };
}

void runtime_message_box(const char* msg) {
    MessageBoxA(
        nullptr,
        msg,
        "Aero Stadium 2 - N64ModernRuntime",
        MB_OK | MB_ICONERROR
    );
}

} // namespace

namespace aerostadium2 {

void run_np3f_runtime_probe(const std::u8string& game_id) {
    const recomp::rsp::callbacks_t rsp_callbacks{
        .get_rsp_microcode = get_rsp_microcode,
    };

    const ultramodern::renderer::callbacks_t renderer_callbacks{
        .create_render_context = create_render_context,
        .get_graphics_api_name = nullptr,
    };

    const ultramodern::audio_callbacks_t audio_callbacks{
        .queue_samples = queue_samples,
        .get_frames_remaining = get_frames_remaining,
        .set_frequency = set_frequency,
    };

    const ultramodern::input::callbacks_t input_callbacks{
        .poll_input = poll_input,
        .get_input = get_input,
        .set_rumble = set_rumble,
        .get_connected_device_info = get_connected_device_info,
    };

    const ultramodern::gfx_callbacks_t gfx_callbacks{
        .create_gfx = create_gfx,
        .create_window = create_window,
        .update_gfx = update_gfx,
    };

    const ultramodern::error_handling::callbacks_t error_callbacks{
        .message_box = runtime_message_box,
    };

    recomp::Configuration cfg{};
    cfg.project_version = recomp::Version{ 0, 1, 0, "-runtime-probe" };
    cfg.rsp_callbacks = rsp_callbacks;
    cfg.renderer_callbacks = renderer_callbacks;
    cfg.audio_callbacks = audio_callbacks;
    cfg.input_callbacks = input_callbacks;
    cfg.gfx_callbacks = gfx_callbacks;
    cfg.error_handling_callbacks = error_callbacks;

    std::printf("[runtime-probe] Demarrage du CPU recompile NP3F...\n");
    recomp::start_game(game_id, "");
    recomp::start(cfg);
    std::printf("[runtime-probe] N64ModernRuntime termine.\n");
}

} // namespace aerostadium2
