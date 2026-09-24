# Windows workflow

The project is being developed with Windows as the user-facing platform.

The upstream pret/pokestadiumgs Makefile currently rejects native Windows builds. We therefore keep the original upstream reconstruction model as a reference while building a separate Windows-oriented workflow for this project.

## First local check

From PowerShell at the repository root:

    .\windows\verify_np3f.ps1

This only validates the locally supplied NP3F ROM. It does not upload the ROM anywhere.

## Development rule

Generated extraction/build output stays local unless a particular generated source file is intentionally committed as part of the project.
