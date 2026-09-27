# LastProgressLogs — Aero-Stadium-2-FR

Dernière mise à jour : **27 septembre 2026, 17:30 Europe/Paris**.

## Dernière avancée — checkpoint publié et blocage du menu identifié

**Sources publiées : branche `codex/native-rt64-integration` à `10038f97ed986d3a8cb8f0d8e50552c4094053d6`.** Ce head contient le checkpoint `e2221be441b5b55008fc74f5283541a7cbafaf42`, puis le hook coopératif partagé de fin de tâche et son test ROM-free. Main reçoit le journal ; les corrections de code restent sur la branche d'intégration.

Le test `20260927-172302-547` (300 s, code 24) atteint un écran de menu, puis se fige à 1 450 listes. Les piles montrent une boucle `func_80003AC0 -> func_8000201C` pendant le décodage d'une image. La version locale Work/Codex a affiné le premier hook de callsite : le hook publié est désormais placé dans **`func_8000201C` avant `0x80002038`**, qui est le prédicat partagé par le décodage d'image et la sauvegarde d'options. Il appelle `aero_poll_events(rdram)` seulement si `(int32_t)ctx->r3 <= 0`, c'est-à-dire sur le chemin « pas prêt », sans modifier le résultat ni l'état du jeu. `tools/recomp/test_native_adapters.py` vérifie ce hook exact et interdit le retour de l'ancien hook `func_80003AC0 / 0x80003BB0`. **Le résultat runtime de cette version affinée n'est pas encore validé : reconstruction/test Windows à faire.**

Audio mesuré sur ce test : **3 762 880 échantillons, pic 21 951**. Cela prouve une production non silencieuse, pas la qualité sonore. Les textures noires signalées par l'utilisateur restent à diagnostiquer.

### Correctif runner PowerShell 5.1

`windows/prepare_np3f_native_code.ps1` a été corrigé après un faux échec `NativeCommandError` sur `native_adapter_tests`. Python `unittest` écrit normalement ses points de progression sur stderr ; avec `$ErrorActionPreference = 'Stop'` et `*> $Log`, Windows PowerShell 5.1 transformait cette sortie normale en erreur terminante. Le runner capture désormais stdout/stderr séparément, restaure l'ErrorActionPreference et décide uniquement d'après le vrai `$LASTEXITCODE`. Commit : `36ff3e51f1cce645b4123e0abfe401215731b944`.

### Dernier test Windows — ancien gel dépassé, crash KSEG0 identifié

Le test visible 180 s avec le hook conditionnel partagé dépasse l'ancien gel du menu à ~1 450 listes : progression observée jusqu'à **1 539 display lists**. Le prochain arrêt est un vrai access violation dans `func_81801420 + 0x298`, appartenant au fragment 4 (VRAM nominale 0x81800000, ROM NP3F 0xAE600). Juste avant le crash, ce fragment est chargé via le runtime slot 8.

Le crash lit l'adresse hôte correspondant à un offset RDRAM `0x80204894`. Cette valeur est une guest address KSEG0 valide dont l'offset physique est `0x00204894`, mais elle est arrivée zéro-étendue alors que les macros N64Recomp soustraient la base KSEG0 sign-étendue `0xFFFFFFFF80000000`. `np3f_memory_compat.h` normalise désormais explicitement le seul window KSEG0 RDRAM `0x80000000..0x807FFFFF` vers une valeur sign-étendue, tout en conservant la normalisation KSEG1 existante et sans masquer les MMIO/VRAM de fragments. Test ROM-free ajouté. Commit : `25b9f994607fa195cd3ba486b22830c068ad9f89`.

Prochaine action : récupérer `np3f_memory_compat.h` et `test_native_adapters.py` depuis ce commit, relancer `prepare_np3f_native_code.ps1`, puis `test_np3f_boot.ps1 -Seconds 180 -Visible`. Si le crash se déplace, analyser le nouveau probe plutôt que revenir au gel du menu.

### Dernier test Windows — KSEG0 corrigé, boundary overlay fragment10 manquante

