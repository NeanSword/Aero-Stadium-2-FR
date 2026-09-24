# NP3F mapping status

## Verified findings from the local analysis

The NP3F work is not being treated as a simple file-offset substitution.

The previous analysis established:

- 88 executable fragments were identified in the French ROM;
- the fragment VRAM bases matched the US reference during the analysis;
- ROM file offsets moved by cumulative deltas between fragment ranges;
- 8,233 French functions were associated with known US symbols;
- the first 16 bytes matched at the expected US-derived location for 6,039 of 8,233 mapped functions (73.4%);
- the first 32 bytes matched for 5,026 (61.0%);
- the first 64 bytes matched for 3,841 (46.7%).

The fragment deltas used by tooling are stored in `config/np3f_fragments.json`.

## Important distinction

A candidate relocation is **not** equivalent to a verified build.

In particular:

1. identical byte runs can prove relocation anchors but cannot prove changed control flow;
2. localized code and data must be disassembled in the NP3F image;
3. guessed VRAM values must be validated against fragment loading behavior;
4. a candidate YAML must only become a build input after a real reconstruction test confirms its sections;
5. native recompilation should consume a stable ELF/metadata layer rather than directly assuming that ROM offsets are runtime addresses.

The existing candidate YAML and relocated symbol map were generated during analysis and remain evidence artifacts until they are integrated and validated.

## Why the project keeps the reference source separate

`pret/pokestadiumgs` is included as a pinned Git submodule. Its own Makefile currently targets Unix-like environments and explicitly rejects native Windows builds. The Aero-Stadium-2-FR project therefore treats upstream as the reconstruction reference while keeping the Windows-native layer under its own control.

## Native-port direction

N64Recomp currently consumes an ELF plus metadata and emits native C/C++ suitable for compilation with modern host compilers. N64ModernRuntime provides the runtime layer used by modern N64 ports, including the low-level bridge around recompiled code.

That suggests the project boundary:

```
NP3F ROM
   |
   +--> NP3F reconstruction / ELF metadata
   |
   +--> N64Recomp
           |
           +--> native C/C++
           |
           +--> modern runtime
                    |
                    +--> Windows executable
```

This is deliberately separated from the extraction/reconstruction phase so that frame-rate and rendering work can be developed without contaminating the original game-logic timing.
