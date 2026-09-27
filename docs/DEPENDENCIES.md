# Dependency map

## Reconstruction reference

### pret/pokestadiumgs

Submodule:

```text
upstream/pokestadiumgs
```

Role:

- reference reconstruction/decompilation base for Pokémon Stadium 2 US/JP;
- source of comparison material used during the NP3F mapping work;
- historical reference for symbols and layout relationships.

The French NP3F-specific reconstruction data remains owned by this repository.

## Static recompilation

### N64Recomp

Pinned Windows bootstrap commit:

```text
ffb39cdad1da5de07eaaa48bd1db4a89a7986771
```

Submodule:

```text
upstream/N64Recomp
```

Role:

- consume the NP3F symbol TOML and local ROM;
- generate native C translation units;
- generate the function lookup source used by the static library.

The Windows bootstrap also downloads the exact dependencies required by this revision into `.local/`.

## Runtime

### N64ModernRuntime

Pinned Windows bootstrap commit:

```text
cdf5abbd5026fef5c364c676e4667c45e42b6863
```

Submodule:

```text
upstream/N64ModernRuntime
```

Role:

- runtime bridge for recompiled N64 code;
- ROM loading and validation integration;
- threading/runtime services;
- function lookup and overlay facilities;
- input callback interfaces;
- platform-facing services used by the linked executable.

The runtime bootstrap embeds the same pinned N64Recomp revision so generated code and runtime headers can share a consistent ABI.

## Graphics

### RT64

Pinned Windows bootstrap commit:

```text
23cab603c4f9f4a8b369b38e036f1aa484603878
```

Role:

- N64 display-list interpretation;
- graphics backend used by the current `AeroStadium2.exe` prototype;
- native graphics API integration.

RT64 is currently linked statically into the Windows probe target. Required runtime DLLs such as DXC and SDL2 are copied beside the executable by CMake.

## Input

### SDL2

SDL2 is currently consumed from RT64's bundled Windows dependency tree.

Role:

- GameController discovery;
- polling;
- hotplug handling;
- N64 button/stick mapping;
- rumble support when available.

The project may later replace or wrap this layer behind a more user-facing input configuration system.

## Frontend reference

### RecompFrontend

Submodule:

```text
upstream/RecompFrontend
```

Role:

- reference for future menus, settings and common PC-port UI patterns.

It is **not** currently part of the linked `AeroStadium2.exe` runtime path.

## Project-owned layer

### Aero-Stadium-2-FR

The project-specific layer owns:

- NP3F ROM identification;
- canonical NP3F Splat layout;
- symbol generation;
- Windows bootstrap/build scripts;
- NP3F memory/runtime compatibility shims;
- PI/EPi DMA overlay registration;
- RT64 renderer integration;
- SDL2 controller mapping;
- runtime instrumentation and crash diagnostics;
- future PC settings, gameplay improvements and networking.

## Dependency boundary

The active Windows path is:

```text
NP3F ROM + metadata
        |
        v
N64Recomp
        |
        v
generated C
        |
        v
AeroNP3FGenerated.lib
        |
        v
AeroStadium2.exe
        |
        +--> N64ModernRuntime
        +--> RT64
        +--> SDL2
        +--> Aero NP3F compatibility layer
```

Generated artifacts and local dependency builds remain outside version control.
