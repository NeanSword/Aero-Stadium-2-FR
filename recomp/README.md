# Native recompilation boundary

Aero-Stadium-2-FR utilise N64Recomp pour transformer la carte de fonctions NP3F en code C natif compilable sur Windows x64.

## Dépendances épinglées

Les dépendances principales restent explicitement épinglées :

- N64Recomp ;
- N64ModernRuntime ;
- RT64 ;
- RecompFrontend comme référence upstream.

Le workflow Windows peut télécharger les sources nécessaires sans Git local dans `.local/`.

## Chemin actif

```text
yamls/fr/splat.yaml
        |
        v
Splat --disassemble-all
        |
        v
tools/recomp/generate_np3f_symbols.py
        |
        +--> build/np3f/recomp/np3f.syms.toml
        |
        v
recomp/np3f.toml
        |
        v
N64Recomp
        |
        v
generated/recomp/np3f/
        |
        v
AeroNP3FGenerated.lib
        |
        v
AeroStadium2.exe
```

La passe actuelle contient :

- **10 911 fonctions** dans la carte de symboles ;
- **89 sections** comportant des fonctions ;
- **214 unités C générées** ;
- un `lookup.cpp` généré ;
- une bibliothèque statique MSVC `AeroNP3FGenerated.lib`.

Le premier link Windows x64 de `AeroStadium2.exe` est désormais réussi.

## Configuration canonique

Le fichier :

```text
recomp/np3f.toml
```

est la configuration canonique de génération.

Le runner `windows/run_np3f_recomp_prepare.ps1` vérifie sa révision avant d'exécuter N64Recomp. Il vérifie aussi la provenance du binaire N64Recomp standalone et refuse les anciens hooks Aero parasites qui ont existé pendant les premières expérimentations.

## ABI du code généré

Le smoke build compile le C NP3F avec le `recomp.h` provenant du N64Recomp embarqué dans la version épinglée de N64ModernRuntime.

Cette règle est volontaire : le code généré et le runtime final doivent partager la même ABI.

## Compatibilité runtime NP3F

La couche de compatibilité actuelle couvre notamment :

- les alias KSEG1 de la RDRAM ;
- certains accès MMIO utilisés pendant le bootstrap ;
- des bridges PI/EPi DMA ;
- l'enregistrement des fragments exécutables chargés dynamiquement ;
- le lookup des fonctions d'overlays ;
- quelques comportements libultra non encore couverts directement par le runtime upstream.

Ces bridges sont des étapes de portage ciblées. Ils doivent être remplacés ou resserrés lorsque le comportement réel du jeu est mieux caractérisé.

## Commandes Windows

Génération :

```powershell
.\windows\run_np3f_recomp_prepare.ps1
```

Compilation des unités générées :

```powershell
.\windows\build_np3f_generated_smoke.ps1 -Clean
```

Link final :

```powershell
.\windows\build_np3f_link_smoke.ps1
```

Test runtime :

```powershell
.\windows\run_np3f_runtime_probe.ps1
```

## Statut

La frontière « ROM NP3F -> C généré -> bibliothèque statique -> EXE Windows » est maintenant établie.

La priorité n'est plus de prouver que la chaîne peut linker, mais de valider le comportement du jeu au runtime et de corriger les divergences observées.
