# Development status

## Base

- Repository initialized.
- Upstream reconstruction referenced as a pinned submodule.
- NP3F ROM metadata recorded without storing the ROM.
- Windows-oriented scripts introduced.
- NP3F comparison and relocation tooling added.

## Verified analysis already available

- 88 executable fragments mapped in the French ROM.
- VRAM bases observed as aligned with the US reference.
- Cumulative ROM relocation ranges established.
- 8,233 function mappings produced during the previous analysis.
- 16-byte exact-anchor match rate: 73.4%.
- 32-byte exact-anchor match rate: 61.0%.
- 64-byte exact-anchor match rate: 46.7%.

These figures describe the evidence collected during analysis; they do not by themselves prove a complete matching build.

## Immediate technical target

The next milestone is to turn the candidate NP3F mapping into a reproducible reconstruction input:

1. establish the French ROM layout;
2. validate fragment boundaries;
3. validate section and VRAM metadata;
4. integrate high-confidence function anchors;
5. run the real MIPS/Splat pipeline against the user's local ROM;
6. only then promote candidate data to verified build metadata.

## Native port target

Once a stable NP3F ELF/metadata representation exists:

- feed the native recompilation stage;
- provide a modern runtime;
- separate game simulation cadence from presentation cadence;
- validate 60 Hz game logic while allowing presentation at higher display refresh rates;
- defer online multiplayer until local deterministic behavior is stable.
