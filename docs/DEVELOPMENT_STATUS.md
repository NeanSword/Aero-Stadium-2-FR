# Development status

## Jalon atteint : introduction, écran titre et démonstration de combat

L'exécutable Windows x64 affiche ces scènes via RT64. Certaines textures sont noires ; le port n'est pas encore validé comme jouable. Le journal [LastProgressLogs](../LastProgressLogs.md) contient les versions et les diagnostics actuels.

État validé :

- layout canonique NP3F dans `yamls/fr/splat.yaml` ;
- 88 fragments exécutables cartographiés ;
- extraction Splat reproductible ;
- carte de symboles courante de 11 050 fonctions ;
- 89 sections de code avec fonctions ;
- génération N64Recomp de 217 unités C ;
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

1. parcours interactif des menus et combat complet ;
2. stabilité des threads et overlays dans les autres modes ;
3. tâches RSP dans les scènes suivantes (audio et type 4 fonctionnent dans l'introduction) ;
4. correction des textures noires dans RT64 ;
5. chemin audio ;
6. contrôleurs en jeu ;
7. stabilité des accès mémoire ;
8. transitions entre menus/modes ;
9. sauvegardes ;
10. déterminisme suffisant pour préparer le réseau.

## Analyse NP3F encore conservée

Les scripts de relocation et les seeds historiques sont conservés volontairement.

L'adaptateur add_np3f_relocations.py fait partie du build natif : les 116 174 relocations entre fragments sont nécessaires à l'exécution. Les scripts historiques d'analyse restent disponibles pour diagnostiquer les écarts de mapping.

## Objectifs suivants

Après validation du premier boot :

- remplacer les shims de bootstrap par des comportements runtime précis lorsque nécessaire ;
- durcir le renderer RT64 ;
- compléter audio/input/sauvegardes ;
- ajouter les menus et options PC ;
- stabiliser une exécution locale déterministe ;
- seulement ensuite activer les jalons réseau décrits dans [NETWORKING.md](NETWORKING.md).
