# NP3F texture catalog and pilot gate

The user-supplied `GRAPHICS_1440P_CHARTER.md` governs this phase. Runtime,
renderer code, geometry, audio and input are frozen. The existing graphics
checkpoint is `181c38e63247b8deae48d96ddd49fbf54a63e5f6`; the current local
executable has SHA-256 `AB2AB13B121B24993A060003BC4074AFB7FFB4FF4AC83AD29F213C223B7745E9`.

## Reproduce locally

Use Python with Pillow. Run from the project root:

```powershell
python tools/graphics/test_texture_decoder.py
python tools/graphics/catalog_np3f_textures.py --dump-zip build/rt64-test-userdata/NP3F_texture_dumps.zip --output build/np3f/graphics-workbench/catalog
python tools/graphics/prepare_np3f_texture_pilots.py --catalog build/np3f/graphics-workbench/catalog --output build/np3f/graphics-workbench/pilot-validation
python tools/graphics/catalog_np3f_textures.py --dump-zip build/rt64-test-userdata/NP3F_texture_dumps.zip --output build/np3f/graphics-workbench/catalog --labels build/np3f/graphics-workbench/pilot-validation/labels.json
```

Open `catalog/index.html` locally. It has format/category/size filters, hash
search, paginated previews, and links to decoded originals. No network access
is required. JSON/CSV and contact sheets support reproducible review.

Keep the ZIP, previews, PNG controls, user data and ROM caches local. Do not
publish them. Only tools, tests and documentation belong in Git.

## Source and decoding

Verified ZIP SHA-256: `ea4dd62a6b779c4ab42a9c1f9ffaf03b60345b144123235febf9e4045d54f173`.
11,269 entries / 2,817 v5 textures, with all four source components present.
RGBA16 2,474; IA8 228; I4 66; I8 33; IA4 10; IA16 4; RGBA32 2.

TMEM decoding follows the locally built RT64 implementation:
`src/shaders/TextureDecoder.hlsli`, `Formats.hlsli`, and the decode constants
in `src/render/rt64_texture_cache.cpp`. It handles the 64-bit TMEM start and
stride units, odd-row word swaps, 4 KiB addressing, RGBA32 split banks and
the original I/IA channel meanings. I alpha equals intensity; IA stores a
separate alpha. No color grading or alpha cleanup is applied to raw previews.

Five synthetic tests cover known channel values, nibble order, odd-row
swapping, nonzero starts, TMEM wrapping, RGBA32 split banks and rejection of
unsupported palettes. Independent linear RDRAM checks match all 2,149
applicable records. The other 668 use special loads, pre-interleaved rows,
unaligned source addresses or unsupported direct-linear layouts; this is
not a claim that their source is corrupted. Their previews use TMEM.

Raw and nearest previews cannot be overwritten with different pixels.
Re-running against a different source ZIP requires a new output directory.

## Classification evidence

77 glyphs (24x20, including accents/symbols and blank spacing) and all 245
40x40 icon previews have been visually inspected. Category assignments are
recorded as preview evidence, not proof of scene-specific hash use.

**56x26 and 56x28 are not automatically text labels.** The contact sheets
show cropped rendered Pokemon portraits, often with many variants/states.
These need reconstruction and scene mapping before any retouching. Do not
generate a mass UI pack based on their dimensions. Keep unreviewed hashes
`unknown`. The 1,601 16x16 entries remain deferred.

Phase manifests separate candidates from production approval. Phase 3 and
4 deliberately have empty production lists until model/stadium mapping is
demonstrated. Re-running pilot preparation recreates pending validation
records; archive reviewed results separately before regenerating.

## Four technical control pilots

| Role | Hash | Source | Control export | Meaning |
|---|---|---|---|---|
| Text | `02f9b8d67777bf16` | IA8 24x20 | 96x80 | L glyph |
| RGBA | `82dbc094ea0f8ac0` | RGBA16 40x40 | 160x160 | Pikachu icon |
| I/IA | `951448e72cb575fc` | I4 112x36 | 448x144 | COMBAT! menu strip |
| Repeat | `369e34f9da3e0131` | I4 128x64 | 512x256 | repeating Poké Ball motif |

These files reuse the exact nearest-neighbor previews. **They are controls,
not HD artwork.** Four PNGs plus an RT64 configuration v3 / hash v5 database
exercise the existing replacement loader. Paths omit extensions; preload
is used for these tiny controls. I/IA exports remain neutral grayscale and
retain their original alpha values.

Set `texture_pack` to the absolute `control-pack` directory in a separate
test data directory, with `texture_replacements=true`. Keep all other
settings identical to the baseline. The production graphics.ini remains
unchanged. The existing runtime accepts `--rom`, `--data-dir`, `--seconds`.

Loading the database does **not** prove that each hash was used. Confirm
each in-scene match, UV/orientation, alpha, and repetition at 1440p; run the
1080p check; retain comparable screenshots. Only then mark the pilot gate
passed. No mass production is authorized by the generated manifests.

## Runtime observation during baseline (2026-09-28)

Before enabling replacements, the visible baseline reached the menus,
combat rule selection and team preview, then stopped before combat with:

```text
[fragment-map] slot=0 rom=0015E8E0 ram=8025CED0 size=00006790
[fragment-map] No compiled section for slot=239 ram=80263870 size=0000E4F0
Failed to find function at 0x80263890
```

This is a baseline runtime limitation, not caused by this pack. It is
recorded without changing runtime code under the charter. It prevents
claiming complete combat/stadium validation. UI-only testing can continue.

The subsequent 1440p pilot run reports `Texture pack HD: charge` (this is
the renderer's generic log label, not a quality claim). It reaches combat
rule selection and then the same missing function, without a texture load
error. Database loading is verified; the individual pilot checks and
before/after comparisons remain pending. No pilot is marked accepted and
no mass artwork production has begun.
