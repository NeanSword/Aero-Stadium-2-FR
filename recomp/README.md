# Native recompilation boundary

The project uses the pinned N64Recomp tool after the NP3F ROM layout and function metadata are stable.

## Pinned dependencies

The repository tracks these public projects as Git submodules:

- `upstream/N64Recomp`
- `upstream/N64ModernRuntime`
- `upstream/RecompFrontend`

They are pinned to the commits recorded in this repository's Git history so a checkout is reproducible.

The pinned N64Recomp commit used here supports two metadata paths: ELF input, or a function-symbol TOML paired directly with the ROM. Aero-Stadium-2-FR now targets the second path first, avoiding an unnecessary intermediate matching ELF while the NP3F reconstruction is still being developed.

N64ModernRuntime provides the runtime bridge for recompiled N64 projects, including platform/runtime integration and facilities such as overlay handling and ROM-related services. Its upstream documentation recommends CMake integration and supports recent MSVC/GCC toolchains.

## Planned boundary

    NP3F ROM
        |
        v
    Splat / reconstruction
        |
        v
    validated NP3F ELF + metadata
        |
        v
    N64Recomp
        |
        v
    native C/C++
        |
        v
    Aero runtime host
        |
        +--> fixed-step simulation
        +--> input
        +--> audio
        +--> renderer
        +--> Windows platform

No N64Recomp source is copied into this repository. The submodules keep the dependency boundary explicit.

The fixed-step runtime under `native/` remains independently testable so timing behavior can be validated before the recompiled game is connected.


## First NP3F recompilation pass

The current experimental path is:

    canonical yamls/fr/splat.yaml
        |
        v
    Splat --disassemble-all
        |
        v
    tools/recomp/generate_np3f_symbols.py
        |
        +--> build/np3f/recomp/np3f.syms.toml
        |
        v
    recomp/np3f.toml
        |
        v
    .local/bin/N64Recomp.exe
        |
        v
    generated/recomp/np3f/

On Windows without Git:

    .\windows\bootstrap_n64recomp.ps1
    .\windows\run_np3f_recomp_prepare.ps1

The bootstrap downloads the exact pinned N64Recomp commit and its required submodules as GitHub source archives into `.local/`, which is ignored by the repository.

This first pass deliberately does not claim runtime correctness yet. Its purpose is to establish a reproducible static-recompilation boundary and expose missing function metadata, overlay relocation needs, unsupported instructions, and runtime interfaces as concrete diagnostics.
