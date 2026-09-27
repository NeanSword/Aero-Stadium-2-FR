# Native runtime foundation

Ce dossier reste le **laboratoire autonome de timing/hôte natif** du projet.

Il est volontairement petit, sans dépendance graphique, et continue d'être compilé et testé par GitHub Actions. Son rôle est de valider des contrats génériques — notamment la séparation entre cadence de simulation et cadence de présentation — sans avoir besoin de la ROM.

## Important : ce n'est plus le chemin principal du jeu

Le runtime actif de la recompilation NP3F se trouve désormais dans :

```text
cmake/np3f_link_smoke/
```

et relie :

- le C NP3F généré par N64Recomp ;
- N64ModernRuntime ;
- RT64 ;
- SDL2 ;
- les bridges de compatibilité propres à Pokémon Stadium 2 FR.

Le dossier `native/` n'est donc pas obsolète, mais il ne faut pas le confondre avec `AeroStadium2.exe`.

## FixedStepClock

Le `FixedStepClock` utilise un accumulateur rationnel plutôt qu'une durée entière arrondie en millisecondes.

Le laboratoire peut tester une simulation fixe avec une présentation appelée à 60, 120, 144, 240 Hz ou une autre fréquence.

Il limite aussi le nombre de ticks consommés lors d'une seule mise à jour afin d'éviter une boucle de rattrapage non bornée après un long stall.

La cadence exacte à retenir pour la logique du jeu doit rester fondée sur le comportement runtime observé ; elle ne doit pas être imposée par la fréquence de rendu.

## Build

Avec CMake 3.20+ :

```powershell
cmake -S native -B build/native
cmake --build build/native --config Release
ctest --test-dir build/native -C Release --output-on-failure
```

Aucune ROM n'est nécessaire pour ces tests.

## Conservation

Ce dossier est volontairement conservé car :

- il possède encore des tests CI actifs ;
- il isole les contrats de timing des dépendances N64 ;
- il peut servir de banc d'essai pour de futurs changements de cadence ou d'hôte.
