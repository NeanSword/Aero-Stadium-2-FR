# Networking target

Aero-Stadium-2-FR must support Internet multiplayer in addition to the original local multiplayer behavior.

## Product goal

The networking layer must preserve the original game simulation rather than stream video from another machine.

Target user flow:

1. open **Réseau / Multijoueur en ligne**;
2. create a private or public lobby;
3. invite another player or share a short lobby code;
4. validate that every participant runs a compatible Aero Stadium 2 build and the expected NP3F game data;
5. launch the original multiplayer mode with remote players mapped to N64 controller slots.

## Preferred architecture

The initial target is **host-authoritative peer-to-peer**:

- one player owns the session and advances the authoritative simulation;
- players exchange controller inputs and synchronization data rather than video;
- direct P2P is preferred when connectivity allows it;
- relay fallback is used when NAT/firewalls prevent a direct path;
- a forced-relay privacy option should be available so peers do not need to learn each other's public IP address.

Epic Online Services (EOS) is the current preferred transport/service candidate because it provides P2P connectivity, NAT traversal/relay support, sessions and lobbies without requiring Aero Stadium 2 to operate a permanent dedicated game server.

The networking backend must remain isolated behind an Aero-specific interface so another provider or a self-hosted backend can be added later.

## Determinism and synchronization

Networking is intentionally scheduled after the local native runtime is deterministic enough to test reliably.

The netcode should include:

- deterministic random seed synchronization;
- controller input frames tagged with simulation frame numbers;
- configurable input delay;
- periodic lightweight state hashes to detect divergence;
- pause/resume handling when a peer temporarily loses connectivity;
- version/protocol compatibility checks before a match;
- clean host departure and disconnect handling.

Rollback may be evaluated after basic lockstep/input-delay netplay is stable. It should not be assumed until the cost of capturing and restoring the recompiled game's state is measured.

## Security and privacy

Do not expose ROM contents through the network layer.

Only metadata needed for compatibility validation should be exchanged, such as:

- Aero Stadium 2 protocol/build version;
- game region/version identifier;
- non-reversible compatibility hashes where appropriate.

A relay-only mode should be supported for players who do not want direct peer connectivity.

## Dedicated servers

A permanently hosted authoritative gameplay server is not required for the first Internet multiplayer milestone.

If competitive or public matchmaking later needs stronger authority, a dedicated-server mode can be added without replacing the P2P implementation.

## Milestones

1. deterministic two-instance local test harness;
2. controller-input synchronization over localhost;
3. LAN multiplayer;
4. Internet P2P transport;
5. lobby/session discovery and invite flow;
6. relay fallback and relay-only privacy mode;
7. disconnect/reconnect handling;
8. latency diagnostics and configurable input delay;
9. optional rollback feasibility prototype;
10. optional public matchmaking / dedicated authority.
