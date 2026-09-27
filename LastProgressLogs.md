# LastProgressLogs — Aero-Stadium-2-FR

Dernière mise à jour : **27 septembre 2026 — chantier graphique 1440p**.


## Chantier graphique 1440p — plan détaillé

### Décision de phase

Le jeu est considéré fonctionnel pour le chantier actuel. **Le runtime est gelé** : aucune modification du scheduler, des fragments, des entrées, de l'audio, du pipeline RT64 ou de la logique de jeu ne doit être faite pour l'instant. La priorité est exclusivement l'amélioration graphique.

Cible principale : **2560×1440**.

L'objectif n'est pas de moderniser artificiellement Pokémon Stadium 2, mais d'obtenir un rendu **« N64 premium »** : mêmes formes, mêmes silhouettes, mêmes compositions et même identité visuelle, avec davantage de définition, des contours plus propres et une interface réellement lisible en 1440p.

### Dump NP3F reçu et analysé

Archive utilisateur : `NP3F_texture_dumps.zip`. Seul le nom du ZIP extérieur a été changé ; le dossier interne `texture_dumps/` est intact.

Première analyse :

- 11 269 entrées dans l'archive ;
- 2 817 textures uniques ;
- chaque texture possède quatre fichiers : `.rice.json`, `.rice.rdram`, `.tile.json`, `.tmem`.

Formats observés :

- RGBA16 : 2 474 ;
- IA8 : 228 ;
- I4 : 66 ;
- I8 : 33 ;
- IA4 : 10 ;
- IA16 : 4 ;
- RGBA32 : 2.

Les textures I/IA sont souvent des masques d'intensité/alpha. **Ne pas les recolorer automatiquement** : la couleur finale peut être appliquée par le rendu.

Principales dimensions :

- 16×16 : 1 601 ;
- 40×40 : 245 ;
- 32×32 : 116 ;
- 56×26 : 114 ;
- 56×28 : 113 ;
- 24×20 : 77 ;
- 376×4 : 49 ;
- 24×24 : 46 ;
- 32×64 : 32 ;
- 136×14 : 31 ;
- 128×16 : 30 ;
- 144×28 : 29 ;
- 112×36 : 28 ;
- 256×8 : 27 ;
- 64×32 : 26.

### Direction artistique verrouillée

Deux niveaux d'amélioration :

**A — UI / textes / menus : amélioration forte autorisée**

Pour les glyphes, labels, boutons, cadres, bandeaux, menus, HUD et pictogrammes, la reconstruction peut être très propre et détaillée. Priorités : netteté, lisibilité, alpha propre, contours précis et couleurs cohérentes avec l'original. Le résultat peut être sensiblement plus détaillé que la texture N64 d'origine.

**B — Pokémon / stades / gameplay : amélioration fidèle**

Pour les Pokémon, sols, murs et décors, priorité à la fidélité. Augmenter la définition, nettoyer les défauts et stabiliser les couleurs, mais ne pas inventer de micro-détails réalistes, de matière photoréaliste ou de rendu incompatible avec la géométrie simple du jeu.

Règle : **fidélité avant richesse**.

### Politique de résolution

Le 1440p est la résolution d'affichage, pas la taille de chaque texture.

Recommandations de départ :

- glyphes 24×20 : master ×8, export ×4 ou ×8 selon test ;
- icônes 40×40 : master ×8, export ×4 ou ×8 ;
- UI 56×26 / 56×28 : master ×8, export ×4 ou ×8 ;
- UI 112×36 / 136×14 / 144×28 : master ×4 à ×8, export ×4 ;
- petites textures UI : ×8 possible ;
- Pokémon : master ×4, export ×2 à ×4 ;
- stades : master ×4, export ×2 à ×4.

Ne jamais appliquer ×8 à tout le pack : le coût mémoire serait disproportionné. Utiliser ×8 surtout sur les petits éléments UI réellement visibles.

### Pipeline de travail

