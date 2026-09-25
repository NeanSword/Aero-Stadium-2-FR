#include <atomic>
#include <cstdio>
#include <memory>
#include <string>
#include <thread>
#include <chrono>
#include <cstring>
#include <array>

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#include "recomp.h"
#include "librecomp/game.hpp"
#include "librecomp/rsp.hpp"
#include "ultramodern/ultramodern.hpp"

extern "C" void recomp_entrypoint(uint8_t* rdram, recomp_context* ctx);

namespace {

std::atomic_bool g_logged_display_list = false;
std::atomic_bool g_logged_rsp_task = false;
std::atomic_uint32_t g_created_thread_count = 0;
std::atomic_bool g_entrypoint_started = false;
std::atomic_bool g_entrypoint_returned = false;
std::atomic<uint8_t*> g_rdram = nullptr;

LONG WINAPI probe_unhandled_exception_filter(EXCEPTION_POINTERS* info) {
    if (info == nullptr || info->ExceptionRecord == nullptr) {
        return EXCEPTION_CONTINUE_SEARCH;
    }

    const EXCEPTION_RECORD* record = info->ExceptionRecord;
    const uintptr_t module_base = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
    const uintptr_t exception_address = reinterpret_cast<uintptr_t>(record->ExceptionAddress);
    const uintptr_t exception_rva =
        exception_address >= module_base ? exception_address - module_base : 0;

    std::fprintf(
        stderr,
        "[win-crash] code=0x%08lX address=%p module_base=%p rva=0x%llX\n",
        record->ExceptionCode,
        record->ExceptionAddress,
        reinterpret_cast<void*>(module_base),
        static_cast<unsigned long long>(exception_rva)
    );

    if (record->ExceptionCode == EXCEPTION_ACCESS_VIOLATION &&
        record->NumberParameters >= 2) {
        const char* operation = "inconnue";
        switch (record->ExceptionInformation[0]) {
            case 0: operation = "lecture"; break;
            case 1: operation = "ecriture"; break;
            case 8: operation = "execution"; break;
            default: break;
        }

        const uintptr_t target = static_cast<uintptr_t>(record->ExceptionInformation[1]);
        const uintptr_t rdram_base = reinterpret_cast<uintptr_t>(g_rdram.load());

        std::fprintf(
            stderr,
            "[win-crash] access_violation operation=%s target=0x%llX rdram_base=0x%llX\n",
            operation,
            static_cast<unsigned long long>(target),
            static_cast<unsigned long long>(rdram_base)
        );

        if (rdram_base != 0 && target >= rdram_base) {
            const uint64_t offset = static_cast<uint64_t>(target - rdram_base);
            std::fprintf(
                stderr,
                "[win-crash] rdram_offset=0x%llX",
                static_cast<unsigned long long>(offset)
            );

            if (offset <= 0xFFFFFFFFULL) {
                const uint32_t low = static_cast<uint32_t>(offset);
                if (low < 0x20000000u) {
                    std::fprintf(
                        stderr,
                        " n64_kseg0=0x%08X",
                        0x80000000u + low
                    );
                }
                else if (low < 0x40000000u) {
                    std::fprintf(
                        stderr,
                        " n64_kseg1=0x%08X",
                        0x80000000u + low
                    );
                }
            }
            std::fprintf(stderr, "\n");
        }
    }

    std::fflush(stderr);
    return EXCEPTION_CONTINUE_SEARCH;
}

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
    wc.hCursor = LoadCursorW(nullptr, MAKEINTRESOURCEW(32512));
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
    uint8_t* rdram,
    ultramodern::renderer::WindowHandle,
    bool
) {
    g_rdram.store(rdram);
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

void print_thread_snapshot(uint8_t* rdram, uint32_t vaddr, const char* label) {
    const PTR(OSThread) addr = static_cast<int32_t>(vaddr);
    const OSThread* thread = TO_PTR(OSThread, addr);

    std::printf(
        "[boot-snapshot] %-11s addr=0x%08X id=%d pri=%d state=%u sp=0x%08X queue=0x%08X context=%p\n",
        label,
        vaddr,
        thread->id,
        thread->priority,
        static_cast<unsigned>(thread->state),
        static_cast<unsigned>(thread->sp),
        static_cast<unsigned>(thread->queue),
        static_cast<void*>(thread->context)
    );
}

void print_boot_snapshot() {
    uint8_t* rdram = g_rdram.load();
    if (rdram == nullptr) {
        std::printf("[boot-snapshot] RDRAM indisponible.\n");
        return;
    }

    std::printf("[boot-snapshot] Structures OSThread NP3F apres 3 secondes:\n");
    print_thread_snapshot(rdram, 0x800A82A0u, "idle/id1");
    print_thread_snapshot(rdram, 0x800D05D0u, "crash/id2");
    print_thread_snapshot(rdram, 0x800CE190u, "rsp/id20");
    print_thread_snapshot(rdram, 0x800CD040u, "thread/id3");
    print_thread_snapshot(rdram, 0x80122B40u, "thread/id4");
    print_thread_snapshot(rdram, 0x800CDA80u, "thread/id21");
    print_thread_snapshot(rdram, 0x800A8850u, "game/id6");
}


bool plausible_rdram_ptr(uint32_t value) {
    return value == 0 ||
           value == 0xFFFFFFFFu ||
           (value >= 0x80000000u && value < 0x80800000u);
}

void scan_known_np3f_threads() {
    uint8_t* rdram = g_rdram.load();
    if (rdram == nullptr) {
        std::printf("[thread-scan] RDRAM indisponible.\n");
        return;
    }

    constexpr std::array<int32_t, 8> kInterestingIds{1, 2, 3, 4, 5, 6, 20, 21};
    constexpr uint32_t kRdramSize = 8u * 1024u * 1024u;

    std::printf("[thread-scan] Scan RDRAM des OSThread NP3F connus:\n");

    uint32_t found = 0;
    for (uint32_t offset = 0; offset + sizeof(OSThread) <= kRdramSize; offset += 4) {
        OSThread thread{};
        std::memcpy(&thread, rdram + offset, sizeof(thread));

        bool interesting_id = false;
        for (int32_t id : kInterestingIds) {
            if (thread.id == id) {
                interesting_id = true;
                break;
            }
        }
        if (!interesting_id) {
            continue;
        }

        const uint32_t sp = static_cast<uint32_t>(thread.sp);
        const uint32_t queue = static_cast<uint32_t>(thread.queue);
        if (thread.priority < 0 || thread.priority > 255) {
            continue;
        }
        if (thread.state > 3) {
            continue;
        }
        if (!(sp >= 0x80000000u && sp < 0x80800000u)) {
            continue;
        }
        if (!plausible_rdram_ptr(queue)) {
            continue;
        }
        if (thread.context == nullptr) {
            continue;
        }

        std::printf(
            "[thread-scan] addr=0x%08X id=%d pri=%d state=%u sp=0x%08X queue=0x%08X context=%p\n",
            0x80000000u + offset,
            thread.id,
            thread.priority,
            static_cast<unsigned>(thread.state),
            sp,
            queue,
            static_cast<void*>(thread.context)
        );
        ++found;
    }

    std::printf("[thread-scan] Total candidats valides: %u\n", found);
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

void trace_np3f_on_init(uint8_t* rdram, recomp_context* ctx) {
    // IPL3 stores osTvType at virtual address 0x80000300, i.e. RDRAM offset 0x300.
    // Access the RDRAM offset directly here instead of feeding an unsigned KSEG0
    // address into MEM_W, which expects a sign-extended 64-bit N64 address.
    constexpr size_t kOsTvTypeOffset = 0x300;
    constexpr int32_t kOsTvPal = 0;

    auto* os_tv_type = reinterpret_cast<int32_t*>(rdram + kOsTvTypeOffset);
    const int32_t runtime_tv_type = *os_tv_type;
    *os_tv_type = kOsTvPal;

    std::printf(
        "[cpu-trace] on_init NP3F: sp=0x%08X ra=0x%08X osTvType=%d -> %d (PAL)\n",
        static_cast<unsigned>(ctx->r29),
        static_cast<unsigned>(ctx->r31),
        runtime_tv_type,
        *os_tv_type
    );
    std::fflush(stdout);
}

void traced_np3f_entrypoint(uint8_t* rdram, recomp_context* ctx) {
    g_entrypoint_started.store(true);
    std::printf(
        "[cpu-trace] ENTREE recomp_entrypoint NP3F: sp=0x%08X ra=0x%08X\n",
        static_cast<unsigned>(ctx->r29),
        static_cast<unsigned>(ctx->r31)
    );
    std::fflush(stdout);

    recomp_entrypoint(rdram, ctx);

    g_entrypoint_returned.store(true);
    std::printf("[cpu-trace] SORTIE recomp_entrypoint NP3F\n");
    std::fflush(stdout);
}

void trace_np3f_thread_create(uint8_t* rdram, recomp_context* ctx) {
    const uint32_t index = g_created_thread_count.fetch_add(1) + 1;

    const PTR(OSThread) current_thread_addr = ultramodern::this_thread();
    OSThread* current_thread = nullptr;
    if (current_thread_addr != NULLPTR) {
        current_thread = TO_PTR(OSThread, current_thread_addr);
    }

    if (current_thread != nullptr) {
        std::printf(
            "[cpu-trace] Thread N64 #%u: id=%d pri=%d state=%u thread=0x%08X sp=0x%08X arg=0x%08X ra=0x%08X\n",
            index,
            current_thread->id,
            current_thread->priority,
            static_cast<unsigned>(current_thread->state),
            static_cast<unsigned>(current_thread_addr),
            static_cast<unsigned>(ctx->r29),
            static_cast<unsigned>(ctx->r4),
            static_cast<unsigned>(ctx->r31)
        );
    }
    else {
        std::printf(
            "[cpu-trace] Thread N64 #%u: OSThread inconnu sp=0x%08X arg=0x%08X ra=0x%08X\n",
            index,
            static_cast<unsigned>(ctx->r29),
            static_cast<unsigned>(ctx->r4),
            static_cast<unsigned>(ctx->r31)
        );
    }

    std::fflush(stdout);
}

void run_np3f_runtime_probe(const std::u8string& game_id) {
    SetUnhandledExceptionFilter(probe_unhandled_exception_filter);
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
    std::thread boot_watchdog([]() {
        using namespace std::chrono_literals;
        std::this_thread::sleep_for(3s);
        std::printf(
            "[cpu-trace] Watchdog 3s: entrypoint=%s retour=%s threads_executes=%u rsp=%s displaylist=%s\n",
            g_entrypoint_started.load() ? "oui" : "non",
            g_entrypoint_returned.load() ? "oui" : "non",
            g_created_thread_count.load(),
            g_logged_rsp_task.load() ? "oui" : "non",
            g_logged_display_list.load() ? "oui" : "non"
        );
        print_boot_snapshot();
        scan_known_np3f_threads();
        std::fflush(stdout);
    });
    boot_watchdog.detach();

    recomp::start_game(game_id, "");
    recomp::start(cfg);
    std::printf("[runtime-probe] N64ModernRuntime termine.\n");
}

} // namespace aerostadium2
