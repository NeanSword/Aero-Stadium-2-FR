# Dependency map

## Reconstruction

**pret/pokestadiumgs**

Pinned submodule:

    upstream/pokestadiumgs

Role: reference reconstruction/decompilation base for Stadium 2 US/JP.

The current upstream project documents itself as a WIP decompilation and requires the user to provide a ROM. Its current Makefile targets Unix-like build environments rather than native Windows. citeturn894293search1

## Native recompilation

**N64Recomp**

Pinned submodule:

    upstream/N64Recomp

Role: static recompilation of an N64 ELF into native C code. citeturn894293search0

## Runtime

**N64ModernRuntime**

Pinned submodule:

    upstream/N64ModernRuntime

Role: runtime layer for traditional N64 ports/recompilations, including the bridge used by generated code and platform-facing services. citeturn894293search6

## Frontend

**RecompFrontend**

Pinned submodule:

    upstream/RecompFrontend

Role: optional frontend layer for menus, input handling and common PC-port UI functionality once the core recompiled game is operational.

## Project-owned layer

**Aero-Stadium-2-FR**

The project-specific layer owns:

- NP3F ROM identification and reconstruction metadata;
- Windows-first tooling;
- the fixed-step timing boundary;
- future input/audio/render integration;
- future PC configuration and multiplayer transport logic.

The dependency tree is intentionally layered so the game reconstruction can be validated separately from modern PC features.