Le test suivant confirme que le crash `func_81801420 + 0x298` sur l'adresse guest KSEG0 `0x80204894` a disparu après la normalisation KSEG0. Le runtime continue ensuite jusqu'à un nouveau point d'arrêt déterministe :

```text
[fragment-map] slot=6  rom=000D7BC0 ram=80145250 size=0000C310
[fragment-map] slot=8  rom=000AE600 ram=80151570 size=000060F0
[fragment-map] slot=24 rom=000D4C50 ram=80157670 size=00002A70
Failed to find function at 0x80157B00
```

Le ROM start `0xD4C50` correspond à **fragment10**, VRAM nominale `0x82800000`. Le target runtime `0x80157B00` est à l'offset `+0x490`, donc correspond nominalement à **`func_82800490`**. Les symboles publics Stadium 2 placent la fonction suivante à `0x82800620`, soit une taille de `0x190`.

`generate_np3f_symbols.py` utilise maintenant son mécanisme existant `KNOWN_NP3F_MANUAL_FUNCTIONS` pour injecter cette boundary uniquement si Splat ne l'a pas déjà trouvée :

```python
("fragment10", 0x82800490): ("func_82800490", 0x190)
```

Un test ROM-free verrouille cette entrée. Commit de branche : `01792e6324a521299f9612ddb4d5a872fa53ada5`.

Prochaine action : récupérer `tools/recomp/generate_np3f_symbols.py` et `tools/recomp/test_native_adapters.py`, relancer `prepare_np3f_native_code.ps1`, reconstruire `AeroNP3FGenerated.lib`, relinker, puis refaire le test visible 180 s. Si `Failed to find function at 0x80157B00` disparaît, analyser le prochain point d'arrêt.

### Dernier test Windows — boundary fragment10 validée, crash KSEG0 restant via LD

Le run suivant confirme que la boundary `func_82800490` a corrigé l'arrêt `Failed to find function at 0x80157B00` : cette erreur n'apparaît plus. Le runtime poursuit ensuite jusqu'au chargement de fragment4 (slot 8, ROM `0xAE600`) puis retombe dans `func_81801420` sur le même guest pointer KSEG0 zéro-étendu `0x80204894`.

La normalisation `MEM_W/H/B/HU/BU` était bien forcée dans toutes les unités générées, mais `recomp.h` définit `load_doubleword()` **avant** que `np3f_memory_compat.h` ne redéfinisse `MEM_W`. Le helper original a donc capturé l'accès brut et `LD` continuait de contourner la normalisation. L'adresse fautive finit par `+4`, ce qui correspond au premier mot chargé par `load_doubleword()`.

`np3f_memory_compat.h` redéfinit désormais `LD` pour reconstruire le 64-bit via le `MEM_W` normalisé. Aucun autre helper non aligné n'est modifié sans preuve. Test ROM-free ajouté. Commit de branche : `10038f97ed986d3a8cb8f0d8e50552c4094053d6`.

Prochaine action : récupérer seulement `cmake/np3f_generated_smoke/np3f_memory_compat.h` et `tools/recomp/test_native_adapters.py`, lancer le test ROM-free, reconstruire proprement `AeroNP3FGenerated.lib` (préférer `-Clean` pour forcer la prise en compte du forced-include), relinker, puis refaire le test visible 180 s.

## Reprise immédiate (détails du checkpoint)

Le jeu natif Windows affiche maintenant **l'introduction, l'écran titre français et une démonstration de combat en 3D**. Observé directement dans la fenêtre AeroStadium2 via Computer Use. **Certaines textures sont noires**, signalement utilisateur à diagnostiquer ; ne pas déclarer le rendu correct ou le jeu terminé.

Le dernier test terminé, `build/np3f/probes/20260927-171712-983`, dépasse 2 011 listes graphiques et montre le stade et un Pokémon. Il s'arrête sur `Failed to find function at 0x8025C5B8`. Cet appel est l'export du fragment 26 à **0x81000168**, un J/NOP vers **0x841050E4** dans un autre fragment. Le générateur acceptait seulement les cibles du même fragment. Correction locale 2026-09-27.3 + test sans ROM ajoutés, compilation réussie.

