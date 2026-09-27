#include <atomic>
#include <cstdio>
#include <memory>
#include <string>
#include <thread>
#include <chrono>
#include <cstring>
#include <array>
#include <algorithm>
#include <fstream>
#include <vector>
#include <cstdlib>
#include <iterator>
#include <mutex>
#include <SDL.h>

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#include "recomp.h"
#include "librecomp/game.hpp"
#include "librecomp/rsp.hpp"
#include "ultramodern/ultramodern.hpp"
#include "np3f_rt64_renderer.h"
#include "np3f_sdl_input.h"

extern "C" void recomp_entrypoint(uint8_t* rdram, recomp_context* ctx);
RspExitReason aspMain_np3f(uint8_t* rdram, uint32_t ucode_addr);
RspExitReason task4_np3f(uint8_t* rdram, uint32_t ucode_addr);

namespace {

std::atomic_bool g_logged_display_list = false;
std::atomic_bool g_logged_rsp_task = false;
std::atomic_uint32_t g_created_thread_count = 0;
std::atomic_bool g_entrypoint_started = false;
std::atomic_bool g_entrypoint_returned = false;
std::atomic<uint8_t*> g_rdram = nullptr;
std::atomic_uint32_t g_completed_display_lists = 0;
std::atomic<ULONGLONG> g_last_display_list_tick = 0;
std::array<std::atomic<DWORD>, 16> g_guest_thread_ids{};
std::atomic_uint16_t g_buttons = 0;
std::atomic_uint16_t g_pressed_buttons = 0;
std::atomic_uint32_t g_stick_keys = 0;
std::mutex g_audio_mutex;
SDL_AudioDeviceID g_audio_device = 0;
std::atomic_uint64_t g_audio_samples = 0;
std::atomic_uint32_t g_audio_peak = 0;

struct MapSymbol {
    uint64_t address = 0;
    std::string name;
};

std::vector<MapSymbol> g_map_symbols;
uint64_t g_map_preferred_base = 0;

void load_probe_map_symbols() {
    wchar_t exe_path[MAX_PATH]{};
    const DWORD len = GetModuleFileNameW(nullptr, exe_path, static_cast<DWORD>(std::size(exe_path)));
    if (len == 0 || len >= std::size(exe_path)) {
        std::fprintf(stderr, "[map-symbols] Impossible de determiner le chemin EXE.\n");
        return;
    }

    std::wstring map_path(exe_path, len);
    const size_t dot = map_path.find_last_of(L'.');
    if (dot != std::wstring::npos) {
        map_path.resize(dot);
    }
    map_path += L".map";

    std::ifstream input(map_path);
    if (!input) {
        std::fprintf(stderr, "[map-symbols] Fichier MAP introuvable.\n");
        return;
    }

    std::string line;
    while (std::getline(input, line)) {
        const char* preferred_marker = "Preferred load address is ";
        const size_t marker_pos = line.find(preferred_marker);
        if (marker_pos != std::string::npos) {
            const char* value = line.c_str() + marker_pos + std::strlen(preferred_marker);
            g_map_preferred_base = std::strtoull(value, nullptr, 16);
            continue;
        }

        unsigned section = 0;
        unsigned long long section_offset = 0;
        unsigned long long absolute = 0;
        char name[512]{};
        if (std::sscanf(
                line.c_str(),
                " %x:%llx %511s %llx",
                &section,
                &section_offset,
                name,
                &absolute
            ) == 4) {
            g_map_symbols.push_back(MapSymbol{
                .address = static_cast<uint64_t>(absolute),
                .name = name,
            });
        }
    }

    std::sort(
        g_map_symbols.begin(),
        g_map_symbols.end(),
        [](const MapSymbol& a, const MapSymbol& b) {
            return a.address < b.address;
        }
    );

    std::fprintf(
        stderr,
        "[map-symbols] MAP charge: %zu symboles, preferred_base=0x%llX\n",
        g_map_symbols.size(),
        static_cast<unsigned long long>(g_map_preferred_base)
    );
    std::fflush(stderr);
}

void print_probe_map_symbol(uintptr_t exception_rva) {
    if (g_map_preferred_base == 0 || g_map_symbols.empty()) {
        return;
    }

    const uint64_t preferred_address =
        g_map_preferred_base + static_cast<uint64_t>(exception_rva);

    const auto it = std::upper_bound(
        g_map_symbols.begin(),
        g_map_symbols.end(),
        preferred_address,
        [](uint64_t address, const MapSymbol& symbol) {
            return address < symbol.address;
        }
    );

    if (it == g_map_symbols.begin()) {
        return;
    }

    const MapSymbol& symbol = *std::prev(it);
    const uint64_t delta = preferred_address - symbol.address;
    std::fprintf(
        stderr,
        "[win-symbol] nearest=%s +0x%llX preferred=0x%llX\n",
        symbol.name.c_str(),
        static_cast<unsigned long long>(delta),
        static_cast<unsigned long long>(preferred_address)
    );
}

// Sample only this process's guest threads when a bounded probe stops making
// progress. Resume each thread before formatting symbols or writing logs.
void print_stalled_guest_stacks() {
    const uintptr_t module = reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
    for (const auto& entry : g_guest_thread_ids) {
        const DWORD id = entry.load();
        if (!id) continue;
        HANDLE thread = OpenThread(THREAD_SUSPEND_RESUME | THREAD_GET_CONTEXT, FALSE, id);
        if (!thread) continue;
        DWORD64 frames[48]{};
        size_t count = 0;
        if (SuspendThread(thread) != DWORD(-1)) {
            CONTEXT context{};
            context.ContextFlags = CONTEXT_FULL;
            if (GetThreadContext(thread, &context)) {
                while (context.Rip && count < std::size(frames)) {
                    frames[count++] = context.Rip;
                    DWORD64 image_base = 0;
                    auto* function = RtlLookupFunctionEntry(context.Rip, &image_base, nullptr);
                    if (function) {
                        PVOID handler_data = nullptr;
                        DWORD64 establisher = 0;
                        RtlVirtualUnwind(UNW_FLAG_NHANDLER, image_base, context.Rip,
                            function, &context, &handler_data, &establisher, nullptr);
                    } else {
                        SIZE_T bytes = 0;
                        if (!ReadProcessMemory(GetCurrentProcess(), reinterpret_cast<void*>(context.Rsp),
                            &context.Rip, sizeof(context.Rip), &bytes) || bytes != sizeof(context.Rip)) break;
                        context.Rsp += sizeof(DWORD64);
                    }
                }
            }
            ResumeThread(thread);
        }
        CloseHandle(thread);
        std::fprintf(stderr, "[guest-stack] host_thread=%lu frames=%zu\n", id, count);
        for (size_t i = 0; i < count; ++i) {
            if (frames[i] >= module && frames[i] - module < 0x10000000ULL)
                print_probe_map_symbol(frames[i] - module);
        }
    }
}


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

