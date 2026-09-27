# LastProgressLogs — Aero-Stadium-2-FR

Dernière mise à jour : **28 septembre 2026, chantier textures**.

## État actuel — fond Johto et logo AeroStadium 2 intégrés, 28 septembre 2026

L'utilisateur a choisi une **illustration originale pour donner une identité au portage**, uniquement avec des Pokémon de deuxième génération, puis un **logo « AeroStadium 2 » dans le style de l'ancien et de qualité comparable au nouveau fond**. Cette décision remplace la recherche d'un upscale fidèle pour cet écran seulement. Runtime toujours gelé ; aucune exception combat autorisée.

### Résultat créé et installé

Deux créations réalisées avec l'outil imagegen intégré :
- Fond original Johto : Germignon, Héricendre, Kaiminus, Pharamp, Scarhino, Mentali, Noctali, Lugia et Ho-Oh. Source générée 1448×1086, export sRGB opaque **1920×1440**.
- Logo original : AERO doré/bleu, STADIUM rouge en relief et 2 sur médaillon métallique. Source générée 1737×905 RGBA, export transparent **2256×1176** avec interpolation alpha prémultipliée et RGB nul dans les pixels totalement transparents.

Le service a bien produit ces deux nouvelles créations ; le refus d'un ancien essai d'édition n'est pas leur statut. Les dimensions exportées ne sont pas les résolutions natives du service.

**Pack actif :** `build/np3f/graphics-workbench/rt64-title-aerostadium-v1/`, pointé par `build/rt64-test-userdata/graphics.ini` (1440p, MSAA4, 4:3, plein écran, dump désactivé).

349 hashes uniques : **300 tuiles de fond 96×96 et 49 bandes de logo 2256×24**. Réassemblages pixel-identiques aux deux masters, alpha inclus. Les captures en jeu prouvent le nouveau fond et le logo AeroStadium 2 avec transparence.

### Raccords corrigés par configuration du pack

La comparaison master/capture montre que `defaultShift: "half"` causait des discontinuités du fond (œil de Kaiminus, contours de Germignon). Le test A/B avec **`defaultShift: "none"`** supprime ces décalages visibles. Le pack final fond+logo utilise `none`. **Aucun code renderer/runtime modifié.** Ne pas généraliser ce réglage aux autres assets sans test. Une partie des déformations observées en jeu venait donc du réglage de raccord, en plus du rendu artistique rejeté de l'upscale v2.

### Sources publiées et reprise locale

Branche `feature/graphics-quality`, commit **`c9bd4538a662f4abe75a198cf6c6cc643ddb44b7`**. Publication expressément autorisée par l'utilisateur après la demande du contrôle automatique. Six fichiers : trois outils d'export/découpage, une documentation et deux prompts. Aucun artwork, ROM, dump, modèle neuronal ou binaire publié.

