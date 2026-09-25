#include <cstdio>
#include <cstdint>
#include <filesystem>
#include <string>

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <commdlg.h>
#include <shlobj.h>

#include "recomp.h"
#include "librecomp/game.hpp"

namespace aerostadium2 { void register_np3f_overlays(); }

extern "C" void recomp_entrypoint(uint8_t* rdram, recomp_context* ctx);
gpr get_entrypoint_address();
const char* get_rom_name();

namespace {

constexpr uint64_t kNp3fRomHash = 0x93AC31A17326F35BULL;
const std::u8string kNp3fGameId = u8"pokemon_stadium_2_fr";

std::filesystem::path get_config_path() {
    PWSTR local_app_data = nullptr;
    if (SUCCEEDED(SHGetKnownFolderPath(FOLDERID_LocalAppData, KF_FLAG_DEFAULT, nullptr, &local_app_data)) &&
        local_app_data != nullptr) {
        std::filesystem::path result = std::filesystem::path(local_app_data) / L"AeroStadium2";
        CoTaskMemFree(local_app_data);
        return result;
    }

    return std::filesystem::current_path() / "AeroStadium2";
}

std::filesystem::path select_rom_file() {
    wchar_t file_name[32768] = {};

    OPENFILENAMEW dialog{};
    dialog.lStructSize = sizeof(dialog);
    dialog.hwndOwner = nullptr;
    dialog.lpstrFilter =
        L"ROM Nintendo 64 (*.z64;*.n64;*.v64)\0*.z64;*.n64;*.v64\0"
        L"Tous les fichiers (*.*)\0*.*\0\0";
    dialog.lpstrFile = file_name;
    dialog.nMaxFile = static_cast<DWORD>(std::size(file_name));
    dialog.lpstrTitle = L"Selectionner la ROM francaise de Pokemon Stadium 2";
    dialog.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_NOCHANGEDIR;

    if (GetOpenFileNameW(&dialog) == TRUE) {
        return std::filesystem::path(file_name);
    }

    return {};
}

const wchar_t* validation_error_text(recomp::RomValidationError error) {
    switch (error) {
        case recomp::RomValidationError::Good:
            return L"ROM valide.";
        case recomp::RomValidationError::FailedToOpen:
            return L"Impossible d'ouvrir le fichier selectionne.";
        case recomp::RomValidationError::NotARom:
            return L"Le fichier selectionne n'est pas une ROM Nintendo 64 valide.";
        case recomp::RomValidationError::IncorrectRom:
            return L"Cette ROM n'est pas Pokemon Stadium 2 France (NP3F).";
        case recomp::RomValidationError::IncorrectVersion:
            return L"Pokemon Stadium 2 a ete reconnu, mais ce n'est pas la version NP3F attendue.";
        case recomp::RomValidationError::NotYet:
            return L"Cette version de la ROM n'est pas encore prise en charge.";
        case recomp::RomValidationError::OtherError:
        default:
            return L"Erreur inconnue pendant la validation de la ROM.";
    }
}

bool ensure_np3f_rom_loaded() {
    if (recomp::load_stored_rom(kNp3fGameId)) {
        std::printf("ROM NP3F stockee et validee: OK\n");
        return true;
    }

    MessageBoxW(
        nullptr,
        L"Aero Stadium 2 a besoin de votre ROM francaise de Pokemon Stadium 2 (NP3F).\n\n"
        L"Selectionnez votre dump legal dans la fenetre suivante. Les formats .z64, .n64 et .v64 sont acceptes.",
        L"Aero Stadium 2 - Premier lancement",
        MB_OK | MB_ICONINFORMATION
    );

    const std::filesystem::path selected_rom = select_rom_file();
    if (selected_rom.empty()) {
        std::printf("Selection de ROM annulee.\n");
        return false;
    }

    const recomp::RomValidationError validation = recomp::select_rom(selected_rom, kNp3fGameId);
    if (validation != recomp::RomValidationError::Good) {
        MessageBoxW(
            nullptr,
            validation_error_text(validation),
            L"Aero Stadium 2 - ROM refusee",
            MB_OK | MB_ICONERROR
        );
        std::printf("Validation ROM: ECHEC (%d)\n", static_cast<int>(validation));
        return false;
    }

    if (!recomp::load_stored_rom(kNp3fGameId)) {
        MessageBoxW(
            nullptr,
            L"La ROM a ete validee mais son chargement depuis le cache local a echoue.",
            L"Aero Stadium 2 - Erreur",
            MB_OK | MB_ICONERROR
        );
        return false;
    }

    MessageBoxW(
        nullptr,
        L"Pokemon Stadium 2 France (NP3F) a ete reconnu avec succes.\n\n"
        L"La ROM normalisee est maintenant stockee dans les donnees locales d'Aero Stadium 2.",
        L"Aero Stadium 2 - ROM validee",
        MB_OK | MB_ICONINFORMATION
    );

    std::printf("Validation ROM NP3F: OK\n");
    return true;
}

} // namespace

int main() {
    const std::filesystem::path config_path = get_config_path();
    std::filesystem::create_directories(config_path);

    recomp::register_config_path(config_path);

    const recomp::GameEntry np3f_game {
        .rom_hash = kNp3fRomHash,
        .internal_name = "POKEMON STADIUM 2",
        .display_name = "Pokemon Stadium 2 (France)",
        .game_id = kNp3fGameId,
        .mod_game_id = "aerostadium2",
        .save_type = recomp::SaveType::Flashram,
        .thumbnail_bytes = {},
        .is_enabled = true,
        .decompression_routine = nullptr,
        .has_compressed_code = false,
        .entrypoint_address = get_entrypoint_address(),
        .entrypoint = recomp_entrypoint,
        .thread_create_callback = nullptr,
        .on_init_callback = nullptr,
    };

    recomp::register_game(np3f_game);
    aerostadium2::register_np3f_overlays();

    std::printf("Aero Stadium 2 - launcher bootstrap NP3F\n");
    std::printf("Linkage N64ModernRuntime: OK\n");
    std::printf("GameEntry NP3F: OK\n");
    std::printf("Overlays NP3F: OK\n");
    std::printf("Hash NP3F attendu: 0x%016llX\n", static_cast<unsigned long long>(kNp3fRomHash));
    std::printf("Point d entree NP3F: 0x%08X\n", static_cast<std::uint32_t>(get_entrypoint_address()));
    std::printf("Nom ROM N64Recomp: %s\n", get_rom_name());
    std::printf("Dossier de donnees: %ls\n", config_path.c_str());

    if (!ensure_np3f_rom_loaded()) {
        return 0;
    }

    std::printf("ROM NP3F chargee en memoire: OK\n");
    std::printf("Etape suivante: initialisation des callbacks RSP/rendu/audio/input puis recomp::start_game().\n");

    return 0;
}