Autre cause identifiée : **osContGetReadData à 0x80077544 manquait des symboles importés**. Il était recompilé en parseur PIF invité, alors que StartReadData était remplacé par le runtime hôte. Cela empêchait la lecture réelle du clavier/manette. Une plage vérifiée par SHA-256 découpe maintenant l'objet 0x800774C0..0x800776A0 et route GetReadData vers le moteur PC. Reconstruction et test interactif en cours à cette mise à jour.

## Emplacement du travail et publication

Compilation/test dans le dossier autorisé :
```text
C:\Users\dofus\Downloads\PokemonStadium2_FR_Windows_Next\pokestadiumgs-fr
```

Ce dossier n'est pas un checkout Git. Les sources sont préparées dans :
```text
C:\Users\dofus\.codex\.chatgpt-projects\g-p-6ab58e3c969481918cad038344c3d218\Aero-Stadium-2-integration
```

Branche : **codex/native-rt64-integration**, checkpoint **e2221be** publié. Main contient ce journal mais pas encore ces corrections de code.

La fusion locale des ajouts récents de main est terminée. Préserver les modifications postérieures au checkpoint indiquées en tête. Les sources/exe de Downloads reçus de main pendant l'interruption nocturne ont été sauvegardés dans **build/codex-backup-20260927-042913/** avant le déploiement des sources réunies. Ancien backup : build/codex-backup-rt64-integration. Préserver également l'ancien checkout sale Aero-Stadium-2-FR ; sources/ du miroir ChatGPT est en lecture seule.

Exécutable :
```text
build/np3f/link-smoke-prebuilt-vs2022-x64/bin/AeroStadium2.exe
```

## Corrections intégrées localement

- Relocations réelles des 88 fragments : **116 174**, dérivées des tables ROM, avec adaptation du lecteur de symboles de N64Recomp pour les références entre sections.
- Trampolines J/NOP de fragments et table d'exports du fragment 26, désormais avec les destinations connues dans d'autres fragments.
- Plages de fonctions manquantes vérifiées par SHA-256 : helpers assembleur audio, guRotateRPY, osAiSetNextBuffer, et désormais les routines de lecture des contrôleurs.
- Quatre vérifications cartouche conservées ; les lectures PI passent par le bridge ROM hôte, sans forcer leurs résultats.
- Fragments enregistrés à l'allocation complète par hooks func_80002440 / func_8000251C.
- **Taille résidente corrigée** : le runtime utilisait la taille du fichier ROM, comprenant une table de relocation libérée par le jeu. Le registre natif utilise maintenant la vraie allocation du jeu et charge exactement le slot voulu. Le blocage « Cannot partially unload section » du slot 52 est dépassé.
- Deux attentes du compteur audio, à 0x80035614 et 0x80035660, coopèrent avec le scheduler via yield_self_1ms. Compteur et conditions d'origine préservés.
- Deux accesseurs de fichiers de données du slot 239 traduits uniquement sur leurs motifs exacts : accesseur sept instructions ; accesseur douze instructions retournant le descripteur pour sélecteur 0 et le type 1 pour sélecteur 1. Bornes, adresse signée et effets de registres/stack contrôlés. CTest réussi.
- Microcode audio réel **aspMain_np3f** : ROM 0x1060, IMEM 0x1000, table FR ROM 0x87C20. Généré par tools/recomp/generate_np3f_rsp_audio.py.
- **Microcode RSP type 4** : ROM 0x85F90, instructions sur 0xAF0 octets, entrée IMEM 0x1080. Signature et branches vérifiées ; exécuté avec succès. Les 0x1000 octets annoncés par l'OSTask incluent des données non exécutables.
- SDL audio stéréo : échange des échantillons adjacents du RDRAM word-swizzled. Fréquences 48 kHz, 32 kHz et 30 kHz observées. Le son audible et sa qualité restent à vérifier.
- Runtime **PAL 50 Hz** et osViSetXScale/YScale implémentés par tools/recomp/patch_np3f_video.py, intégré au bootstrap.
- Clavier et manettes SDL réunis. Pressions clavier brèves conservées jusqu'au prochain poll ; le raccordement manquant de GetReadData restait toutefois à corriger.
- Test borné fiable : listes graphiques achevées, âge de la dernière, arrêt code 24 si rendu figé depuis 5 secondes. Piles des seuls threads invités en cas de blocage.