Documentation : [TITLE_AEROSTADIUM_ORIGINAL.md](https://github.com/NeanSword/Aero-Stadium-2-FR/blob/feature/graphics-quality/docs/TITLE_AEROSTADIUM_ORIGINAL.md).
Prompts exacts : `docs/TITLE_JOHTO_ORIGINAL_PROMPT.txt` et `docs/TITLE_AEROSTADIUM_LOGO_PROMPT.txt`.

Assets conservés dans le vrai projet local `C:\\Users\\dofus\\Downloads\\PokemonStadium2_FR_Windows_Next\\pokestadiumgs-fr` :

```text
build/np3f/graphics-workbench/title-background/johto-original-v1/title-background-1920x1440.png
build/np3f/graphics-workbench/title-logo/aerostadium-v1/aerostadium-2-logo-2256x1176.png
build/np3f/graphics-workbench/title-logo/aerostadium-v1/in-game-aerostadium-1440p.png
build/np3f/graphics-workbench/rt64-title-aerostadium-v1/rt64.json
build/np3f/graphics-workbench/rt64-title-aerostadium-v1/build-manifest.json
build/np3f/graphics-workbench/rt64-title-aerostadium-v1/validation.json
```

Masters SHA-256 : fond `2fbcdb58e76def3121fb725791a53aec636bb441d18dc7a5457f7e5e4518a0a2`, logo `f23e0e0309cbfe4a2f28f3832ed1d86519819936264f7d573cd374a1794b4323`.

### Tests : visibilité validée, durée complète non validée

- `20260928-005257-712` : fond original, 120 s demandées, arrêt combat préexistant vers 101 s sur `0x80263890` ; exit -1073740791.
- `20260928-005554-147` : comparaison des raccords `none`, 30 s demandées, fermeture demandée après environ 14,77 s ; exit 0.
- `20260928-005953-090` : fond+logo final, 120 s demandées, fermeture demandée après environ 20,37 s ; exit 0. Capture complète conservée. **Ne pas annoncer 120 s réussies.**

Exécutable inchangé : **`AB2AB13B121B24993A060003BC4074AFB7FFB4FF4AC83AD29F213C223B7745E9`** ; pas de rebuild. Les deux checkpoints stables restent intacts. Retour avant logo : `graphics.ini.before-title-aerostadium-v1-20260928` ; retour avant fond Johto : `graphics.ini.before-title-johto-original-v1-20260928` ; ces sauvegardes sont à côté de `graphics.ini`.

**Suite possible :** recueillir le retour artistique sur l'écran original, puis poursuivre les textes/UI identifiés. Ne pas relancer les upscales rejetés comme s'ils étaient acceptés ; ne pas ouvrir un chantier runtime. Un essai continu de 120 s reste à faire si nécessaire, sans fermeture anticipée ni transition vers le combat bloqué.

---

## Historique — essais d'upscale abandonnés pour cet écran

**Interface exclusivement : l'utilisateur a répondu « Non, continuer uniquement l’interface » à la demande d'exception runtime.** Le blocage combat 0x80263890 reste volontairement non corrigé.

Le fond titre source 320×240 a été reconstruit (300 tuiles RGBA16 vérifiées). L'utilisateur demande un master 1920×1440, son intégration et un essai visible de 120 s. Après un refus du service de génération d'image, il autorise explicitement le traitement local fidèle.

- **v1** : nettoyage léger + Lanczos, intégré ; gain jugé invisible par l'utilisateur. Le probe `20260928-002502-503` est interrompu par l'arrêt combat préexistant, donc ne valide pas 120 s.
- **v2** : Real-ESRGAN x4plus-anime puis Lanczos vers 1920×1440 ; 300 PNG 96×96 et réassemblage pixel-identique validés. Remplacement observé sur une capture du jeu en 2560×1440. **Rejet artistique explicite : « l'upscale est bien, mais déforme énormément les pokémons ». Ne pas réactiver cette version.**
- Le probe v2 `20260928-004437-183` demandait 120 s mais a reçu une fermeture vers 31 s (stdout du 00:44:37 au 00:45:08), exit 0, aucun résultat de fin chronométrée. **Ne pas le déclarer validé 120 s.**
- Le 28 septembre, après ce retour, `graphics.ini` est restauré depuis `graphics.ini.before-title-background-v2-20260928` : pack **v1** à nouveau actif. La v2 et ses preuves restent conservées localement, sans publication de l'artwork.
- Un essai de restauration contrainte v3 respecte presque exactement les valeurs source lors de la réduction mais conserve trop de flou/aliasing : **prévisualisation seulement, non intégrée**. Une contrainte numérique ne prouve pas la fidélité artistique.

Assets locaux : `build/np3f/graphics-workbench/title-background/` (v1, `neural-v2/`, `rt64-title-background-v2/`). Le miroir de travail contient aussi `constrained-v3/` et les outils de restauration en cours. Recherche d'un master original HD : aucun trouvé exploitable à ce stade ; ne pas remplacer par une autre composition.

Exécutable toujours inchangé : `AB2AB13B121B24993A060003BC4074AFB7FFB4FF4AC83AD29F213C223B7745E9`. Le runtime, les checkpoints et le code du renderer restent gelés. **Prochaine étape : comparer une méthode d'agrandissement plus conservatrice ; montrer un aperçu fidèle avant de remplacer à nouveau le fond. Aucun résultat HD n'est accepté à ce stade.**

## Reprise prioritaire — chantier textures, 28 septembre 2026

La charte remise par l'utilisateur dans `Downloads/LastProgressLogs.md` est désormais conservée dans [docs/GRAPHICS_1440P_CHARTER.md](https://github.com/NeanSword/Aero-Stadium-2-FR/blob/feature/graphics-quality/docs/GRAPHICS_1440P_CHARTER.md). **Runtime gelé ; phase graphique exclusivement.** Les anciennes « prochaines actions » runtime ci-dessous sont historiques, pas des consignes actives.

### Nouveau checkpoint graphique
Branche `feature/graphics-quality`, commit **`717fd137a85f5f559bdbdd61db15c09b658a785b`**. Ajout de trois outils de catalogue/pilotes/tests et de deux documents. Aucun code runtime modifié ; aucun rebuild ; aucun dump, PNG propriétaire ou ROM publié.

Les branches de retour `checkpoint/stable-runtime-180s-2026-09-27` (`8c537b748578ea2f600c74e669946965886262a7`) et `checkpoint/graphics-1440p-stable-180s-2026-09-27` (`181c38e63247b8deae48d96ddd49fbf54a63e5f6`) restent inchangées.

Exécutable local conservé : SHA-256 **`AB2AB13B121B24993A060003BC4074AFB7FFB4FF4AC83AD29F213C223B7745E9`**, construit le 27 septembre à 22:00. Au checkpoint catalogue, le fichier `build/rt64-test-userdata/graphics.ini` était inchangé (SHA-256 `415ada1c8b9d104e5477ebf5833b1419d6262e3ceb5587a144da0012eeff02cb`). Son intégration titre ultérieure est décrite en tête de journal.

### Catalogue reproductible terminé
Archive retrouvée dans :
```text
C:\Users\dofus\Downloads\PokemonStadium2_FR_Windows_Next\pokestadiumgs-fr\build\rt64-test-userdata\NP3F_texture_dumps.zip
```
SHA-256 ZIP : `ea4dd62a6b779c4ab42a9c1f9ffaf03b60345b144123235febf9e4045d54f173`.

Inventaire vérifié : **11 269 entrées, 2 817 textures**, dont RGBA16 2 474 ; IA8 228 ; I4 66 ; I8 33 ; IA4 10 ; IA16 4 ; RGBA32 2. Tous les aperçus ont été décodés depuis TMEM ; les originaux et les agrandissements nearest-neighbor sont protégés contre l'écrasement par des pixels différents. Cinq tests synthétiques passent. Contre-vérification RDRAM linéaire : 2 149 correspondances, zéro échec applicable ; 668 chargements particuliers hors champ de cette contre-vérification.

Artefacts **locaux** installés dans le vrai projet Downloads :
```text
build/np3f/graphics-workbench/catalog/index.html
build/np3f/graphics-workbench/catalog/catalog.json
build/np3f/graphics-workbench/catalog/catalog.csv
build/np3f/graphics-workbench/catalog/raw/
build/np3f/graphics-workbench/catalog/nearest/
build/np3f/graphics-workbench/catalog/sheets/
build/np3f/graphics-workbench/pilot-validation/
build/np3f/graphics-workbench/stable-checkpoint.json
```
Outils installés : `tools/graphics/catalog_np3f_textures.py`, `prepare_np3f_texture_pilots.py`, `test_texture_decoder.py`. Commandes de reproduction et limites : [docs/TEXTURE_CATALOG_AND_PILOTS.md](https://github.com/NeanSword/Aero-Stadium-2-FR/blob/feature/graphics-quality/docs/TEXTURE_CATALOG_AND_PILOTS.md).

**Correction de classification importante :** les feuilles de contact 56×26 / 56×28 montrent des morceaux de portraits Pokémon rendus, souvent avec plusieurs états. Ne pas les traiter automatiquement comme des labels texte. Les 77 glyphes 24×20 et les 245 icônes 40×40 ont été examinés sur les feuilles de contact ; leur catégorie est fondée sur ces aperçus, l'association précise aux scènes reste à vérifier. Les autres hashes restent inconnus tant que leur usage n'est pas démontré. Les 1 601 microtuiles 16×16 restent différées.

### Quatre pilotes préparés — contrôle technique, pas artwork HD
| Rôle | Hash | Source | Export de contrôle |
|---|---|---|---|
| Texte L | `02f9b8d67777bf16` | IA8 24×20 | 96×80 |
| Icône Pikachu RGBA | `82dbc094ea0f8ac0` | RGBA16 40×40 | 160×160 |
| Bande COMBAT!, intensité | `951448e72cb575fc` | I4 112×36 | 448×144 |
| Motif Poké Ball répété | `369e34f9da3e0131` | I4 128×64 | 512×256 |

Les PNG reprennent exactement les previews nearest-neighbor ×4. Les masques restent neutres, sans recoloration. Un `rt64.json` v3/hash v5 contient ces quatre entrées preload. Les manifests Phase 1–5 sont générés, **production_allowed=false**. Ne pas présenter ces agrandissements comme un gain de qualité HD.

Le test visible confirme `[rt64] Texture pack HD: charge` (libellé générique du moteur). Configuration de test : preset 1440p, RT64 6×, MSAA 4×, aspect 4:3, fenêtre demandée 2560×1440. **Le chargement du pack est confirmé, mais les quatre hashes ne sont pas encore tous validés individuellement dans leur scène.** Comparaisons avant/après propres, orientation/alpha/UV/raccords, validation 1080p et mesures VRAM restent à faire. Aucun feu vert à la production massive.

### Blocage préexistant retrouvé au passage en combat
Le test de référence **sans remplacement** atteint menus/règles/aperçu des équipes, puis :
```text
[fragment-map] slot=0 rom=0015E8E0 ram=8025CED0 size=00006790
[fragment-map] No compiled section for slot=239 ram=80263870 size=0000E4F0
Failed to find function at 0x80263890
```
Le test avec les quatre pilotes rencontre le **même arrêt** avant combat. Pas d'erreur de chargement de texture constatée. Ne pas attribuer ce blocage au pack, ni déclarer toutes les scènes gameplay validées.

Logs copiés dans `build/np3f/graphics-workbench/` :
`baseline-visible.stdout.log`, `baseline-visible.stderr.log`, `pilot-1440p.stdout.log`, `pilot-1440p.stderr.log`.

Aucune correction runtime appliquée, conformément à la charte. **Réponse reçue : « Non, continuer uniquement l’interface ». Aucune exception runtime autorisée.**

La préparation de référence est également conservée dans le miroir local :
`C:\Users\dofus\.codex\.chatgpt-projects\g-p-6ab58e3c969481918cad038344c3d218\graphics-workbench`.
Les données de test sont séparées ; la configuration habituelle, les sauvegardes habituelles et la ROM source restent intactes.

---

## Historique — checkpoint stable et branche graphique

L'état runtime stable validé 180 secondes est désormais figé sur une branche de retour dédiée :

```text
checkpoint/stable-runtime-180s-2026-09-27
8c537b748578ea2f600c74e669946965886262a7
```

**Ne jamais modifier cette branche pour les expérimentations graphiques.** Elle sert de point de retour si une amélioration visuelle provoque une régression.

Les améliorations graphiques sont développées séparément sur :

```text
feature/graphics-quality
181c38e63247b8deae48d96ddd49fbf54a63e5f6
```

Cette branche ajoute une couche `graphics.ini` persistante avec preset **1440p par défaut** (RT64 6x, référence 240 -> 1440), presets 1080p et 4K, MSAA 4x par défaut, upscale 2D complet, filtrage anti-aliased pixel scaling, three-point filtering, format couleur interne High, triple buffering, aspect 4:3 par défaut et options fenêtre/fullscreen.

Elle ajoute aussi le chargement d'un texture pack RT64 depuis `textures` et un mode optionnel `dump_textures=true` qui remplit `texture_dumps`. Ce dump est destiné à identifier les hashes du fond de l'écran titre, des glyphes/texte, du HUD et des autres textures afin de produire de vrais remplacements HD. Aucun asset propriétaire n'est distribué.

Documentation : `docs/GRAPHICS_SETTINGS.md`.

**État de validation :** le checkpoint stable est validé ; la branche graphique est statiquement vérifiée mais n'a pas encore été compilée/testée sur Windows. Prochaine action : déployer les fichiers du commit `2e57f5d5...`, lancer les tests ROM-free, reconstruire uniquement le link-smoke, puis effectuer un probe visible court avant de continuer vers le pack HD.

### Premier build graphique Windows — configure OK, correction C++ appliquée

Le premier rebuild `-Clean` de la branche graphique configure correctement CMake/MSVC/RT64, puis échoue uniquement à la compilation de `np3f_rt64_renderer.cpp` sur une redéfinition locale de `gfx` :

```text
error C2374: 'gfx' : redéfinition ; initialisation multiple
error C2086: 'const aerostadium2::graphics::Settings &gfx' : redéfinition
```

La cause était une seconde déclaration `const auto& gfx = graphics::current();` dans le même scope constructeur après l'initialisation RT64. Le correctif supprime uniquement cette déclaration redondante ; la référence `gfx` initialisée plus haut reste utilisée par le log final, tandis que la déclaration du bloc de chargement texture reste dans son scope imbriqué.

Commit branche graphique corrigé :

```text
181c38e63247b8deae48d96ddd49fbf54a63e5f6
```

Diff : 1 suppression dans `cmake/np3f_link_smoke/np3f_rt64_renderer.cpp`. Le checkpoint stable `8c537b...` reste inchangé.

Prochaine action : récupérer uniquement ce fichier depuis le commit épinglé, relancer `build_np3f_link_smoke.ps1 -Clean -SkipRun`, puis poursuivre le probe 1440p si le build passe.

### Branche graphique 1440p validée 180 s

Le premier build corrigé de la branche `feature/graphics-quality` compile entièrement avec MSVC/RT64 et produit `AeroStadium2.exe` avec un exit code de build 0.

Le probe visible 180 s confirme l'activation réelle des réglages :

```text
[graphics] ... preset=1440p target=1440p scale=6.00x MSAA=4x upscale2D=all textures=on
[rt64] Renderer initialise: api=D3D12, preset=1440p, scale=6.00x, MSAA=4x, 2D=all, aspect=4:3, cadence=originale.
```

Aucun `[win-crash]`, aucun `Failed to find function`, aucune erreur RT64 ni erreur texture-pack n'apparaît dans ce run. Le renderer est encore actif à la fin :

```text
[test-result] seconds=180 entrypoint=1 threads=10 rsp=1 displaylist=1 completed=4342 age_ms=16 progressing=1
[audio-result] samples=11246656 peak=31204
```

Les métriques restent très proches du checkpoint stable précédent (4348 completions / age 31 ms), donc le preset 1440p 6x + MSAA 4x + upscale 2D complet ne montre pas de régression de progression dans ce scénario.

Un second checkpoint de retour a été créé :

```text
checkpoint/graphics-1440p-stable-180s-2026-09-27
181c38e63247b8deae48d96ddd49fbf54a63e5f6
```

Le checkpoint runtime original reste également inchangé :

```text
checkpoint/stable-runtime-180s-2026-09-27
8c537b748578ea2f600c74e669946965886262a7
```

**Prochaine phase :** capturer les textures RT64 utilisées par l'écran titre, les glyphes, le HUD et les textures 2D/3D importantes avec `dump_textures=true`, puis construire un vrai texture pack HD NP3F. L'objectif est d'améliorer les détails source réels, pas seulement de les afficher à plus haute résolution.

### Dump RT64 analysé — écran titre cartographié pour remplacements HD

Le ZIP `NP3F_texture_dumps.zip` contient 11 269 entrées, correspondant à 2 817 textures RT64 uniques avec leurs métadonnées/raw dumps.

L'écran titre NP3F a été reconstruit et cartographié précisément :

```text
Fond titre        320x240  = 300 tuiles RGBA16 de 16x16
Logo Stadium 2    376x196  = 49 bandes RGBA16 de 376x4
Mentions légales  416x64   = 8 bandes IA8 de 416x8
APPUYER SUR START 200x20   = hash 8ddd84322afffbe2
Dolby Surround     88x34   = hash f59608edae6d8d5a
Expansion Pak     216x18   = hash 811653c2eab64947
```

Le fond 320x240 reconstitué est bien l'image statique de l'écran titre avec le groupe de Pokémon ; le logo et les textes ont également été reconstitués séparément.

Un générateur de pack RT64 HD a été ajouté sur `feature/graphics-quality` :

```text
tools/graphics/build_np3f_title_pack_from_dump.py
```

Il lit directement le ZIP de dump, découvre automatiquement les hashes RT64 hashVersion 5 à partir de l'ancre `dd04fe928a08d2c1`, découpe des images maîtres HD et génère les PNG de remplacement + `rt64.json`.

Validation locale du générateur avec les masters 1x reconstitués :

```text
Background textures: 300
Logo textures: 49
Legal strips: 8
RT64 entries: 357
```

HEAD branche graphique après intégration :

```text
feature/graphics-quality
feae0b9e037f05e21f26a551bfd72786decad692
```

Le checkpoint graphique stable reste inchangé :

```text
checkpoint/graphics-1440p-stable-180s-2026-09-27
181c38e63247b8deae48d96ddd49fbf54a63e5f6
```

Documentation : `docs/HD_TITLE_TEXTURE_PACK.md`.

**Prochaine phase :** produire les images maîtres HD (fond 1920x1440, logo 2256x1176, textes/UI à 6x), générer le pack RT64 via l'outil, puis tester le remplacement in-game. Ensuite répéter le même travail de cartographie pour les menus, HUD, sprites et textures 3D importantes.

## Dernière avancée — baseline runtime stable 180 s, ancien crash overlay supprimé

**Sources publiées : branche `codex/native-rt64-integration` à `8c537b748578ea2f600c74e669946965886262a7`.** Ce head contient le checkpoint `e2221be441b5b55008fc74f5283541a7cbafaf42`, puis le hook coopératif partagé de fin de tâche et son test ROM-free. Main reçoit le journal ; les corrections de code restent sur la branche d'intégration.

Le test `20260927-172302-547` (300 s, code 24) atteint un écran de menu, puis se fige à 1 450 listes. Les piles montrent une boucle `func_80003AC0 -> func_8000201C` pendant le décodage d'une image. La version locale Work/Codex a affiné le premier hook de callsite : le hook publié est désormais placé dans **`func_8000201C` avant `0x80002038`**, qui est le prédicat partagé par le décodage d'image et la sauvegarde d'options. Il appelle `aero_poll_events(rdram)` seulement si `(int32_t)ctx->r3 <= 0`, c'est-à-dire sur le chemin « pas prêt », sans modifier le résultat ni l'état du jeu. `tools/recomp/test_native_adapters.py` vérifie ce hook exact et interdit le retour de l'ancien hook `func_80003AC0 / 0x80003BB0`. **Le résultat runtime de cette version affinée n'est pas encore validé : reconstruction/test Windows à faire.**

Audio mesuré sur ce test : **3 762 880 échantillons, pic 21 951**. Cela prouve une production non silencieuse, pas la qualité sonore. Les textures noires signalées par l'utilisateur restent à diagnostiquer.

### Baseline runtime stable — test 180 s après correction du preload overlay

Le test visible 180 s construit depuis le commit de branche `8c537b748578ea2f600c74e669946965886262a7` ne montre **aucun `[win-crash]`**, aucun `Failed to find function` et aucun softlock graphique à la fin du probe.

Résultat du harness :

```text
[test-result] seconds=180 entrypoint=1 threads=10 rsp=1 displaylist=1 completed=4348 age_ms=31 progressing=1
[audio-result] samples=11174688 peak=32767
```

Progression RT64 observée jusqu'à la fin :

```text
screens=6900 lists=3311
screens=7200 lists=3461
screens=7500 lists=3611
screens=7800 lists=3761
screens=8100 lists=3911
screens=8400 lists=4061
screens=8700 lists=4211
```

Le compteur continue d'augmenter d'environ 150 listes toutes les 300 présentations sur la fin du test. Le harness rapporte encore `progressing=1` avec seulement 31 ms depuis la dernière completion : **ce run se termine par la limite de 180 s alors que le jeu continue de tourner**, pas par un blocage identifié.

Le crash historique `func_81801420 / rdram_offset=0x80204894` est donc supprimé par le correctif du double chargement d'overlay. La boundary `func_82800490` reste également validée puisque l'erreur `Failed to find function at 0x80157B00` ne réapparaît pas.

Important : les anciens patchs expérimentaux de normalisation KSEG0 et de redéfinition `LD` sont encore présents dans la branche, mais **ils ne sont plus considérés comme la cause de cette correction**. Le diagnostic du C généré a prouvé que `func_81801420` n'utilisait que `MEM_W`; la cause démontrée était le preload/remap overlay. Ne pas les étendre davantage. Leur nettoyage éventuel devra être fait plus tard par test A/B, une fois un scénario gameplay reproductible établi.

Le runtime charge maintenant de nombreux fragments supplémentaires pendant les 180 s, notamment les slots 7, 19, 3, 51, 22, 50, 4, 49 et 0, sans crash. Les messages `No compiled section for slot=239` continuent d'apparaître pour des assets non compilés ; ils ne sont pas bloquants dans ce run.

**Prochaine phase : validation interactive longue plutôt qu'un nouveau patch.** Utiliser `test_np3f_boot.ps1 -Seconds 600 -Visible`, naviguer volontairement dans plusieurs menus, lancer au moins un combat ou mode jouable, tester les entrées manette, la sauvegarde/options et noter les problèmes visuels/audio. Ne modifier le runtime que si un nouveau défaut reproductible apparaît dans ce scénario.

### Correctif runner PowerShell 5.1

`windows/prepare_np3f_native_code.ps1` a été corrigé après un faux échec `NativeCommandError` sur `native_adapter_tests`. Python `unittest` écrit normalement ses points de progression sur stderr ; avec `$ErrorActionPreference = 'Stop'` et `*> $Log`, Windows PowerShell 5.1 transformait cette sortie normale en erreur terminante. Le runner capture désormais stdout/stderr séparément, restaure l'ErrorActionPreference et décide uniquement d'après le vrai `$LASTEXITCODE`. Commit : `36ff3e51f1cce645b4123e0abfe401215731b944`.

### Historique (supplanté) — ancien gel dépassé, première hypothèse KSEG0

Le test visible 180 s avec le hook conditionnel partagé dépasse l'ancien gel du menu à ~1 450 listes : progression observée jusqu'à **1 539 display lists**. Le prochain arrêt est un vrai access violation dans `func_81801420 + 0x298`, appartenant au fragment 4 (VRAM nominale 0x81800000, ROM NP3F 0xAE600). Juste avant le crash, ce fragment est chargé via le runtime slot 8.

Le crash lit l'adresse hôte correspondant à un offset RDRAM `0x80204894`. Cette valeur est une guest address KSEG0 valide dont l'offset physique est `0x00204894`, mais elle est arrivée zéro-étendue alors que les macros N64Recomp soustraient la base KSEG0 sign-étendue `0xFFFFFFFF80000000`. `np3f_memory_compat.h` normalise désormais explicitement le seul window KSEG0 RDRAM `0x80000000..0x807FFFFF` vers une valeur sign-étendue, tout en conservant la normalisation KSEG1 existante et sans masquer les MMIO/VRAM de fragments. Test ROM-free ajouté. Commit : `25b9f994607fa195cd3ba486b22830c068ad9f89`.

Prochaine action : récupérer `np3f_memory_compat.h` et `test_native_adapters.py` depuis ce commit, relancer `prepare_np3f_native_code.ps1`, puis `test_np3f_boot.ps1 -Seconds 180 -Visible`. Si le crash se déplace, analyser le nouveau probe plutôt que revenir au gel du menu.

### Historique — boundary overlay fragment10 manquante

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

### Historique (supplanté) — hypothèse LD

Le run suivant confirme que la boundary `func_82800490` a corrigé l'arrêt `Failed to find function at 0x80157B00` : cette erreur n'apparaît plus. Le runtime poursuit ensuite jusqu'au chargement de fragment4 (slot 8, ROM `0xAE600`) puis retombe dans `func_81801420` sur le même guest pointer KSEG0 zéro-étendu `0x80204894`.

La normalisation `MEM_W/H/B/HU/BU` était bien forcée dans toutes les unités générées, mais `recomp.h` définit `load_doubleword()` **avant** que `np3f_memory_compat.h` ne redéfinisse `MEM_W`. Le helper original a donc capturé l'accès brut et `LD` continuait de contourner la normalisation. L'adresse fautive finit par `+4`, ce qui correspond au premier mot chargé par `load_doubleword()`.

`np3f_memory_compat.h` redéfinit désormais `LD` pour reconstruire le 64-bit via le `MEM_W` normalisé. Aucun autre helper non aligné n'est modifié sans preuve. Test ROM-free ajouté. Commit de branche : `10038f97ed986d3a8cb8f0d8e50552c4094053d6`.

Prochaine action : récupérer seulement `cmake/np3f_generated_smoke/np3f_memory_compat.h` et `tools/recomp/test_native_adapters.py`, lancer le test ROM-free, reconstruire proprement `AeroNP3FGenerated.lib` (préférer `-Clean` pour forcer la prise en compte du forced-include), relinker, puis refaire le test visible 180 s.

### Historique (supplanté) — crash inchangé après hypothèse LD

Le nouveau binaire a bien été reconstruit (SHA-256 `E1FF4CE74BEF60EEA538006708D006439E6B89A69C8C92EAE448EEEDE6C83DB0`). L'arrêt `Failed to find function at 0x80157B00` reste absent, donc la boundary `func_82800490` est toujours validée.

Le crash persiste toutefois dans `func_81801420 + 0x11D` avec la même lecture guest zéro-étendue :

```text
[win-crash] access_violation operation=lecture target=0x1001F4894 rdram_base=0x7FFF0000
[win-crash] rdram_offset=0x80204894
```

Le patch `LD` n'a donc pas touché le chemin fautif. Ne pas ajouter d'autre correctif mémoire par supposition. Un nouvel outil ROM-free `tools/recomp/diagnose_generated_function.py` a été ajouté sur la branche pour extraire le C réellement généré de `func_81801420` et lister ses opérations mémoire. Commit de branche : `931705f8fd4b8e3b814a1c97e3548bdc58ee0e5d`.

Prochaine action : récupérer uniquement ce diagnostic, exécuter `.\.venv\Scripts\python.exe .\tools\recomp\diagnose_generated_function.py`, puis examiner/envoyer `build\np3f\logs\generated_func_81801420.log`. Le prochain correctif doit être fondé sur l'opération mémoire réellement présente dans ce C généré.

### Diagnostic exact du crash 0x80204894 — double chargement overlay confirmé

Le diagnostic du C généré de `func_81801420` montre uniquement des accès `MEM_W`; ni `LD` ni helper non aligné ne sont utilisés. Le problème n'était donc pas une macro mémoire spéciale.

La cause exacte est le preload générique de N64ModernRuntime. Au démarrage, le runtime appelle `load_overlays(0x1000, entrypoint, 1 MiB)`. Comme fragment4 est à ROM `0xAE600`, il est préchargé automatiquement à :

```text
0x80000400 + (0xAE600 - 0x1000) = 0x800ADA00
```

Plus tard Stadium enregistre réellement fragment4 (slot 8) à `0x80151570`. Notre ancien `aero_unmap_fragment()` ne déchargeait le slot que si le booléen local `fragment_loaded[slot]` était déjà vrai. Ce booléen ne connaît pas le preload générique, donc librecomp gardait l'ancienne base `0x800ADA00`.

`load_overlay_by_id()` voyait alors une section déjà relocalisée et utilisait sa branche d'addition :

```text
0x800ADA00 + 0x80151570 = 0x001FEF70   (wrap 32 bits)
0x001FEF70 + 0x5924    = 0x00204894
```

Puis le chemin mémoire transformait cette adresse physique incorrecte en l'offset hôte fautif `0x80204894`, exactement celui du crash.

Correctif : `aero_unmap_fragment()` décharge maintenant **tout slot compilé** via `unload_overlay_by_id(slot)`, même si `fragment_loaded[slot]` est faux. `unload_overlay_by_id()` est un no-op sûr si la section n'est pas chargée, et remet `section_addresses[section.index]` à la VRAM nominale lorsqu'elle l'est. Ainsi le remap Stadium repart toujours d'un état propre. Test ROM-free ajouté. Commit de branche : `8c537b748578ea2f600c74e669946965886262a7`.

Prochaine action : récupérer `cmake/np3f_link_smoke/np3f_register_overlays.cpp` et `tools/recomp/test_native_adapters.py`, lancer les tests ROM-free, relinker uniquement le link-smoke, puis refaire le test visible 180 s. Pas besoin de régénérer N64Recomp ni de recompiler `AeroNP3FGenerated.lib` pour ce correctif.

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