    print_probe_map_symbol(exception_rva);

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
            if (offset <= 0xFFFFFFFFULL) {
                std::fprintf(
                    stderr,
                    "[win-crash] rdram_offset=0x%llX",
                    static_cast<unsigned long long>(offset)
                );

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
                std::fprintf(stderr, "\n");
            }
        }
    }

    std::fflush(stderr);
    return EXCEPTION_CONTINUE_SEARCH;
}

LRESULT CALLBACK probe_window_proc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    switch (msg) {
        case WM_KEYDOWN:
        case WM_KEYUP: {
            uint16_t mask = 0;
            uint32_t stick = 0;
            switch (wparam) {
                case VK_RETURN: mask = 0x1000; break;
                case 'X': mask = 0x8000; break;
                case 'C': mask = 0x4000; break;
                case 'Z': mask = 0x2000; break;
                case 'Q': mask = 0x0020; break;
                case 'E': mask = 0x0010; break;
                case VK_UP: mask = 0x0800; break;
                case VK_DOWN: mask = 0x0400; break;
                case VK_LEFT: mask = 0x0200; break;
                case VK_RIGHT: mask = 0x0100; break;
                case 'I': mask = 0x0008; break;
                case 'K': mask = 0x0004; break;
                case 'J': mask = 0x0002; break;
                case 'L': mask = 0x0001; break;
                case 'W': stick = 1; break;
                case 'S': stick = 2; break;
                case 'A': stick = 4; break;
                case 'D': stick = 8; break;
            }
            if (msg == WM_KEYDOWN) {
                if ((lparam & (1LL << 30)) == 0) g_pressed_buttons.fetch_or(mask);
                g_buttons.fetch_or(mask); g_stick_keys.fetch_or(stick);
            } else {
                g_buttons.fetch_and(uint16_t(~mask)); g_stick_keys.fetch_and(~stick);
            }
            return 0;
        }
        case WM_KILLFOCUS:
            g_buttons.store(0); g_pressed_buttons.store(0); g_stick_keys.store(0);
            return 0;
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
    aerostadium2::input::pump_controller_events();
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
    ultramodern::renderer::WindowHandle window_handle,
    bool developer_mode
) {
    g_rdram.store(rdram);

#if defined(AEROSTADIUM2_WITH_RT64)
    std::printf("[runtime-probe] Initialisation du renderer RT64...\n");
    std::fflush(stdout);
    return aerostadium2::create_rt64_renderer_context(
        rdram,
        window_handle,
        developer_mode
    );
#else
    std::printf("[runtime-probe] Renderer factice initialise.\n");
    return std::make_unique<ProbeRendererContext>();
#endif
}

