# Aero-Stadium-2-FR

Projet de reconstruction et de portage Windows natif de **Pokémon Stadium 2 – région française NP3F**.

## Objectif

Construire progressivement une version PC native à partir de la reconstruction N64 et des travaux de reverse engineering associés, puis préparer :

- une exécution native Windows x64 ;
- un rendu moderne avec fréquence d'affichage indépendante de la logique de jeu ;
- la localisation française NP3F ;
- des outils de développement et de débogage reproductibles sous Windows ;
- à terme, une architecture permettant d'étudier le multijoueur en ligne.

## Principe de stockage

La ROM originale, les dumps complets et les fichiers binaires extraits du jeu ne sont **pas** stockés dans ce dépôt.

Le dépôt contient le code, les outils, la documentation, les métadonnées de vérification et les scripts nécessaires pour reproduire les étapes avec une copie locale légitime de la ROM.

## État actuel

Le point de départ technique est le projet public `pret/pokestadiumgs`, une reconstruction WIP de Pokémon Stadium 2 pour les régions US/JP.

La ROM française étudiée localement est la région **NP3F**. Les analyses déjà réalisées montrent que les bases VRAM des 88 fragments étudiés restent alignées avec l'US, tandis que les offsets ROM français se décalent par plages cumulatives.

## Organisation

```
docs/       Notes techniques et décisions
tools/      Outils reproductibles
windows/    Workflow Windows
config/     Métadonnées du projet
```

## Règle de travail

GitHub est la source de vérité du projet. Les archives ZIP ne sont créées que lorsqu'un transfert vers une machine de test Windows est réellement nécessaire.

## Avertissement

Pokémon Stadium 2 et ses éléments originaux restent la propriété de leurs ayants droit. Ce dépôt vise les travaux de développement et de reverse engineering autour d'une copie fournie par l'utilisateur.
