# NP3F title-screen HD texture mapping

The RT64 texture dump captured from the French NP3F runtime has been decoded
and the title screen has been mapped without committing any copyrighted game
texture data.

## Identified title assets

- background: **320x240**, stored as 300 sequential 16x16 RGBA16 tiles;
- Pokémon Stadium 2 logo: **376x196**, stored as 49 sequential 376x4 RGBA16 strips;
- legal text: **416x64**, stored as 8 sequential 416x8 IA8 strips;
- `APPUYER SUR START`: 200x20 IA8;
- Dolby Surround mark: 88x34 IA8;
- `Expansion Pak N64 détecté`: 216x18 IA8.

The title background is detected from RT64 hash-version-5 anchor
`dd04fe928a08d2c1` and the original RDRAM layout observed in the NP3F dump.

## Development pack builder

`tools/graphics/build_np3f_title_pack_from_dump.py` reads the original RT64
dump ZIP and discovers the exact hashes automatically. This avoids storing a
large list of runtime hashes manually.

For the current 1440p preset, prepare 6x master images:

- background: 1920x1440;
- logo: 2256x1176;
- legal text: 2496x384;
- press start: 1200x120;
- Dolby mark: 528x204;
- Expansion Pak message: 1296x108.

Example:

```powershell
.\.venv\Scripts\python.exe .\tools\graphics\build_np3f_title_pack_from_dump.py `
  --dump-zip .\NP3F_texture_dumps.zip `
  --background .\hd_sources\title_background.png `
  --logo .\hd_sources\title_logo.png `
  --legal-text .\hd_sources\title_legal.png `
  --press-start .\hd_sources\press_start.png `
  --dolby .\hd_sources\dolby.png `
  --expansion-pak .\hd_sources\expansion_pak.png
```

The result is written to `build/np3f/hd_texture_pack` and contains
`rt64.json` plus all replacement PNGs.

For development, point `graphics.ini` at the generated directory. PNG is
supported by RT64 for development. A distributable pack should later use DDS
with mipmaps and RT64's texture packer to create an RTZ package.

## Validation performed

The builder was tested against the uploaded NP3F dump. With reconstructed 1x
title background, logo and legal-text masters it discovered:

- 300 background textures;
- 49 logo strips;
- 8 legal-text strips;
- 357 RT64 entries total.

This verifies the hash discovery and slicing layout before HD artwork is
introduced.
