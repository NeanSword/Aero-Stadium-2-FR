# Plan de portage

## Phase 0 — Fondations

- [x] Créer le dépôt de travail.
- [x] Documenter la cible NP3F.
- [x] Conserver la ROM hors du dépôt.
- [x] Établir un bootstrap Windows reproductible.
- [x] Ajouter la vérification automatique du hash ROM.
- [x] Établir une base de build/reconstruction NP3F.

## Phase 1 — Reconstruction NP3F

- [x] Stabiliser la cartographie ROM des 88 fragments et des frontières de code.
- [ ] Valider indépendamment les VRAM encore marquées `guessed`.
- [x] Produire un YAML NP3F canonique vérifié, avec seed historique séparé.
- [x] Produire une carte de symboles exploitable par N64Recomp.
- [ ] Continuer l'amélioration des noms/données françaises lorsque cela aide le runtime.
- [ ] Mesurer les divergences fonctionnelles restantes par rapport aux références disponibles.
- [ ] Obtenir une reconstruction bit-identique uniquement lorsque cela apporte une valeur réelle au portage.

## Phase 2 — Recompilation native

- [x] Valider le bootstrap N64Recomp Windows sans Git local.
- [x] Générer la sortie C N64Recomp depuis NP3F ROM + symboles Splat.
- [x] Compiler les unités générées en bibliothèque statique MSVC x64.
- [x] Relier la bibliothèque à N64ModernRuntime.
- [x] Produire un premier `AeroStadium2.exe` Windows x64.
- [x] Ajouter les bridges initiaux pour les overlays et PI DMA.
- [ ] Valider le premier boot réel du jeu.

## Phase 3 — Runtime moderne

- [x] Intégrer un premier backend RT64.
- [x] Router les display lists vers RT64.
- [x] Ajouter une première couche manette SDL2.
- [x] Ajouter la vibration lorsque le contrôleur la prend en charge.
- [x] Ajouter un runner de runtime instrumenté et des logs de crash/progression.
- [ ] Valider l'exécution CPU/threading sur une session réelle.
- [ ] Valider les tâches RSP nécessaires.
- [ ] Obtenir le premier affichage de jeu correct.
- [ ] Ajouter/valider le chemin audio.
- [ ] Valider les contrôleurs dans les menus et en jeu.
- [ ] Valider les sauvegardes.
- [ ] Définir et vérifier la cadence de simulation réelle.
- [ ] Ajouter les options d'affichage, d'entrée et de gameplay PC.

## Phase 4 — QA et stabilité

- [ ] Tests de régression.
- [ ] Comparaison de séquences déterministes.
- [ ] Tests de performance.
- [ ] Tests sur Windows réel.
- [ ] Diagnostic des divergences audio/vidéo/input.
- [ ] Tests multi-GPU / pilotes pertinents.

## Phase 5 — Multijoueur

Le multijoueur en ligne reste un objectif de premier plan, mais seulement après stabilisation locale.

- [x] Documenter l'architecture réseau visée.
- [ ] Établir un mode local déterministe reproductible.
- [ ] Définir les données d'état synchronisables.
- [ ] Ajouter le transport P2P hôte-autoritaire.
- [ ] Ajouter les lobbies/codes de session.
- [ ] Ajouter un fallback relay.
- [ ] Ajouter les contrôles de compatibilité de version.
- [ ] Ajouter les hashes d'état et diagnostics de désynchronisation.
- [ ] Étudier le rollback après validation de la synchronisation de base.