RspUcodeFunc* get_rsp_microcode(const OSTask* task) {
    if (!g_logged_rsp_task.exchange(true)) {
        std::printf(
            "[runtime-probe] Premiere tache RSP recue: type=%u ucode=0x%08X data=0x%08X\n",
            task->t.type,
            task->t.ucode,
            task->t.ucode_data
        );
        std::printf("[audio-rsp] Executing recompiled NP3F audio microcode.\n");
    }
    if (task->t.type == 2 && uint32_t(task->t.ucode) == 0x80000460u &&
        task->t.ucode_size == 0x1000 && uint32_t(task->t.ucode_data) == 0x80087010u &&
        task->t.ucode_data_size == 0x2DF) return aspMain_np3f;
    if (task->t.type == 4 && uint32_t(task->t.ucode) == 0x80085390 &&
        task->t.ucode_size == 0x1000 && uint32_t(task->t.ucode_data) == 0x800A7E40 &&
        task->t.ucode_data_size == 0x800) {
        static bool logged = false;
        if (!logged) {
            std::fprintf(stderr, "[rsp-task4] Executing verified recompiled NP3F microcode.\n");
            logged = true;
        }
        return task4_np3f;
    }
    std::fprintf(stderr, "[rsp] Unsupported task type=%u ucode=%08X size=%08X data=%08X data_size=%08X task_data=%08X task_size=%08X\n",
        task->t.type, task->t.ucode, task->t.ucode_size, task->t.ucode_data,
        task->t.ucode_data_size, task->t.data_ptr, task->t.data_size);
    return nullptr;
}

void queue_samples(int16_t* samples, size_t count) {
    std::lock_guard lock(g_audio_mutex);
    std::vector<int16_t> output(count);
    uint32_t peak = 0;
    // RDRAM stores each 32-bit word in host order, reversing its two samples.
    for (size_t i = 0; i + 1 < count; i += 2) {
        output[i] = samples[i + 1]; output[i + 1] = samples[i];
        peak = (std::max)(peak, uint32_t((std::max)(std::abs(int(output[i])), std::abs(int(output[i + 1])))));
    }
    g_audio_samples.fetch_add(count);
    g_audio_peak.store((std::max)(g_audio_peak.load(), peak));
    if (g_audio_device && SDL_QueueAudio(g_audio_device, output.data(), Uint32(output.size() * sizeof(int16_t))) != 0)
        std::fprintf(stderr, "[audio] Queue failed: %s\n", SDL_GetError());
}

size_t get_frames_remaining() {
    std::lock_guard lock(g_audio_mutex);
    return g_audio_device ? SDL_GetQueuedAudioSize(g_audio_device) / (2 * sizeof(int16_t)) : 0;
}

