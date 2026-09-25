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
- [ ] Intégrer progressivement les fonctions et données françaises.
- [ ] Mesurer les divergences fonctionnelles par rapport à l'US.
- [ ] Obtenir une reconstruction NP3F bit-identique lorsque cela est pertinent.

## Phase 2 — Recompilation native

- [ ] Valider localement le bootstrap N64Recomp sans Git.
- [ ] Générer la première sortie C N64Recomp à partir de NP3F ROM + symboles Splat.
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
