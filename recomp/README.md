# Native recompilation boundary

The project will use N64Recomp after the NP3F reconstruction reaches a stable ELF and symbol/section metadata.

N64Recomp's current workflow accepts an ELF together with symbol/section metadata and emits native C code. Its output is intended to be compiled by a host C compiler and executed through a runtime layer.

For Aero-Stadium-2-FR, the intended boundary is:

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

No N64Recomp source is copied into this repository yet. This avoids pinning an integration to an unvalidated NP3F ELF before the reconstruction stage is ready.

The fixed-step runtime introduced under native/ is intentionally usable independently of the recompiler so that timing behavior can be tested first.
