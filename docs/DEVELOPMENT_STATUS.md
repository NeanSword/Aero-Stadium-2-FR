# Development status

## Jalon atteint : premier EXE Windows lié

La chaîne NP3F actuelle atteint désormais un exécutable Windows x64 lié avec succès.

État validé :

- layout canonique NP3F dans `yamls/fr/splat.yaml` ;
- 88 fragments exécutables cartographiés ;
- extraction Splat reproductible ;
- carte de symboles courante de 10 911 fonctions ;
- 89 sections de code avec fonctions ;
- génération N64Recomp de 214 unités C ;
- compilation de `AeroNP3FGenerated.lib` ;
- linkage avec N64ModernRuntime ;
- linkage avec RT64 ;
- linkage avec SDL2 ;
- création de `AeroStadium2.exe`.

## Runtime actuellement branché

Le prototype Windows lié comprend déjà :

- sélection et validation de la ROM NP3F ;
- cache local de ROM géré par N64ModernRuntime ;
- fenêtre Win32 de probe ;
- initialisation SDL2 des manettes ;
- mapping N64 de base pour jusqu'à quatre contrôleurs ;
- support rumble lorsque disponible ;
- renderer RT64 ;
- routage des display lists ;
- bridges PI/EPi DMA ;
- détection et enregistrement des fragments exécutables chargés dynamiquement ;
- logs CPU/RSP/display-list ;
- watchdog de progression ;
- résolution d'adresses via le fichier MAP lors des diagnostics de crash.

## Ce qui n'est pas encore validé

Le succès du linker ne constitue pas encore un port jouable.

À valider maintenant :

1. premier démarrage réel de l'entrypoint NP3F ;
2. comportement des threads et overlays ;
3. tâches RSP rencontrées en pratique ;
4. premières display lists RT64 ;
5. chemin audio ;
6. contrôleurs en jeu ;
7. stabilité des accès mémoire ;
8. transitions entre menus/modes ;
9. sauvegardes ;
10. déterminisme suffisant pour préparer le réseau.

## Analyse NP3F encore conservée

Les scripts de relocation et les seeds historiques sont conservés volontairement.

Ils ne sont plus dans le chemin normal du build, mais restent nécessaires pour reproduire l'analyse ou diagnostiquer un futur écart de mapping.

## Objectifs suivants

Après validation du premier boot :

- remplacer les shims de bootstrap par des comportements runtime précis lorsque nécessaire ;
- durcir le renderer RT64 ;
- compléter audio/input/sauvegardes ;
- ajouter les menus et options PC ;
- stabiliser une exécution locale déterministe ;
- seulement ensuite activer les jalons réseau décrits dans [NETWORKING.md](NETWORKING.md).
