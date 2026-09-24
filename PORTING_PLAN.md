# Plan de portage

## Phase 0 — Fondations

- [x] Créer le dépôt de travail.
- [x] Documenter la cible NP3F.
- [x] Conserver la ROM hors du dépôt.
- [ ] Établir un bootstrap Windows reproductible.
- [ ] Ajouter la vérification automatique du hash ROM.
- [ ] Établir une base de build/reconstruction NP3F.

## Phase 1 — Reconstruction NP3F

- [ ] Stabiliser la cartographie ROM/VRAM.
- [ ] Produire les YAML NP3F indépendamment des données US.
- [ ] Intégrer progressivement les fonctions et données françaises.
- [ ] Mesurer les divergences fonctionnelles par rapport à l'US.
- [ ] Obtenir une reconstruction NP3F bit-identique lorsque cela est pertinent.

## Phase 2 — Recompilation native

- [ ] Préparer la chaîne N64Recomp.
- [ ] Générer les sorties C/C++ de recompilation.
- [ ] Isoler les interfaces runtime.
- [ ] Produire une première cible Windows x64.

## Phase 3 — Runtime moderne

- [ ] Séparer la cadence de simulation de la cadence de rendu.
- [ ] Garantir une logique de jeu à cadence fixe.
- [ ] Ajouter un pipeline de rendu moderne.
- [ ] Ajouter options d'affichage et d'entrée PC.
- [ ] Vérifier la compatibilité avec la logique originale.

## Phase 4 — QA et stabilité

- [ ] Tests de régression.
- [ ] Comparaison de séquences déterministes.
- [ ] Tests de performance.
- [ ] Tests sur Windows réel.
- [ ] Diagnostic des divergences audio/vidéo/input.

## Phase 5 — Multijoueur

Le multijoueur en ligne sera traité uniquement après stabilisation de la version locale.

- [ ] Définir les données d'état synchronisables.
- [ ] Définir la stratégie de déterminisme.
- [ ] Concevoir la couche transport.
- [ ] Ajouter la gestion de désynchronisation.
