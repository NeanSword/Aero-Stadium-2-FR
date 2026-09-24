# Native recompilation boundary

The project will use N64Recomp after the NP3F reconstruction reaches a stable ELF and symbol/section metadata.

## Pinned dependencies

The repository tracks these public projects as Git submodules:

- `upstream/N64Recomp`
- `upstream/N64ModernRuntime`
- `upstream/RecompFrontend`

They are pinned to the commits recorded in this repository's Git history so a checkout is reproducible.

N64Recomp currently works from an ELF plus symbols/metadata and emits native C code. The upstream documentation describes this as static recompilation of N64 binaries into native code and notes that ELF is currently the metadata input path.

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
