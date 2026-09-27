# LastProgressLogs — Aero-Stadium-2-FR

Dernière mise à jour : **27 septembre 2026, 04:22 Europe/Paris**, session locale Codex/Work.

## Point de reprise actuel

**Le blocage à 61 listes graphiques est dépassé dans la version locale d’intégration.** Ne pas repartir de ce diagnostic sans vérifier quelle version est exécutée.

- L’exécutable Windows natif compile et entre dans le jeu.
- Les fragments de l’introduction et leurs modèles sont chargés.
- Un second blocage vers 710 listes graphiques a été identifié et corrigé : deux boucles attendant un compteur audio empêchaient le scheduler coopératif de traiter ses événements.
- Un test de 40 secondes avec le RSP encore factice a terminé avec **1 140 listes graphiques achevées**, dernière liste vieille de 31 ms, et chargement du fragment de l’écran suivant.
- Le vrai microcode audio NP3F et une sortie audio SDL ont ensuite été intégrés localement. Ce test avance jusqu’au chargement du module suivant, puis s’arrête sur **une tâche RSP type 4, ucode 0x80085390**, encore non prise en charge.
- L’image visible, le son audible, les menus et un combat complet restent à valider. Les compteurs de rendu ne constituent pas à eux seuls une preuve de jouabilité.

**Dernière erreur réelle :**
```text
[audio-rsp] Unsupported task type=4 ucode=80085390
No registered RSP ucode for 4 (returned `nullptr`)
Failed to execute task type: 4
```

## Où se trouve le travail

Dossier de compilation/test autorisé par l’utilisateur :
```text
C:\Users\dofus\Downloads\PokemonStadium2_FR_Windows_Next\pokestadiumgs-fr
```

Exécutable :
```text
build/np3f/link-smoke-prebuilt-vs2022-x64/bin/AeroStadium2.exe
```

Ce dossier de téléchargements n’est pas un checkout Git. Les modifications sont préparées dans :
```text
C:\Users\dofus\.codex\.chatgpt-projects\g-p-6ab58e3c969481918cad038344c3d218\Aero-Stadium-2-integration
```
Branche locale : **codex/native-rt64-integration**, initialement créée depuis `5a476e82b141a640fe8770a384e3fc670aaba5a5`.