1. conserver le runtime stable ;
2. conserver le ZIP source localement et ne pas le publier ;
3. cataloguer chaque hash : dimensions, format, preview, catégorie, priorité, scènes observées ;
4. générer une preview brute nearest-neighbor et ne jamais l'écraser ;
5. classer les textures en `ui/text`, `ui/labels`, `ui/icons`, `pokemon`, `stadium`, `effects`, `backgrounds`, `microtiles`, `unknown` ;
6. valider le mécanisme de remplacement avec quatre textures pilotes : un texte, une RGBA, une I/IA et une texture répétée ;
7. vérifier orientation, UV, alpha, wrapping/clamping et rendu 1440p ;
8. commencer la production massive uniquement après ce test ;
9. capturer systématiquement avant/après ;
10. mesurer le bénéfice visuel et éviter les tailles inutiles.

### Traitement UI

- reconstruire proprement les diagonales et coins ;
- conserver proportions et composition ;
- préférer des aplats propres plutôt que du bruit ajouté ;
- nettoyer l'alpha ;
- tester sur fond clair et sombre ;
- juger à taille réelle en 1440p, pas seulement au zoom.

### Traitement des icônes

- conserver silhouette et aplats ;
- nettoyer les pixels accidentels ;
- lisser les courbes avec retenue ;
- corriger les couleurs seulement si la quantification source les a réellement dégradées ;
- éviter les halos autour des silhouettes.

### Traitement Pokémon

- comparer source, preview et rendu en jeu ;
- ne pas peindre un éclairage dynamique dans la texture ;
- conserver motifs, teintes et transitions stylisées ;
- ne pas ajouter poils, pores ou relief réaliste ;
- vérifier de près et à distance normale.

Le résultat doit sembler être **le même Pokémon Stadium 2, simplement plus propre**.

### Traitement des stades

- vérifier les répétitions et raccords ;
- préserver la fréquence des motifs ;
- éviter le moiré ;
- ne pas utiliser de photos de matériaux ;
- améliorer lignes, motifs, panneaux et logos avec retenue ;
- rester cohérent avec la faible densité polygonale.

### Couleurs

Pas de saturation/contraste global automatique.

- travailler en sRGB ;
- préserver les teintes dominantes ;
- corriger uniquement les dérives utiles ;
- éviter noirs bouchés et blancs brûlés ;
- tester sous l'éclairage réel du jeu ;
- pour I/IA, traiter intensité/alpha sans imposer une couleur finale.

### Alpha / contours

Contrôler :

- halos blancs/noirs ;
- franges d'upscale ;
- RGB parasite dans les pixels transparents ;
- perte d'un contour volontairement dur ;
- semi-transparence ajoutée inutilement.

### Validation 1440p

Scènes minimales :

1. écran titre ;
2. menu principal ;
3. écran riche en texte ;
4. sélection Pokémon ;
5. Pokémon en gros plan ;
6. Pokémon à distance normale ;
7. plan large d'un stade ;
8. surface de stade proche ;
9. transparence/effets ;
10. écran combinant plusieurs types d'UI.

Pour chaque scène : capture originale et capture pack avec paramètres identiques. Contrôle principal à 100 % en 2560×1440. Faire également un test rapide en 1080p.

### Performance

À chaque lot :

- surveiller chargements et stutters ;
- surveiller la VRAM si possible ;
- redescendre de ×8 à ×4 si le gain est invisible ;
- ne pas privilégier le nombre de pixels au détriment du résultat réel.

### Ordre de production

**Phase 1 — UI / texte / menus**

Priorités :
- 24×20 : 77 ;
- 56×26 : 114 ;
- 56×28 : 113 ;
- 112×36 : 28 ;
- 136×14 : 31 ;
- 144×28 : 29 ;
- puis les strips 128×16, 120×16, 152×12, 164×12, 180×10, 196×10, 104×18, 256×8 et 376×4 après identification.

**Phase 2 — icônes / éléments 2D**

- 40×40 : 245 ;
- 24×24 ;
- 32×32 ;
- autres petites illustrations identifiées.

**Phase 3 — Pokémon**

Construire d'abord le mapping :
`hash -> scène -> Pokémon -> partie du modèle`.

Traiter ensuite par petits lots avec captures comparatives.

**Phase 4 — stades**

