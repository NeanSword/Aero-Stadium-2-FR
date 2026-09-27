# Native runtime architecture

## Architecture active

Le prototype Windows actif est désormais organisé ainsi :

```text
NP3F recompiled C
      |
      v
AeroNP3FGenerated.lib
      |
      v
AeroStadium2.exe
      |
      +--> N64ModernRuntime
      |      +--> threads / services runtime
      |      +--> ROM / overlays
      |      +--> input callbacks
      |
      +--> compatibility NP3F
      |      +--> KSEG1 aliases
      |      +--> PI/EPi DMA bridges
      |      +--> dynamic fragment registration
      |
      +--> RT64
      |      +--> N64 display-list interpretation
      |      +--> native graphics APIs
      |
      +--> SDL2 controllers
```

Il s'agit d'une application Windows native construite par recompilation statique du code MIPS vers C/C++/x64, avec un runtime qui réimplémente les services nécessaires de la plateforme N64.

RT64 interprète toujours les sémantiques graphiques N64 et les display lists ; ce n'est donc pas une suppression de toute couche d'émulation de comportement matériel.

## Overlays

Pokémon Stadium 2 charge de nombreux fragments exécutables via PI DMA.

La couche NP3F détecte les chargements de fragments exécutables et les enregistre auprès du runtime avant que le thread réveillé puisse résoudre l'entrypoint du fragment.

Ce chemin devra être validé sur les transitions réelles du jeu.

## Input

SDL2 fournit actuellement une première implémentation GameController pour jusqu'à quatre ports.

Le mapping couvre les principaux boutons N64, le stick analogique et la vibration lorsqu'elle est disponible.

Le clavier et l'interface de remapping utilisateur restent à ajouter.

## Graphics

RT64 est lié statiquement au prototype et reçoit les display lists depuis le callback renderer de N64ModernRuntime.

Le premier objectif runtime est de vérifier que les tâches graphiques réellement émises par NP3F atteignent correctement RT64.

## Timing

Le laboratoire `native/` conserve un `FixedStepClock` indépendant afin de tester les contrats de timing.

La cadence de simulation finale ne doit pas être déduite de la fréquence de présentation. Elle devra être validée à partir du comportement réel du jeu et du runtime avant toute option HFR.

## Current boundary

Le linker Windows est validé.

Le prochain travail porte sur le comportement à l'exécution : threads, overlays, RSP, rendu, audio, entrées et sauvegardes.
