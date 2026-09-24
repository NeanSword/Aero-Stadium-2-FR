# Native runtime architecture

The native port is structured around an explicit separation:

    Wall clock
        |
        v
    Fixed-step simulation (target 60 Hz)
        |
        +----> game state
        |
        +----> audio state
        |
        +----> render snapshot
                         |
                         v
                   presentation
                   (independent FPS)

The fixed-step layer must remain deterministic and must not consult the renderer's frame frequency to decide how much game logic to execute.

The current implementation is intentionally dependency-free. This lets the timing contract be tested before bringing in a renderer or platform backend.

The target architecture will later place the reconstructed NP3F code behind this boundary and use the native runtime to provide Windows-specific services.

The 60 Hz value is a working target matching the intended original cadence; it should be validated against the actual game timing before being treated as an immutable engine invariant.