Construire :
`hash -> stade -> surface/objet -> wrapping/clamping -> importance visuelle`.

Priorité aux sols, murs/panneaux proches, grandes surfaces répétées et logos basse résolution.

**Phase 5 — micro-tiles 16×16**

Les 1 601 textures 16×16 sont repoussées jusqu'à ce que leur usage soit identifié et leur gain visuel prouvé.

### Lissage des polygones

Le pack texture peut améliorer la perception des contours et motifs, mais **ne modifie pas la géométrie**. Aucun changement de maillage, normales ou nombre de polygones pendant cette phase.

### Critères d'acceptation

UI :
- netteté réellement supérieure en 1440p ;
- texte fidèle ;
- alpha propre ;
- absence de halo ;
- cohérence avec Stadium 2.

Pokémon :
- silhouette et grands motifs inchangés ;
- pas de détail réaliste inventé ;
- pas de changement fort de teinte ;
- amélioration visible mais discrète.

Stades :
- raccords invisibles ;
- pas de matériau photographique ;
- pas de moiré notable ;
- ambiance originale conservée.

Tous :
- aucun remplacement de mauvais hash ;
- aucune régression runtime ;
- aucun coût de performance disproportionné.

### Risques à surveiller

1. masques I/IA teintés dynamiquement ;
2. alpha limité de certaines textures source ;
3. coutures sur textures répétées ;
4. volume énorme des 16×16 ;
5. faux mapping par simple similarité de dimensions ;
6. confusion entre texture et éclairage ;
7. coût VRAM du ×8 ;
8. texture superbe isolément mais incohérente dans le jeu ;
9. hashes correspondant à des états/dumps dynamiques ;
10. perte du ZIP lors d'un changement d'environnement : dans ce cas demander simplement à l'utilisateur de le renvoyer.

### Prochaines actions exactes

1. ne toucher à aucun code runtime ;
2. figer le checkpoint graphique stable ;
3. rendre le catalogue reproductible ;
4. générer les previews par hash ;
5. créer les manifests Phase 1/2/3/4 ;
6. vérifier le chemin exact de remplacement RT64 déjà intégré ;
7. valider les quatre textures pilotes ;
8. tester en 2560×1440 ;
9. traiter les glyphes 24×20 ;
10. traiter les labels 56×26 / 56×28 ;
11. traiter les bandeaux larges ;
12. traiter les icônes 40×40 ;
13. mapper puis traiter un premier petit lot Pokémon ;
14. mapper puis traiter un premier petit lot stade ;
15. capturer avant/après ;
16. ajuster les multiplicateurs selon qualité et VRAM ;
17. ne revenir aux 16×16 qu'après les familles à fort impact ;
18. documenter dans ce journal les hashes, tailles source/export, scènes testées et commits de chaque lot.

### Définition de succès

Le chantier est réussi si, en 1440p :

- texte et menus paraissent réellement haute définition ;
- icônes propres et lisibles ;
- Pokémon plus nets tout en restant visuellement ceux de Stadium 2 ;
- stades plus propres sans photoréalisme ;
- aucune texture ne semble stylistiquement étrangère ;
- runtime toujours stable ;
- performances acceptables.

---

## Historique runtime — état antérieur conservé pour référence

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

Branche : **codex/native-rt64-integration**. Le checkpoint publié demeure [a9bd5cae](https://github.com/NeanSword/Aero-Stadium-2-FR/commit/a9bd5cae42a424e23e5d9c6f358b1bf0ec94cba6). Les corrections décrites ci-dessous sont encore locales au moment de cette entrée ; publication d'un nouveau checkpoint en cours. Main contient ce journal mais pas encore toutes ces corrections.

La fusion locale des ajouts récents de main est résolue mais pas encore commitée. Préserver les fichiers et terminer cette fusion. Les sources/exe de Downloads reçus de main pendant l'interruption nocturne ont été sauvegardés dans **build/codex-backup-20260927-042913/** avant le déploiement des sources réunies. Ancien backup : build/codex-backup-rt64-integration. Préserver également l'ancien checkout sale Aero-Stadium-2-FR ; sources/ du miroir ChatGPT est en lecture seule.

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

