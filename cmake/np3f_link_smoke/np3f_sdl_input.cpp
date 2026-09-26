#include "np3f_sdl_input.h"

#include <SDL.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <mutex>

namespace aerostadium2::input {
namespace {

constexpr std::size_t kMaxControllers = 4;
constexpr float kStickDeadzone = 0.16f;
constexpr float kCButtonStickThreshold = 0.55f;
constexpr Sint16 kTriggerThreshold = 16384;

// Standard N64 OSContPad button bits.
constexpr uint16_t kN64A = 0x8000;
constexpr uint16_t kN64B = 0x4000;
constexpr uint16_t kN64Z = 0x2000;
constexpr uint16_t kN64Start = 0x1000;
constexpr uint16_t kN64DpadUp = 0x0800;
constexpr uint16_t kN64DpadDown = 0x0400;
constexpr uint16_t kN64DpadLeft = 0x0200;
constexpr uint16_t kN64DpadRight = 0x0100;
constexpr uint16_t kN64L = 0x0020;
constexpr uint16_t kN64R = 0x0010;
constexpr uint16_t kN64CUp = 0x0008;
constexpr uint16_t kN64CDown = 0x0004;
constexpr uint16_t kN64CLeft = 0x0002;
constexpr uint16_t kN64CRight = 0x0001;

struct ControllerSlot {
    SDL_GameController* controller = nullptr;
    SDL_JoystickID instance_id = -1;
};

std::array<ControllerSlot, kMaxControllers> g_slots{};
std::mutex g_controller_mutex;
bool g_initialized = false;

float normalize_axis(Sint16 value) {
    if (value >= 0) {
        return static_cast<float>(value) / 32767.0f;
    }

    return static_cast<float>(value) / 32768.0f;
}

void apply_radial_deadzone(float& x, float& y) {
    const float magnitude = std::sqrt((x * x) + (y * y));
    if (magnitude <= kStickDeadzone) {
        x = 0.0f;
        y = 0.0f;
        return;
    }

    const float clamped_magnitude = std::min(magnitude, 1.0f);
    const float scaled_magnitude =
        (clamped_magnitude - kStickDeadzone) / (1.0f - kStickDeadzone);
    const float scale = scaled_magnitude / magnitude;

    x = std::clamp(x * scale, -1.0f, 1.0f);
    y = std::clamp(y * scale, -1.0f, 1.0f);
}

bool instance_is_open_locked(SDL_JoystickID instance_id) {
    return std::any_of(
        g_slots.begin(),
        g_slots.end(),
        [instance_id](const ControllerSlot& slot) {
            return slot.controller != nullptr && slot.instance_id == instance_id;
        }
    );
}

ControllerSlot* first_free_slot_locked() {
    for (ControllerSlot& slot : g_slots) {
        if (slot.controller == nullptr) {
            return &slot;
        }
    }

    return nullptr;
}

void remove_disconnected_controllers_locked() {
    for (std::size_t index = 0; index < g_slots.size(); ++index) {
        ControllerSlot& slot = g_slots[index];
        if (slot.controller == nullptr) {
            continue;
        }

        if (SDL_GameControllerGetAttached(slot.controller) == SDL_TRUE) {
            continue;
        }

        std::printf(
            "[input] Manette %zu deconnectee.\n",
            index + 1
        );
        SDL_GameControllerClose(slot.controller);
        slot = {};
    }
}

void discover_controllers_locked() {
    const int joystick_count = SDL_NumJoysticks();
    for (int device_index = 0; device_index < joystick_count; ++device_index) {
        if (SDL_IsGameController(device_index) != SDL_TRUE) {
            continue;
        }

        const SDL_JoystickID instance_id =
            SDL_JoystickGetDeviceInstanceID(device_index);
        if (instance_id < 0 || instance_is_open_locked(instance_id)) {
            continue;
        }

        ControllerSlot* slot = first_free_slot_locked();
        if (slot == nullptr) {
            break;
        }

        SDL_GameController* controller = SDL_GameControllerOpen(device_index);
        if (controller == nullptr) {
            std::fprintf(
                stderr,
                "[input] Impossible d'ouvrir la manette SDL #%d: %s\n",
                device_index,
                SDL_GetError()
            );
            continue;
        }

        SDL_Joystick* joystick = SDL_GameControllerGetJoystick(controller);
        slot->controller = controller;
        slot->instance_id = SDL_JoystickInstanceID(joystick);

        const std::size_t port =
            static_cast<std::size_t>(slot - g_slots.data()) + 1;
        const char* name = SDL_GameControllerName(controller);
        std::printf(
            "[input] Manette %zu connectee: %s%s\n",
            port,
            name != nullptr ? name : "controleur SDL",
            SDL_GameControllerHasRumble(controller) == SDL_TRUE
                ? " (vibration disponible)"
                : ""
        );
    }
}

void refresh_devices_locked() {
    remove_disconnected_controllers_locked();
    discover_controllers_locked();
}

bool pressed(SDL_GameController* controller, SDL_GameControllerButton button) {
    return SDL_GameControllerGetButton(controller, button) != 0;
}

} // namespace

bool initialize_controllers() {
    std::scoped_lock lock(g_controller_mutex);

    if (g_initialized) {
        return true;
    }

    if (SDL_InitSubSystem(SDL_INIT_GAMECONTROLLER) != 0) {
        std::fprintf(
            stderr,
            "[input] Initialisation SDL GameController impossible: %s\n",
            SDL_GetError()
        );
        return false;
    }

    SDL_GameControllerEventState(SDL_ENABLE);
    g_initialized = true;
    refresh_devices_locked();

    std::printf(
        "[input] Support manettes SDL2 actif (jusqu'a %zu joueurs).\n",
        kMaxControllers
    );
    std::printf(
        "[input] Mapping: A/Croix=A N64, B/Rond ou X/Carre=B N64, "
        "Start=Start, LB=L, RB ou RT=R, LT=Z, stick droit=C.\n"
    );
    return true;
}

void shutdown_controllers() {
    std::scoped_lock lock(g_controller_mutex);

    if (!g_initialized) {
        return;
    }

    for (ControllerSlot& slot : g_slots) {
        if (slot.controller != nullptr) {
            SDL_GameControllerRumble(slot.controller, 0, 0, 0);
            SDL_GameControllerClose(slot.controller);
            slot = {};
        }
    }

    SDL_QuitSubSystem(SDL_INIT_GAMECONTROLLER);
    g_initialized = false;
}

void pump_controller_events() {
    std::scoped_lock lock(g_controller_mutex);

    if (!g_initialized) {
        return;
    }

    // SDL requires event pumping on the application's UI/graphics thread for
    // reliable hot-plug updates. We do not consume the event queue here.
    SDL_PumpEvents();
    refresh_devices_locked();
}

void poll_controllers() {
    if (!g_initialized) {
        return;
    }

    SDL_GameControllerUpdate();
}

bool get_controller_input(
    int controller_num,
    uint16_t* buttons,
    float* x,
    float* y
) {
    if (controller_num < 0 ||
        controller_num >= static_cast<int>(kMaxControllers)) {
        return false;
    }

    std::scoped_lock lock(g_controller_mutex);
    ControllerSlot& slot = g_slots[static_cast<std::size_t>(controller_num)];
    SDL_GameController* controller = slot.controller;

    if (controller == nullptr ||
        SDL_GameControllerGetAttached(controller) != SDL_TRUE) {
        return false;
    }

    uint16_t n64_buttons = 0;

    // Face buttons. Both east and west are accepted as N64 B so common Xbox
    // and PlayStation layouts are immediately usable during runtime testing.
    if (pressed(controller, SDL_CONTROLLER_BUTTON_A)) {
        n64_buttons |= kN64A;
    }
    if (pressed(controller, SDL_CONTROLLER_BUTTON_B) ||
        pressed(controller, SDL_CONTROLLER_BUTTON_X)) {
        n64_buttons |= kN64B;
    }
    if (pressed(controller, SDL_CONTROLLER_BUTTON_START)) {
        n64_buttons |= kN64Start;
    }

    if (pressed(controller, SDL_CONTROLLER_BUTTON_DPAD_UP)) {
        n64_buttons |= kN64DpadUp;
    }
    if (pressed(controller, SDL_CONTROLLER_BUTTON_DPAD_DOWN)) {
        n64_buttons |= kN64DpadDown;
    }
    if (pressed(controller, SDL_CONTROLLER_BUTTON_DPAD_LEFT)) {
        n64_buttons |= kN64DpadLeft;
    }
    if (pressed(controller, SDL_CONTROLLER_BUTTON_DPAD_RIGHT)) {
        n64_buttons |= kN64DpadRight;
    }

    if (pressed(controller, SDL_CONTROLLER_BUTTON_LEFTSHOULDER)) {
        n64_buttons |= kN64L;
    }
    if (pressed(controller, SDL_CONTROLLER_BUTTON_RIGHTSHOULDER)) {
        n64_buttons |= kN64R;
    }

    const Sint16 left_trigger =
        SDL_GameControllerGetAxis(controller, SDL_CONTROLLER_AXIS_TRIGGERLEFT);
    const Sint16 right_trigger =
        SDL_GameControllerGetAxis(controller, SDL_CONTROLLER_AXIS_TRIGGERRIGHT);

    if (left_trigger > kTriggerThreshold) {
        n64_buttons |= kN64Z;
    }
    if (right_trigger > kTriggerThreshold) {
        n64_buttons |= kN64R;
    }

    // The right stick acts as the four N64 C buttons.
    const float c_x = normalize_axis(
        SDL_GameControllerGetAxis(controller, SDL_CONTROLLER_AXIS_RIGHTX)
    );
    const float c_y = -normalize_axis(
        SDL_GameControllerGetAxis(controller, SDL_CONTROLLER_AXIS_RIGHTY)
    );

    if (c_x > kCButtonStickThreshold) {
        n64_buttons |= kN64CRight;
    }
    else if (c_x < -kCButtonStickThreshold) {
        n64_buttons |= kN64CLeft;
    }

    if (c_y > kCButtonStickThreshold) {
        n64_buttons |= kN64CUp;
    }
    else if (c_y < -kCButtonStickThreshold) {
        n64_buttons |= kN64CDown;
    }

    // Y/Triangle is a convenient additional C-Up shortcut.
    if (pressed(controller, SDL_CONTROLLER_BUTTON_Y)) {
        n64_buttons |= kN64CUp;
    }

    float stick_x = normalize_axis(
        SDL_GameControllerGetAxis(controller, SDL_CONTROLLER_AXIS_LEFTX)
    );
    float stick_y = -normalize_axis(
        SDL_GameControllerGetAxis(controller, SDL_CONTROLLER_AXIS_LEFTY)
    );
    apply_radial_deadzone(stick_x, stick_y);

    if (buttons != nullptr) {
        *buttons = n64_buttons;
    }
    if (x != nullptr) {
        *x = stick_x;
    }
    if (y != nullptr) {
        *y = stick_y;
    }

    return true;
}

void set_controller_rumble(int controller_num, bool rumble) {
    if (controller_num < 0 ||
        controller_num >= static_cast<int>(kMaxControllers)) {
        return;
    }

    std::scoped_lock lock(g_controller_mutex);
    ControllerSlot& slot = g_slots[static_cast<std::size_t>(controller_num)];

    if (slot.controller == nullptr ||
        SDL_GameControllerHasRumble(slot.controller) != SDL_TRUE) {
        return;
    }

    const Uint16 strength = rumble ? 0xFFFFu : 0u;
    const Uint32 duration_ms = rumble ? 0xFFFFFFFFu : 0u;

    if (SDL_GameControllerRumble(
            slot.controller,
            strength,
            strength,
            duration_ms
        ) != 0) {
        std::fprintf(
            stderr,
            "[input] Vibration SDL impossible sur le port %d: %s\n",
            controller_num + 1,
            SDL_GetError()
        );
    }
}

ultramodern::input::connected_device_info_t get_connected_controller_info(
    int controller_num
) {
    if (controller_num < 0 ||
        controller_num >= static_cast<int>(kMaxControllers)) {
        return {
            .connected_device = ultramodern::input::Device::None,
            .connected_pak = ultramodern::input::Pak::None,
        };
    }

    std::scoped_lock lock(g_controller_mutex);
    ControllerSlot& slot = g_slots[static_cast<std::size_t>(controller_num)];

    if (slot.controller == nullptr ||
        SDL_GameControllerGetAttached(slot.controller) != SDL_TRUE) {
        return {
            .connected_device = ultramodern::input::Device::None,
            .connected_pak = ultramodern::input::Pak::None,
        };
    }

    return {
        .connected_device = ultramodern::input::Device::Controller,
        .connected_pak =
            SDL_GameControllerHasRumble(slot.controller) == SDL_TRUE
                ? ultramodern::input::Pak::RumblePak
                : ultramodern::input::Pak::None,
    };
}

} // namespace aerostadium2::input