void set_frequency(uint32_t frequency) {
    std::lock_guard lock(g_audio_mutex);
    if (g_audio_device) SDL_CloseAudioDevice(g_audio_device);
    g_audio_device = 0;
    if (SDL_InitSubSystem(SDL_INIT_AUDIO) != 0) {
        std::fprintf(stderr, "[audio] SDL initialization failed: %s\n", SDL_GetError()); return;
    }
    SDL_AudioSpec wanted{};
    wanted.freq = int(frequency); wanted.format = AUDIO_S16SYS;
    wanted.channels = 2; wanted.samples = 1024;
    g_audio_device = SDL_OpenAudioDevice(nullptr, 0, &wanted, nullptr, 0);
    if (!g_audio_device) {
        std::fprintf(stderr, "[audio] Device unavailable: %s\n", SDL_GetError()); return;
    }
    SDL_PauseAudioDevice(g_audio_device, 0);
    std::printf("[audio] Stereo device opened: %u Hz\n", frequency);
}

void poll_input() { aerostadium2::input::poll_controllers(); }

bool get_input(int controller, uint16_t* buttons, float* x, float* y) {
    uint16_t pad_buttons = 0;
    float pad_x = 0, pad_y = 0;
    const bool connected = aerostadium2::input::get_controller_input(controller, &pad_buttons, &pad_x, &pad_y);
    const auto stick = controller == 0 ? g_stick_keys.load() : 0;
    if (buttons != nullptr) {
        // Deliver each short key press to at least one controller poll, even
        // when both Windows key messages arrive between two game frames.
        *buttons = pad_buttons | (controller == 0 ? (g_buttons.load() | g_pressed_buttons.exchange(0)) : 0);
    }
    if (x != nullptr) {
        *x = stick & 12 ? float(bool(stick & 8)) - float(bool(stick & 4)) : pad_x;
    }
    if (y != nullptr) {
        *y = stick & 3 ? float(bool(stick & 1)) - float(bool(stick & 2)) : pad_y;
    }
    return controller == 0 || connected;
}

void set_rumble(int controller, bool value) { aerostadium2::input::set_controller_rumble(controller, value); }

ultramodern::input::connected_device_info_t get_connected_device_info(int controller_num) {
    if (controller_num == 0) {
        return {
            .connected_device = ultramodern::input::Device::Controller,
            .connected_pak = ultramodern::input::Pak::None,
        };
    }

    return aerostadium2::input::get_connected_controller_info(controller_num);
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

void set_overlay_rdram(uint8_t* rdram);

void mark_rt64_display_list_seen() {
    g_logged_display_list.store(true);
    g_completed_display_lists.fetch_add(1);
    g_last_display_list_tick.store(GetTickCount64());
}

void trace_np3f_on_init(uint8_t* rdram, recomp_context* ctx) {
    set_overlay_rdram(rdram);
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
    if (index <= g_guest_thread_ids.size()) g_guest_thread_ids[index - 1].store(GetCurrentThreadId());

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

void run_np3f_runtime_probe(const std::u8string& game_id, unsigned test_seconds) {
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    std::setvbuf(stderr, nullptr, _IONBF, 0);
    load_probe_map_symbols();
    SetUnhandledExceptionFilter(probe_unhandled_exception_filter);
    aerostadium2::input::initialize_controllers();
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

    if (test_seconds != 0) {
        std::thread([test_seconds]() {
            std::this_thread::sleep_for(std::chrono::seconds(test_seconds));
            const auto completed = g_completed_display_lists.load();
            const auto age = GetTickCount64() - g_last_display_list_tick.load();
            const bool progressing = completed > 0 && age < 5000;
            std::fprintf(stderr,
                "[test-result] seconds=%u entrypoint=%d threads=%u rsp=%d displaylist=%d completed=%u age_ms=%llu progressing=%d\n",
                test_seconds, g_entrypoint_started.load(), g_created_thread_count.load(),
                g_logged_rsp_task.load(), g_logged_display_list.load(), completed, age, progressing);
            if (!progressing) print_stalled_guest_stacks();
            std::fprintf(stderr, "[audio-result] samples=%llu peak=%u\n", g_audio_samples.load(), g_audio_peak.load());
            // A bounded diagnostic run is not a validation of gameplay/audio.
            ExitProcess(progressing ? 0 : 24);
        }).detach();
    }

    recomp::start_game(game_id, "");
    recomp::start(cfg);
    aerostadium2::input::shutdown_controllers();
    std::printf("[runtime-probe] N64ModernRuntime termine.\n");
}

} // namespace aerostadium2
