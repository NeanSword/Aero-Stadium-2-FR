# Native runtime foundation

This directory is the beginning of the Windows-native runtime layer.

It deliberately starts without a graphics dependency so that the most important rule can be tested first:

**render frequency must not determine simulation frequency.**

The current FixedStepClock uses a rational accumulator instead of a rounded millisecond duration. The default target is 60 simulation ticks per second, while presentation may call the clock at 60, 120, 144, 240 Hz or another rate.

The clock also caps the number of simulation ticks consumed during one render update. This prevents a long stall from turning into an unbounded catch-up loop.

## Build

With CMake 3.20+:

    cmake -S native -B build/native
    cmake --build build/native --config Release
    ctest --test-dir build/native -C Release --output-on-failure

No ROM is needed for this probe.

## What this is not

This is not yet the game runtime and does not render Pokémon Stadium 2.

The next stage is to connect the reconstructed NP3F game state to this timing boundary, then add input/audio/render subsystems behind explicit interfaces.
