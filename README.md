# Aero-Stadium-2-FR

Recompilation statique et portage Windows natif expérimental de **Pokémon Stadium 2 – région française NP3F**.

## État actuel

Le projet a franchi son premier jalon de linkage natif Windows :

- le layout NP3F canonique est stabilisé dans `yamls/fr/splat.yaml` ;
- la passe de symboles Splat produit actuellement **10 911 fonctions** réparties sur **89 sections de code** ;
- N64Recomp génère **214 unités C** pour la passe NP3F actuelle ;
- ces unités compilent en `AeroNP3FGenerated.lib` avec MSVC x64 ;
- l'exécutable Windows `AeroStadium2.exe` se lie avec succès ;
- N64ModernRuntime fournit les services runtime de recompilation ;
- RT64 est intégré comme backend de rendu N64 moderne ;
- SDL2 fournit la première couche manette, jusqu'à quatre ports ;
- les chargements de fragments exécutables par PI DMA sont reliés au système d'overlays du runtime ;
- un runner de test runtime instrumenté conserve stdout/stderr pour les premiers boots réels.

Le prochain jalon est **la validation du premier démarrage runtime**, puis la correction des divergences CPU/RSP/rendu/audio/input observées en exécution.

Un exécutable qui se lie correctement ne signifie pas encore que le jeu est jouable.

## Architecture active

Le chemin principal est désormais :

```text
ROM française NP3F locale
        |
        v
Splat / cartographie NP3F
        |
        v
carte de symboles NP3F
        |
        v
N64Recomp
        |
        v
C généré -> AeroNP3FGenerated.lib
        |
        v
AeroStadium2.exe
        |
        +--> N64ModernRuntime
        +--> RT64
        +--> SDL2
        +--> compatibilité NP3F / overlays
```

Le dossier `native/` reste un laboratoire indépendant pour les contrats de timing et d'hôte natif. Il est toujours testé par CI, mais ce n'est plus le chemin principal de démarrage de Pokémon Stadium 2.

## ROM française requise

La ROM française n'est pas distribuée dans ce dépôt.

Le workflow de reconstruction attend une copie locale légale ici :

```text
baseroms/fr/baserom.z64
```

Consulte [docs/ROM_SETUP_FR.md](docs/ROM_SETUP_FR.md) pour la préparation et la vérification du dump.

Les ROMs, dumps et sorties propriétaires générées localement restent hors du dépôt.

## Workflow Windows actuel

Les scripts Windows n'exigent pas Git local pour télécharger et construire les dépendances épinglées.

Après préparation de la ROM :

```powershell
.\windows\verify_np3f.ps1
.\windows\bootstrap_n64recomp.ps1 -Force
.\windows\bootstrap_n64modernruntime.ps1
.\windows\setup_rt64_windows.ps1
.\windows\run_np3f_recomp_prepare.ps1
.\windows\build_np3f_generated_smoke.ps1 -Clean
.\windows\build_np3f_link_smoke.ps1
```

Une fois `AeroStadium2.exe` créé, le test runtime instrumenté peut être lancé avec :

```powershell
.\windows\run_np3f_runtime_probe.ps1
```

Les logs runtime sont écrits sous :

```text
build/np3f/logs/
```

Voir [windows/README.md](windows/README.md) pour le détail.

## Reconstruction NP3F

La carte ROM NP3F canonique est conservée dans `yamls/fr/splat.yaml`.

- 88/88 en-têtes de fragments correspondent aux signatures `FRAGMENT` observées ;
- 335/335 frontières de code soutenues par des ancres directes NP3E↔NP3F correspondent au layout canonique ;
- 15 frontières supplémentaires ont été vérifiées explicitement ;
- aucune frontière de code ne reste non résolue dans le validateur du layout.

Le fichier `yamls/fr/splat.seed.yaml` est volontairement conservé : il sert à reproduire l'analyse historique des relocations sans appliquer deux fois les deltas.

Les VRAM encore marquées `guessed` dans `config/np3f_fragments.json` restent à valider indépendamment.

Voir [docs/NP3F_MAPPING.md](docs/NP3F_MAPPING.md).

## Réseau

Le multijoueur Internet reste un objectif du projet, mais vient après la stabilisation du runtime local et du déterminisme.

Voir [docs/NETWORKING.md](docs/NETWORKING.md).

## Règles de dépôt

Le dépôt contient uniquement le code, les outils, les métadonnées, les cartes de relocation et la documentation nécessaires au développement.

Il ne doit pas contenir :

- ROM complète ;
- dump propriétaire ;
- cache local de ROM ;
- sorties générées contenant des données propriétaires ;
- exécutables distribués avec des données du jeu.

Voir [docs/REPOSITORY_POLICY.md](docs/REPOSITORY_POLICY.md).

## Licence et ayants droit

Les dépendances et projets upstream restent soumis à leurs licences propres. Pokémon Stadium 2 et ses éléments originaux restent la propriété de leurs ayants droit.
