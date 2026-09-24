# Windows workflow

The project is being developed with Windows as the user-facing platform.

The upstream pret/pokestadiumgs Makefile currently rejects native Windows builds. Aero-Stadium-2-FR therefore keeps its own Windows-oriented workflow for the analysis and native runtime layers.

## ROM check

Place your local NP3F dump at:

    baseroms\fr\baserom.z64

Then:

    .\windows\verify_np3f.ps1

The verifier accepts the common N64 byte orders and normalizes them before checking the NP3F identity.

## Candidate YAML check

To validate a local Splat-style candidate YAML against the 88-fragment catalog:

    .\windows\validate_np3f_yaml.ps1 -CandidateYaml "C:\chemin\vers\candidate.yaml"

## NP3F extraction test

Once the ROM and candidate YAML are ready:

    .\windows\run_np3f_extract.ps1 -CandidateYaml "C:\chemin\vers\candidate.yaml"

The script:

1. verifies the NP3F ROM;
2. validates the fragment map;
3. copies the candidate YAML unchanged into the repository root as a local working file;
4. runs Splat from the repository root so relative ROM paths resolve correctly;
5. captures stdout/stderr in build\NP3F_SPLAT_EXTRACT.log.

Use -DisassembleAll to ask Splat for full disassembly during the test.

The local candidate file and generated build output are ignored by Git.

## What this means

A successful extraction proves that the candidate YAML is syntactically usable by Splat with your local ROM. It does not yet prove a complete matching reconstruction or a native Windows executable.