## Résultats à distinguer

| Test dans build/np3f/probes/ | Résultat |
| --- | --- |
| 20260926-230416-897 | 40 s / 1 140 listes ; ancien RSP factice, ne valide pas l'audio |
| 20260927-043123-578 | Version réunie : arrêt explicite sur RSP type 4 |
| 20260927-043845-087 | Type 4 exécuté ; plus de 1 563 listes ; conflit de taille du slot 52 |
| 20260927-044255-673 | PAL + tailles corrigées ; écran titre complet ; prochain accesseur slot 239 manquant |
| 20260927-171406-040 | Reproduction et dump local de cet accesseur, 12 instructions |
| 20260927-171712-983 | Accesseur corrigé ; combat de démonstration visible ; export 0x81000168 manquant |

Les modèles, animations et l'écran titre apparaissent. Les bandes verticales/horizontales de l'introduction peuvent appartenir à ses transitions ; ne pas les confondre avec les **textures noires** signalées par l'utilisateur. Menus pilotés, combat jouable complet, sauvegarde et son ne sont pas encore validés.

## Prochaines actions

1. Finir reconstruction/test avec osContGetReadData importé et export inter-fragment corrigé.
2. Vérifier Start puis les menus dans la fenêtre ; les entrées utilisateur peuvent interrompre une action Computer Use, il faut alors actualiser l'état de la fenêtre.
3. Reproduire les textures noires sur une scène stable et inspecter le chemin RT64/combiner/texture, sans modifier au hasard les données du jeu.
4. Terminer la fusion locale, publier les sources sur la branche d'intégration et mettre ce journal à jour avec le commit exact.
5. Vérifier audio, transitions, premier combat, fermeture, sauvegarde ; poursuivre jusqu'au prochain blocage réel.

## Commandes utiles

À exécuter dans Downloads avec CMake sous C:/Program Files/CMake/bin et Python .venv/Scripts/python.exe :
```powershell
# Après extraction Splat et bootstrap des dépendances :
.\windows\prepare_np3f_native_code.ps1

# Test borné visible (clavier et captures d'écran possibles) :
.\windows\test_np3f_boot.ps1 -Seconds 180 -Visible
```

La préparation complète a été testée : patch/configuration/build N64Recomp et RSPRecomp, symboles, relocations, génération CPU, microcodes audio et type 4. Après génération, **reconfigurer explicitement CMake de generated-smoke avant build** pour inclure les nouvelles unités. Construire avec MSBuild /m:2 /nodeReuse:false pour limiter les ressources.

Logs récents : build/np3f/logs/native_*.log, task4-*.log, pal-*.log, typed-assets-build.log, export-*.log, input-*.log. Tests visuels : stdout.log, stderr.log et result.json (hash EXE) dans chaque dossier probes.

Dépendances épinglées :
```text
N64ModernRuntime cdf5abbd5026fef5c364c676e4667c45e42b6863
N64Recomp        ffb39cdad1da5de07eaaa48bd1db4a89a7986771
RT64             23cab603c4f9f4a8b369b38e036f1aa484603878
```

ROM locale NP3F SHA-1 d7e13535b671024a92822db01507e87bd42f68ec. Ne publier ni ROM, ni code généré, ni dumps mémoire. AERO_DUMP_FRAGMENTS est opt-in et écrit uniquement localement.

Historique complet antérieur : [journal du checkpoint](https://github.com/NeanSword/Aero-Stadium-2-FR/blob/cfeeb5435b9345e6eb3ce797483d951de53087e4/LastProgressLogs.md).
