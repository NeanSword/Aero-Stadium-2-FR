# Windows workflow

Windows x64 est la plateforme utilisateur principale d'Aero-Stadium-2-FR.

Le workflow actif ne cherche plus à compiler directement le Makefile upstream de pret/pokestadiumgs. Il reconstruit les métadonnées NP3F, génère du C avec N64Recomp, compile une bibliothèque statique puis la lie à N64ModernRuntime, RT64 et SDL2.

## 1. ROM NP3F

Place la copie locale légale ici :

```text
baseroms\fr\baserom.z64
```

Puis vérifie-la :

```powershell
.\windows\verify_np3f.ps1
```

Le vérificateur accepte les ordres d'octets N64 courants et normalise le dump avant validation.

## 2. Dépendances natives

Le projet fournit des bootstraps Windows sans Git local pour les dépendances épinglées :

```powershell
.\windows\bootstrap_n64recomp.ps1 -Force
.\windows\bootstrap_n64modernruntime.ps1
.\windows\setup_rt64_windows.ps1
```

Les sources et builds téléchargés sont placés sous `.local/`, qui reste hors du dépôt.

## 3. Génération NP3F

La passe canonique est :

```powershell
.\windows\run_np3f_recomp_prepare.ps1
```

Après une extraction propre déjà validée, `-SkipExtract` peut réutiliser le cache Splat :

```powershell
.\windows\run_np3f_recomp_prepare.ps1 -SkipExtract
```

Le script valide notamment :

- la révision du fichier `recomp/np3f.toml` ;
- la provenance du N64Recomp standalone ;
- l'absence d'anciens hooks Aero parasites ;
- la carte de symboles générée ;
- la sortie finale N64Recomp.

La passe actuelle produit 10 911 fonctions et 214 unités C.

## 4. Compilation du C généré

```powershell
.\windows\build_np3f_generated_smoke.ps1 -Clean
```

Cette étape compile toutes les unités `funcs_*.c` ainsi que `lookup.cpp` dans :

```text
AeroNP3FGenerated.lib
```

Elle utilise le même `recomp.h` que le N64ModernRuntime épinglé afin d'éviter les divergences ABI.

## 5. Link Windows natif

```powershell
.\windows\build_np3f_link_smoke.ps1
```

Le premier linkage Windows x64 est maintenant validé. La sortie actuelle est :

```text
build\np3f\link-smoke-prebuilt-vs2022-x64\bin\AeroStadium2.exe
```

Le dossier de sortie contient aussi les DLL nécessaires à RT64/SDL2.

Pour les rebuilds incrémentaux, évite `-Clean` sur le link final sauf nécessité : RT64 est coûteux à reconstruire et peut être réutilisé.

## 6. Premier test runtime

Le runner recommandé est :

```powershell
.\windows\run_np3f_runtime_probe.ps1
```

Il :

1. vérifie la présence de l'EXE et des DLL runtime ;
2. lance `AeroStadium2.exe` ;
3. laisse apparaître la sélection de ROM NP3F si le cache local n'est pas encore initialisé ;
4. conserve stdout/stderr ;
5. enregistre un log combiné.

Logs :

```text
build\np3f\logs\NP3F_RUNTIME.log
build\np3f\logs\NP3F_RUNTIME.stdout.log
build\np3f\logs\NP3F_RUNTIME.stderr.log
```

Pour le premier essai manette, branche-la avant le lancement.

## Outils historiques d'analyse

Les scripts de relocation, de comparaison de sous-segments et de validation des candidats Splat restent volontairement présents.

Ils ne font plus partie du chemin normal de build, mais ils restent utiles pour reproduire l'analyse NP3F ou diagnostiquer un futur problème de mapping. Ils ne doivent donc pas être supprimés tant que la reconstruction n'est pas définitivement figée.

## État du jalon

Validé :

- extraction NP3F canonique ;
- génération N64Recomp ;
- compilation des 214 unités générées ;
- liaison N64ModernRuntime ;
- liaison RT64 ;
- liaison SDL2 ;
- création de `AeroStadium2.exe`.

En cours :

- premier boot runtime ;
- validation CPU/RSP/overlays ;
- affichage RT64 réel ;
- audio ;
- entrée en jeu et navigation ;
- stabilité.