**Checkpoint de sources publié : [a9bd5cae](https://github.com/NeanSword/Aero-Stadium-2-FR/commit/a9bd5cae42a424e23e5d9c6f358b1bf0ec94cba6)** sur `codex/native-rt64-integration`. Son arbre est identique au commit local `6219b8c` (arbre `f58c6366e83eae30605076538c88a6c55970488c`). L’intégration des changements récents de main est en cours. Un téléchargement de main ne contient pas encore ces corrections.

**Attention à l’état du dossier Downloads au 27/09 à 04:19 : plusieurs sources et l’exécutable ont été remplacés entre 00:36 et 04:06 par les versions du travail effectué sur main. Les tests du 26/09 listés ici sont ceux du checkpoint, pas ceux de l’exécutable actuellement sur disque.** Préserver ces nouveaux fichiers/logs avant de déployer la version réunie. Les derniers logs de main se trouvent dans `build/np3f/logs/NP3F_RUNTIME.*.log` (04:06). Aucun processus AeroStadium2 n’était encore actif lors de cette inspection.

Le dépôt distant main a été relu et récupéré jusqu’à `6f8870ebb77cff6383659e4446c8abe211c13b7a`. Il contient d’autres travaux récents (manette SDL, génération RSP audio, diagnostics des queues, scripts de build). Il faut les rapprocher du travail local sans écraser les corrections testées ni réintroduire le mauvais enregistrement des fragments.

Un ancien checkout `Aero-Stadium-2-FR` sous le même miroir contient aussi des modifications antérieures non commitées : le préserver. Les fichiers `sources/` du miroir ChatGPT sont des références en lecture seule.

## Corrections locales vérifiées

### Fonctions, fragments et relocation

- Générateur local `2026-09-26.1` : **11 047 fonctions**, **89 sections**, **217 unités C**.
- Injection de **131 trampolines J/NOP** de fragments, dont la table d’exports du fragment 26.
- **11 entrées de fonctions** restaurées à partir de plages vérifiées par SHA-256 : helpers audio assembleur, `guRotateRPY`, `osAiSetNextBuffer`.
- **116 174 relocations** reconstruites dans 88 fragments à partir des tables présentes dans la ROM.
- Adaptation du lecteur de symboles de N64Recomp pour les relocations vers une autre section.
- L’enregistrement natif des fragments suit maintenant le registre du jeu : hooks `func_80002440` / `func_8000251C`. Un petit DMA de 0x1000 octets ne suffit pas à enregistrer un fragment entier ; c’était la cause d’un ancien appel vers du code périmé.
- Le fragment 28 utilise **0x8FE00000** dans le catalogue et le YAML local.
- Les modèles chargés dans le slot 239 contiennent un petit accesseur MIPS. Une traduction native n’accepte que son motif exact de sept instructions, avec contrôle des bornes et de la signature FRAGMENT.
- Les quatre vérifications de cartouche gardent leurs comparaisons originales ; seules leurs lectures directes PI/ROM passent par le bridge hôte.

Fichiers principaux :
```text
tools/recomp/generate_np3f_symbols.py
tools/recomp/add_np3f_relocations.py
tools/recomp/patch_n64recomp_symbols.py
tools/recomp/test_native_adapters.py
config/np3f_recomp_function_overrides.json
recomp/np3f.toml
cmake/np3f_generated_smoke/aero_platform.h
cmake/np3f_generated_smoke/np3f_memory_compat.h
cmake/np3f_link_smoke/np3f_register_overlays.cpp
cmake/np3f_link_smoke/np3f_asset_entry.cpp
cmake/np3f_link_smoke/np3f_asset_entry_test.cpp
```

### Blocage de transition identifié et corrigé

Le relevé de piles natives a trouvé le thread du jeu dans :
```text
func_80035594 -> func_80065850 -> func_80065AB8 -> func_80065050
```
Deux attentes à `0x80035614` et `0x80035660` attendent l’évolution de `D_8009498C`, modifiée par le thread audio. Le moteur natif ne traite ses messages externes qu’aux points de coopération.

Les hooks appellent **yield_self_1ms via aero_poll_events**, sans modifier le compteur ni supprimer les tests de la ROM. La transition reprend. Aucun changement global de la sémantique NOBLOCK n’a été appliqué.

### Audio, saisie et diagnostics actuels

- Microcode audio local généré dans `generated/recomp/np3f/audio_rsp.cpp`, fonction `np3f_audio_rsp`.
- Configuration : `recomp/np3f_audio.toml`, ROM 0x1060, taille 0x1000, IMEM 0x04001000.
- Les 24 entrées indirectes viennent de ROM 0x87C20..0x87C50.
- Callback RSP local : type 2 / ucode 0x80000460 accepté ; autre programme refusé explicitement. Le type 4 est le prochain travail.
- `osAiSetNextBuffer` est identifié par signature et routé vers le runtime. Le bridge MMIO ajouté entre-temps sur main constitue une autre approche : éviter de cumuler deux soumissions du même buffer.
- Sortie audio SDL stéréo, remise dans l’ordre des deux échantillons de chaque mot RDRAM ; ouverture à 48 kHz puis 32 kHz observée. Son audible non encore vérifié.
- Clavier local ajouté au probe : Entrée=Start, X=A, C=B, Z=Z, Q/E=L/R, flèches=croix, WASD=stick, IJKL=boutons C. À tester et à intégrer avec la manette SDL ajoutée sur main.
- Le test borné rapporte le nombre de listes **achevées** et l’âge de la dernière. Il sort avec code 24 si le rendu est arrêté depuis 5 secondes.
- En cas d’arrêt, un relevé des piles natives des seuls threads invités aide à identifier la boucle ou l’attente.
- Les dumps de modèles sont désormais optionnels via `AERO_DUMP_FRAGMENTS`. Ne jamais les publier.

## Résultats de tests et logs locaux

Sous le dossier de téléchargements :

| Dossier dans build/np3f/probes/ | Résultat |
| --- | --- |
| 20260926-225514-707 | 20 s, introduction active ; ancien critère de réussite trop faible |
| 20260926-225712-641 | 120 s, arrêt vers 710 listes ; ancien test retournait à tort 0 |
| 20260926-230057-864 | Nouveau test : code 24, 709 listes ; piles identifiant func_80035594 |
| 20260926-230416-897 | Après coopération des deux boucles : 40 s, code 0, 1 140 listes, progression active |
| 20260926-230848-205 | RSP audio réel + SDL : arrêt explicite sur RSP type 4 / 0x80085390 |

Autres contrôles réussis :
- CTest `asset_entry` : exactitude de l’accesseur, branche a0 non nulle, adresse basse signée, refus de motifs invalides et des adresses MMIO.
- Quatre tests Python sans ROM : relocations entre sections, LO signé, HI absent, bornes de table.
- Validation du YAML complet et du fixture corrigé : 88 fragments. Le catalogue signale encore 19 VRAM historiquement marquées « guessed » ; ne pas les présenter comme indépendamment prouvées par ce test.
- Compilation MSVC de RT64, de la bibliothèque générée et de l’exécutable.

Logs de construction :
```text
build/CODEX_SYMBOLS.log
build/CODEX_RELOCATED_RECOMP.log
build/CODEX_RELOCATED_BUILD.log
build/CODEX_RT64_CONFIGURE.log
build/CODEX_RT64_BUILD.log
build/CODEX_RSP_RECOMP.log
```

## Prochaine séquence de travail

1. Checkpoint publié (a9bd5cae). Rapprocher les changements de main et du checkpoint, sauvegarder les fichiers Downloads remplacés, reconstruire et retester cette version réunie.
2. Identifier la tâche **RSP type 4 à 0x80085390** depuis les octets et l’OSTask locaux (probablement un autre microcode de traitement ; ne pas supposer sa fonction sans vérification). La recompiler ou fournir une implémentation fidèle, sans la remplacer par un succès factice.
3. Relancer le test borné de 40–60 secondes, puis vérifier l’écran et les commandes.
4. Corriger le PAL réel : le probe force osTvType=PAL mais le runtime local utilise encore une cadence VI 60 Hz et ignore les facteurs de osViSetXScale/YScale. Le renderer annonçant 50 Hz ne suffit pas.
5. Vérifier l’audio et le premier parcours interactif. Traiter les nouvelles erreurs à partir des logs.

## Commandes et dépendances utiles

Les builds/tests se font **dans le dossier de téléchargements**. Utiliser le Python `.venv/Scripts/python.exe` et le CMake installé sous `C:/Program Files/CMake/bin` si PATH ne le trouve pas.

```powershell
# Test borné de l'exécutable construit :
.\windows\test_np3f_boot.ps1 -Seconds 40

# Après changement de hooks, avec les symboles ET relocations déjà préparés :
.\.local\bin\N64Recomp-native.exe recomp/np3f.toml
# Reconfigurer explicitement CMake avant de reconstruire la bibliothèque :
# un premier build MSBuild après changement du nombre d'unités peut omettre
# les nouveaux fichiers même si CMake vient de régénérer le projet.

# Microcode audio local :
.\.local\bin\RSPRecomp.exe recomp/np3f_audio.toml
```

`windows/prepare_np3f_native_code.ps1` est en préparation dans le checkout d’intégration ; il reste à le compléter et à le tester avant de le déclarer utilisable.

Dépendances locales :
```text
.local/n64recomp/src
.local/n64recomp/build-vs2022-x64
.local/n64modernruntime/src
.local/n64modernruntime/build-vs2022-x64
.local/rt64/src
```
Versions de référence :
```text
N64ModernRuntime cdf5abbd5026fef5c364c676e4667c45e42b6863
N64Recomp        ffb39cdad1da5de07eaaa48bd1db4a89a7986771
RT64             23cab603c4f9f4a8b369b38e036f1aa484603878
```

ROM locale uniquement : `baseroms/fr/baserom.z64`. Hash runtime `0x93AC31A17326F35B`.
Ne publier ni ROM, ni code généré depuis la ROM, ni dumps mémoire.

## Historique précédent

Le journal avant cette mise à jour est conservé intégralement dans [la révision 6f8870e](https://github.com/NeanSword/Aero-Stadium-2-FR/blob/6f8870ebb77cff6383659e4446c8abe211c13b7a/LastProgressLogs.md).

Il documente les diagnostics de main autour de GFX #61, SP/DP, queues 0x801221E0 / 0x80122A6C / 0x80122AD4, et les ajouts audio/input/shutdown. Ces observations restent utiles pour leur version précise, mais **ne décrivent plus le point de blocage de l’intégration locale testée ci-dessus**.

À chaque progrès notable, actualiser ce fichier avec : version exacte, modification, résultat observé, logs, défaut restant et prochaine action. Distinguer systématiquement « testé localement », « publié sur une branche » et « intégré à main ».
