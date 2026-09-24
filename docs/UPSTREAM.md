# Upstream reference

The reconstruction base used by this project is the public repository:

- https://github.com/pret/pokestadiumgs

Reference commit pinned for the current work:

`c0e10f23d90cc4f335b654711f13e53c2c07323b`

That commit is the July 10, 2026 upstream state that contains the US/JP support used during the NP3F analysis.

The upstream source is kept as a Git submodule rather than copied into this repository. This keeps the project boundary explicit and avoids silently duplicating third-party source.

The French NP3F work belongs in this repository as project-specific code, configuration, tests, and analysis.
